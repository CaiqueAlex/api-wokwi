from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="🚀 ESP32 IoT API",
    description="API IoT com ESP32, PostgreSQL e Edge Computing",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# MODELOS
# ==========================

class SensorData(BaseModel):
    device_id: str
    temperature: float
    humidity: float

# ==========================
# CONFIGURAÇÃO POSTGRESQL
# ==========================

DB_CONFIG = {
    "host": "localhost",
    "database": "iot_sensors", 
    "user": "iot_user",
    "password": "iot123456",
    "port": "5432"
}

def get_db_connection():
    """Conecta ao PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ Conectado ao PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Erro conectando ao PostgreSQL: {e}")
        return None

# ==========================
# ROTAS
# ==========================

@app.get("/")
def home():
    """Página inicial da API"""
    conn = get_db_connection()
    db_status = "✅ Conectado" if conn else "❌ Desconectado"
    if conn:
        conn.close()
    
    return {
        "🚀 status": "API ESP32 IoT funcionando!",
        "🗄️ database": db_status,
        "📚 swagger": "https://SEU_CODESPACE_URL/docs",
        "🔗 endpoints": {
            "GET /": "Esta página",
            "GET /health": "Saúde do sistema",
            "GET /sensors": "Ver todos os dados",
            "POST /sensors": "Receber dados do ESP32",
            "GET /stats": "Estatísticas dos sensores"
        }
    }

@app.get("/health")
def health_check():
    """Verificação de saúde do sistema"""
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            total_registros = cursor.fetchone()[0]
            conn.close()
            
            return {
                "status": "healthy",
                "database": "connected",
                "total_records": total_registros,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            if conn:
                conn.close()
            return {"status": "error", "error": str(e)}
    else:
        return {"status": "unhealthy", "database": "disconnected"}

@app.get("/sensors")
def get_sensors(limit: int = 50):
    """Buscar dados dos sensores"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT %s", (limit,))
        dados = cursor.fetchall()
        
        result = []
        for row in dados:
            result.append({
                "id": row["id"],
                "device_id": row["device_id"],
                "temperature": float(row["temperature"]),
                "humidity": float(row["humidity"]),
                "ip_origem": row["ip_origem"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None
            })
        
        conn.close()
        return {"total": len(result), "dados": result}
        
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Erro: {e}")

@app.post("/sensors")
async def receive_data(data: SensorData, request: Request):
    """Receber dados do ESP32"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco de dados")
    
    try:
        # EDGE COMPUTING - Validações
        if data.temperature < -50 or data.temperature > 100:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Temperatura inválida: {data.temperature}°C")
        
        if data.humidity < 0 or data.humidity > 100:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Umidade inválida: {data.humidity}%")
        
        cursor = conn.cursor()
        client_ip = str(request.client.host) if request.client else "unknown"
        
        # Inserir dados
        cursor.execute("""
            INSERT INTO sensor_readings (device_id, temperature, humidity, ip_origem)
            VALUES (%s, %s, %s, %s)
            RETURNING id, timestamp
        """, (data.device_id, data.temperature, data.humidity, client_ip))
        
        result = cursor.fetchone()
        conn.commit()
        
        logger.info("=" * 60)
        logger.info(f"📊 DADOS SALVOS - ID: {result[0]}")
        logger.info(f"🔧 Device: {data.device_id}")
        logger.info(f"🌡️ Temp: {data.temperature}°C | 💧 Umidade: {data.humidity}%")
        logger.info(f"🌐 IP: {client_ip} | ⏰ {result[1]}")
        logger.info("=" * 60)
        
        conn.close()
        
        return {
            "status": "✅ sucesso",
            "mensagem": "Dados salvos com sucesso!",
            "id": result[0],
            "dados": {
                "device_id": data.device_id,
                "temperature": data.temperature,
                "humidity": data.humidity,
                "timestamp": result[1].isoformat()
            }
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"❌ Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_statistics():
    """Estatísticas dos sensores"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(temperature) as avg_temp,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(humidity) as avg_humidity,
                MAX(timestamp) as last_reading
            FROM sensor_readings
        """)
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            "estatísticas": {
                "total_leituras": stats["total"],
                "última_leitura": stats["last_reading"].isoformat() if stats["last_reading"] else None,
                "temperatura": {
                    "média": round(float(stats["avg_temp"] or 0), 2),
                    "mínima": float(stats["min_temp"] or 0),
                    "máxima": float(stats["max_temp"] or 0)
                },
                "umidade_média": round(float(stats["avg_humidity"] or 0), 2)
            }
        }
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)