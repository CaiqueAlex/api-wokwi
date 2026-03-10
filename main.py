from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional
import logging
import uvicorn
import os

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== BANCO SQLite =====
DATABASE_URL = "sqlite:///./esp32_iot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== MODEL =====
class SensorData(Base):
    __tablename__ = "sensor_data"
    id                = Column(Integer, primary_key=True, index=True)
    device_id         = Column(String(100), index=True)
    temperature       = Column(Float)
    humidity          = Column(Float)
    media_temperatura = Column(Float, nullable=True)
    media_umidade     = Column(Float, nullable=True)
    max_temperatura   = Column(Float, nullable=True)
    min_temperatura   = Column(Float, nullable=True)
    leitura_num       = Column(Integer, nullable=True)
    ip_origem         = Column(String(45), nullable=True)
    timestamp         = Column(DateTime, default=datetime.utcnow)

# ===== DB DEPENDENCY =====
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== SCHEMAS =====
class SensorDataRequest(BaseModel):
    device_id:         str
    temperature:       float
    humidity:          float
    media_temperatura: Optional[float] = None
    media_umidade:     Optional[float] = None
    max_temperatura:   Optional[float] = None
    min_temperatura:   Optional[float] = None
    leitura_num:       Optional[int]   = None

# ===== MIDDLEWARE: Codespaces auth bypass =====
# O GitHub Codespaces bloqueia requisições externas que não vêm de navegador
# com um cookie de autenticação. Este middleware adiciona os headers necessários
# para que o ESP32 (que não é um navegador) consiga passar.
class CodespacesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Permite acesso externo sem autenticação do Codespaces
        response.headers["x-github-token"]        = ""
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# ===== LIFESPAN =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando API ESP32 IoT v8.0...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Banco SQLite pronto: esp32_iot.db")

    # Detecta se está rodando no Codespaces e loga a URL correta
    codespace_name = os.environ.get("CODESPACE_NAME", "")
    if codespace_name:
        public_url = f"https://{codespace_name}-8000.app.github.dev"
        logger.info("=" * 60)
        logger.info("🌐 RODANDO NO GITHUB CODESPACES")
        logger.info(f"📡 URL PÚBLICA: {public_url}")
        logger.info(f"📡 URL /sensors: {public_url}/sensors")
        logger.info("⚠️  Use esta URL no ESP32, NÃO o ngrok!")
        logger.info("⚠️  Certifique que a porta 8000 está como 'Public'")
        logger.info("=" * 60)
    else:
        logger.info("💻 Rodando localmente na porta 8000")

    yield
    logger.info("🛑 Encerrando API...")

# ===== APP =====
app = FastAPI(
    title="ESP32 IoT API",
    description="API para receber dados de sensores ESP32",
    version="8.0.0",
    lifespan=lifespan
)

# Ordem importa: CodespacesMiddleware antes do CORS
app.add_middleware(CodespacesMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ROTAS =====

@app.get("/")
async def root():
    codespace_name = os.environ.get("CODESPACE_NAME", "")
    url_publica = f"https://{codespace_name}-8000.app.github.dev" if codespace_name else "http://localhost:8000"
    return {
        "status":     "online",
        "message":    "🎯 ESP32 IoT API v8.0 funcionando!",
        "timestamp":  datetime.now().isoformat(),
        "url_publica": url_publica,
        "endpoints": {
            "POST_sensors": f"{url_publica}/sensors",
            "GET_sensors":  f"{url_publica}/sensors",
            "GET_dados":    f"{url_publica}/dados",
            "GET_health":   f"{url_publica}/health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "OK", "timestamp": datetime.now().isoformat()}

@app.post("/sensors")
async def receive_sensor_data(
    data: SensorDataRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        client_ip = request.client.host

        logger.info("=" * 60)
        logger.info(f"📡 DADOS RECEBIDOS - Device: {data.device_id}")
        logger.info(f"   🌐 IP: {client_ip}")
        logger.info(f"   🌡️  Temperatura: {data.temperature}°C")
        logger.info(f"   💧 Umidade: {data.humidity}%")
        if data.media_temperatura is not None:
            logger.info(f"   📊 Média Temp: {data.media_temperatura}°C")
            logger.info(f"   📊 Média Umid: {data.media_umidade}%")
            logger.info(f"   📈 Max: {data.max_temperatura}°C | Min: {data.min_temperatura}°C")
        if data.leitura_num is not None:
            logger.info(f"   🔢 Leitura #: {data.leitura_num}")
        logger.info("=" * 60)

        if not (-50 <= data.temperature <= 100):
            raise HTTPException(400, f"Temperatura inválida: {data.temperature}°C")
        if not (0 <= data.humidity <= 100):
            raise HTTPException(400, f"Umidade inválida: {data.humidity}%")

        registro = SensorData(
            device_id         = data.device_id,
            temperature       = data.temperature,
            humidity          = data.humidity,
            media_temperatura = data.media_temperatura,
            media_umidade     = data.media_umidade,
            max_temperatura   = data.max_temperatura,
            min_temperatura   = data.min_temperatura,
            leitura_num       = data.leitura_num,
            ip_origem         = client_ip
        )

        db.add(registro)
        db.commit()
        db.refresh(registro)

        logger.info(f"✅ Salvo no banco com ID: {registro.id}")

        return {
            "status":  "success",
            "message": "OK",
            "saved":   True,
            "id":      registro.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@app.get("/sensors")
async def get_sensor_data(limit: int = 20, db: Session = Depends(get_db)):
    try:
        dados = db.query(SensorData).order_by(
            SensorData.timestamp.desc()
        ).limit(limit).all()

        return {
            "status": "success",
            "count":  len(dados),
            "data": [
                {
                    "id":                d.id,
                    "device_id":         d.device_id,
                    "temperature":       d.temperature,
                    "humidity":          d.humidity,
                    "media_temperatura": d.media_temperatura,
                    "media_umidade":     d.media_umidade,
                    "max_temperatura":   d.max_temperatura,
                    "min_temperatura":   d.min_temperatura,
                    "leitura_num":       d.leitura_num,
                    "ip_origem":         d.ip_origem,
                    "timestamp":         d.timestamp.isoformat() if d.timestamp else None
                }
                for d in dados
            ]
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao consultar banco: {str(e)}")

@app.get("/dados")
async def ver_dados_simples(db: Session = Depends(get_db)):
    try:
        dados = db.query(SensorData).order_by(
            SensorData.timestamp.desc()
        ).limit(10).all()

        if not dados:
            return {"message": "Nenhum dado ainda", "total": 0}

        return {
            "total": len(dados),
            "dados": [
                {
                    "id":     d.id,
                    "device": d.device_id,
                    "temp":   f"{d.temperature}°C",
                    "umid":   f"{d.humidity}%",
                    "quando": d.timestamp.strftime("%H:%M:%S") if d.timestamp else None
                }
                for d in dados
            ]
        }
    except Exception as e:
        raise HTTPException(500, f"Erro ao consultar banco: {str(e)}")

@app.delete("/sensors")
async def limpar_dados(db: Session = Depends(get_db)):
    try:
        count = db.query(SensorData).count()
        db.query(SensorData).delete()
        db.commit()
        logger.info(f"🗑️ {count} registros removidos do banco.")
        return {"status": "ok", "removidos": count}
    except Exception as e:
        raise HTTPException(500, f"Erro ao limpar banco: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)