import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv # NOVO: Importa a função para carregar o .env

# NOVO: Carrega as variáveis do arquivo .env para o ambiente
load_dotenv() 

DATABASE_URL = os.getenv("DATABASE_URL")

# A linha abaixo corrige um bug comum entre SQLAlchemy e o driver do Heroku/Render
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Adicionamos uma verificação para garantir que a URL foi carregada
if DATABASE_URL is None:
    print("ERRO CRÍTICO: A variável de ambiente DATABASE_URL não foi encontrada.")
    print("Verifique se o arquivo .env existe na raiz do projeto e contém a variável DATABASE_URL.")
    # Podemos até forçar a parada aqui, mas por enquanto o erro do SQLAlchemy já faz isso.
    # exit(1) 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()