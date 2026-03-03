from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI(
    title="API REST Wokwi",
    description="API para integração com projeto Wokwi",
    version="1.0.0"
)

# ==========================
# MODELO DE DADOS
# ==========================

class SensorData(BaseModel):
    device_id: str
    temperature: float
    humidity: float


# ==========================
# BANCO SIMPLES EM MEMÓRIA
# ==========================

fake_database = []


# ==========================
# ROTAS GET
# ==========================

@app.get("/")
def home():
    return {"message": "API Wokwi rodando com sucesso 🚀"}


@app.get("/sensors")
def get_all_sensors():
    return fake_database


@app.get("/sensors/{device_id}")
def get_sensor_by_id(device_id: str):
    for item in fake_database:
        if item["device_id"] == device_id:
            return item
    return {"error": "Dispositivo não encontrado"}


# ==========================
# ROTAS POST
# ==========================

@app.post("/sensors")
def create_sensor_data(data: SensorData):
    fake_database.append(data.dict())
    return {
        "message": "Dados recebidos com sucesso",
        "data": data
    }


# ==========================
# EXEMPLO DE ENVIO PARA WOKWI (OPCIONAL)
# ==========================

@app.post("/send-to-wokwi")
def send_to_wokwi(data: SensorData):
    wokwi_url = "https://SEU_ENDPOINT_WOKWI_AQUI"

    try:
        response = requests.post(wokwi_url, json=data.dict())
        return {
            "status": response.status_code,
            "response": response.text
        }
    except Exception as e:
        return {"error": str(e)}