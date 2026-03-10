from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Configuração do PostgreSQL - usando as mesmas credenciais do seu main.py
SQLALCHEMY_DATABASE_URL = "postgresql://iot_user:iot123456@localhost:5432/iot_sensors"

# Criar engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Criar SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Dependency para FastAPI
def get_db():
    """
    Dependency que fornece sessão do banco para os endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função para testar conexão
def test_connection():
    """
    Testa a conexão com o banco de dados
    """
    try:
        connection = engine.connect()
        connection.close()
        return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False