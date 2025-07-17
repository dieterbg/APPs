from sqlalchemy.orm import Session
from . import models

# --- Funções para Pacientes e Mensagens ---

def get_or_create_patient(db: Session, phone_number: str):
    """
    Busca um paciente pelo número de telefone. Se não existir, cria um novo.
    Retorna uma tupla: (objeto_paciente, foi_criado_agora)
    """
    patient = db.query(models.Patient).filter(models.Patient.phone_number == phone_number).first()
    if not patient:
        # Paciente não existe, vamos criar
        patient = models.Patient(phone_number=phone_number)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient, True  # Retorna o paciente e True (foi criado)
    
    return patient, False # Retorna o paciente e False (já existia)


def create_message(db: Session, patient_id: int, text: str, has_alert: bool, sender: str = "patient", ai_suggestion: str | None = None):
    """
    Cria e salva uma nova mensagem no banco de dados, incluindo a sugestão da IA.
    """
    db_message = models.Message(
        patient_id=patient_id,
        text=text,
        has_alert=has_alert,
        sender=sender,
        ai_suggestion=ai_suggestion
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_all_patients(db: Session):
    """
    Retorna todos os pacientes do banco de dados.
    """
    return db.query(models.Patient).all()

def create_metric(db: Session, patient_id: int, metric_type: str, value: float):
    """
    Cria e salva um novo registro de métrica no banco de dados.
    """
    db_metric = models.Metric(
        patient_id=patient_id,
        metric_type=metric_type,
        value=value
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric

def update_patient_details(db: Session, patient_id: int, name: str | None, altura_cm: float | None, peso_inicial: float | None, peso_meta: float | None):
    """
    Atualiza os detalhes de um paciente específico.
    """
    db_patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if db_patient:
        if name is not None:
            db_patient.name = name
        if altura_cm is not None:
            db_patient.altura_cm = altura_cm
        if peso_inicial is not None:
            db_patient.peso_inicial = peso_inicial
        if peso_meta is not None:
            db_patient.peso_meta = peso_meta
        
        db.commit()
        db.refresh(db_patient)
    return db_patient

# --- Funções para Profissionais ---

def get_professional_by_email(db: Session, email: str):
    return db.query(models.Professional).filter(models.Professional.email == email).first()

def create_professional(db: Session, email: str, hashed_password: str):
    db_professional = models.Professional(email=email, hashed_password=hashed_password)
    db.add(db_professional)
    db.commit()
    db.refresh(db_professional)
    return db_professional