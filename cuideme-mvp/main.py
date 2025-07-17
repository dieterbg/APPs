import os
import json
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import List, Annotated
import google.generativeai as genai 

from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from fastapi.middleware.cors import CORSMiddleware
from database import crud, models
from database.database import engine, get_db
from send_scheduled_messages import run_task

# --- Gerenciador de Conexões WebSocket ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
    async def connect(self, websocket: WebSocket, patient_id: int):
        await websocket.accept()
        if patient_id not in self.active_connections: self.active_connections[patient_id] = []
        self.active_connections[patient_id].append(websocket)
        print(f"Nova conexão WebSocket para o paciente {patient_id}.")
    def disconnect(self, websocket: WebSocket, patient_id: int):
        if patient_id in self.active_connections:
            self.active_connections[patient_id].remove(websocket)
            if not self.active_connections[patient_id]: del self.active_connections[patient_id]
            print(f"Conexão WebSocket fechada para o paciente {patient_id}.")
    async def broadcast_to_patient_viewers(self, patient_id: int, message: dict):
        if patient_id in self.active_connections:
            for connection in self.active_connections[patient_id]:
                await connection.send_json(message)

manager = ConnectionManager()
models.Base.metadata.create_all(bind=engine)

# --- Configuração de Segurança e Variáveis de Ambiente ---
SECRET_KEY = os.getenv("SECRET_KEY", "uma_chave_secreta_padrao_para_desenvolvimento")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
CRON_SECRET = os.getenv("CRON_SECRET")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WELCOME_MESSAGE = "Olá! Bem-vindo(a) ao nosso canal de acompanhamento. Por aqui, nossa equipe e nosso assistente virtual irão interagir com você para acompanhar sua jornada. Sinta-se à vontade para responder às perguntas quando for mais conveniente."
ALERT_KEYWORDS = ["dor", "febre", "difícil", "não tomei", "sem dormir", "ansioso", "triste", "passando mal", "ajuda"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- Funções de Segurança ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_professional(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não foi possível validar as credenciais", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    professional = crud.get_professional_by_email(db, email=token_data.email)
    if professional is None: raise credentials_exception
    return professional

# --- Configuração do App FastAPI ---
app = FastAPI(title="Cuide.me Backend", version="1.5.0")
origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Modelos Pydantic ---
class Token(BaseModel): access_token: str; token_type: str
class TokenData(BaseModel): email: str | None = None
class ProfessionalCreate(BaseModel): email: str; password: str
class ProfessionalResponse(BaseModel):
    id: int; email: str
    model_config = ConfigDict(from_attributes=True)
class MessageSendRequest(BaseModel): text: str
class PatientDetailsUpdate(BaseModel):
    name: str | None = None
    altura_cm: float | None = None
    peso_inicial: float | None = None
    peso_meta: float | None = None
class PatientResponse(BaseModel):
    id: int; phone_number: str; name: str | None = None; has_alert: bool = False; status: str; altura_cm: float | None = None; peso_inicial: float | None = None; peso_meta: float | None = None
    model_config = ConfigDict(from_attributes=True)
class MetricResponse(BaseModel):
    metric_type: str; value: float; timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Função Auxiliar ---
def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text}}
    try:
        with httpx.Client() as http_client:
            response = http_client.post(url, headers=headers, json=data)
            response.raise_for_status()
        print(f"Mensagem enviada com sucesso para {to_number}.")
        return True
    except httpx.HTTPStatusError as e:
        print(f"Erro ao enviar mensagem para {to_number}: {e.response.status_code}\n{e.response.text}")
        return False

# --- Endpoints ---
@app.post("/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        if (data.get("entry") and data["entry"][0].get("changes") and data["entry"][0]["changes"][0].get("value") and data["entry"][0]["changes"][0]["value"].get("messages")):
            message_data = data["entry"][0]["changes"][0]["value"]["messages"][0]
            from_number = message_data["from"]
            message_text = message_data["text"]["body"]
            patient, was_created = crud.get_or_create_patient(db, phone_number=from_number)
            if was_created:
                print(f"Novo paciente criado (ID: {patient.id}). Enviando mensagem de boas-vindas.")
                send_whatsapp_message(to_number=patient.phone_number, text=WELCOME_MESSAGE)
            ai_data = {}
            if GOOGLE_API_KEY:
                prompt = ("Analise a mensagem... retorne JSON com 'is_alert', 'auto_reply_text', 'extracted_metrics'.")
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    ai_data = json.loads(cleaned_response)
                except Exception as e:
                    print(f"Erro ao processar com IA: {e}")
            
            has_alert = ai_data.get('is_alert', False)
            auto_reply_text = ai_data.get('auto_reply_text')
            metrics_to_save = ai_data.get('extracted_metrics', [])
            if metrics_to_save:
                for metric in metrics_to_save:
                    crud.create_metric(db, patient_id=patient.id, metric_type=metric['type'], value=metric['value'])
            if auto_reply_text and patient.status == 'automatico':
                send_whatsapp_message(to_number=patient.phone_number, text=auto_reply_text)
            new_message = crud.create_message(db=db, patient_id=patient.id, text=message_text, has_alert=has_alert, sender="patient")
            message_dict = {"id": new_message.id, "text": new_message.text, "sender": new_message.sender, "timestamp": new_message.timestamp.isoformat(), "ai_suggestion": new_message.ai_suggestion}
            await manager.broadcast_to_patient_viewers(patient.id, message_dict)
        return {"status": "ok"}
    except Exception as e:
        print(f"Erro fatal no webhook: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/auth/register", response_model=ProfessionalResponse, status_code=201)
def register_professional(professional: ProfessionalCreate, db: Session = Depends(get_db)):
    db_professional = crud.get_professional_by_email(db, email=professional.email)
    if db_professional: raise HTTPException(status_code=400, detail="Email já registrado")
    hashed_password = get_password_hash(professional.password)
    return crud.create_professional(db=db, email=professional.email, hashed_password=hashed_password)

@app.post("/auth/login", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    professional = crud.get_professional_by_email(db, email=form_data.username)
    if not professional or not verify_password(form_data.password, professional.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": professional.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/patients", response_model=List[PatientResponse])
def get_patients(current_professional: Annotated[models.Professional, Depends(get_current_professional)], db: Session = Depends(get_db)):
    return db.query(models.Patient).all()

@app.put("/api/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int, 
    patient_data: PatientDetailsUpdate,
    current_professional: Annotated[models.Professional, Depends(get_current_professional)], 
    db: Session = Depends(get_db)
):
    updated_patient = crud.update_patient_details(
        db, 
        patient_id=patient_id, 
        name=patient_data.name,
        altura_cm=patient_data.altura_cm,
        peso_inicial=patient_data.peso_inicial,
        peso_meta=patient_data.peso_meta
    )
    if not updated_patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return updated_patient

@app.get("/api/patients/{patient_id}/metrics", response_model=List[MetricResponse])
def get_patient_metrics(patient_id: int, current_professional: Annotated[models.Professional, Depends(get_current_professional)], db: Session = Depends(get_db)):
    return db.query(models.Metric).filter(models.Metric.patient_id == patient_id).order_by(models.Metric.timestamp.asc()).all()

@app.get("/api/messages/{patient_id}", response_model=List[dict])
def get_messages_for_patient(patient_id: int, current_professional: Annotated[models.Professional, Depends(get_current_professional)], db: Session = Depends(get_db)):
    messages_from_db = db.query(models.Message).filter(models.Message.patient_id == patient_id).order_by(models.Message.timestamp.asc()).all()
    response_data = [{"id": msg.id, "text": msg.text, "sender": msg.sender, "timestamp": msg.timestamp.isoformat(), "ai_suggestion": msg.ai_suggestion} for msg in messages_from_db]
    db.query(models.Message).filter(models.Message.patient_id == patient_id, models.Message.has_alert == True).update({"has_alert": False})
    db.commit()
    return response_data

@app.post("/api/messages/send/{patient_id}", status_code=201)
def send_message_to_patient(patient_id: int, message_request: MessageSendRequest, current_professional: Annotated[models.Professional, Depends(get_current_professional)], db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient: raise HTTPException(status_code=404, detail="Paciente não encontrado")
    if not send_whatsapp_message(to_number=patient.phone_number, text=message_request.text):
        raise HTTPException(status_code=500, detail="Erro ao enviar mensagem pela API do WhatsApp.")
    new_message = crud.create_message(db=db, patient_id=patient.id, text=message_request.text, sender="professional")
    return {"id": new_message.id, "text": new_message.text, "sender": new_message.sender, "timestamp": new_message.timestamp.isoformat(), "ai_suggestion": None}

@app.websocket("/ws/{patient_id}")
async def websocket_endpoint(websocket: WebSocket, patient_id: int):
    await manager.connect(websocket, patient_id)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket, patient_id)

@app.get("/")
def read_root():
    return {"status": "API do Cuide.me está funcionando!"}

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode"); token = request.query_params.get("hub.verify_token"); challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN: return int(challenge)
    else: raise HTTPException(status_code=403, detail="Verification token mismatch")