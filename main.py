from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from typing import List
import json

app = FastAPI(
    title="🚀 API ESP32-Wokwi",
    description="API para receber dados do ESP32 via Wokwi",
    version="2.0.0"
)

# CORS
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
# BANCO DE DADOS EM MEMÓRIA
# ==========================

database: List[dict] = []

# ==========================
# ROTAS
# ==========================

@app.get("/")
def home():
    return {
        "🚀 status": "API funcionando!",
        "📊 total_dados": len(database),
        "📚 docs": "/docs",
        "🔗 endpoints": {
            "GET /sensors": "Ver todos os dados",
            "POST /sensors": "Receber dados do ESP32",
            "POST /test": "Teste manual",
            "DELETE /sensors": "Limpar dados"
        }
    }

@app.get("/sensors")
def get_sensors():
    return {
        "total": len(database),
        "dados": database
    }

@app.post("/sensors")
async def receive_data(data: SensorData, request: Request):
    # Dados com timestamp
    sensor_data = {
        "device_id": data.device_id,
        "temperature": data.temperature,
        "humidity": data.humidity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip_origem": str(request.client.host)
    }
    
    database.append(sensor_data)
    
    # LOG DETALHADO
    print("=" * 80)
    print("🌡️ DADOS RECEBIDOS DO ESP32:")
    print(f"🔧 Device: {data.device_id}")
    print(f"🌡️ Temperatura: {data.temperature}°C")
    print(f"💧 Umidade: {data.humidity}%")
    print(f"⏰ Horário: {sensor_data['timestamp']}")
    print(f"🌐 IP: {sensor_data['ip_origem']}")
    print(f"📊 Total registros: {len(database)}")
    print("=" * 80)
    
    return {
        "✅ status": "sucesso",
        "📨 mensagem": "Dados recebidos!",
        "📊 dados": sensor_data,
        "🔢 total": len(database)
    }

@app.post("/test")
def test_api():
    test_data = {
        "device_id": "TEST_ESP32",
        "temperature": 25.8,
        "humidity": 65.2,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip_origem": "teste"
    }
    
    database.append(test_data)
    
    print("🧪 TESTE MANUAL EXECUTADO!")
    print(f"📊 Total registros: {len(database)}")
    
    return {
        "✅ status": "teste_ok",
        "📨 dados": test_data
    }

@app.delete("/sensors")
def clear_data():
    global database
    count = len(database)
    database = []
    
    print(f"🗑️ DATABASE LIMPO! {count} registros removidos.")
    
    return {
        "✅ status": "limpo",
        "🗑️ removidos": count
    }

@app.get("/sensors/{device_id}")
def get_device_data(device_id: str):
    device_data = [d for d in database if d["device_id"] == device_id]
    return {
        "device_id": device_id,
        "total": len(device_data),
        "dados": device_data
    }

# ==========================
# STARTUP
# ==========================

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 80)
    print("🚀 API ESP32-WOKWI INICIADA!")
    print("📡 URL: https://sturdy-lamp-4j7rp5qqgr7p3jw9x-8000.app.github.dev")
    print("📚 Docs: https://sturdy-lamp-4j7rp5qqgr7p3jw9x-8000.app.github.dev/docs")
    print("🔌 Aguardando dados do ESP32...")
    print("=" * 80)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )