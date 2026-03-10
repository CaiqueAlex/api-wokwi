# 🚀 ESP32 IoT API - PostgreSQL

API FastAPI para receber dados de sensores ESP32 com armazenamento PostgreSQL.

## 📋 Funcionalidades

- ✅ Recebe dados de temperatura e umidade
- ✅ Valida dados com Edge Computing 
- ✅ Armazena no PostgreSQL
- ✅ API REST completa
- ✅ Documentação automática (Swagger)
- ✅ Estatísticas em tempo real

## 🚀 Instalação e Execução

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Executar API
```bash
python main.py
```

### 3. Acessar documentação
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## 📡 Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Página inicial |
| GET | `/health` | Status do sistema |
| GET | `/sensors` | Listar dados |
| POST | `/sensors` | Receber dados ESP32 |
| GET | `/stats` | Estatísticas |

## 📊 Exemplo de Dados

```json
{
  "device_id": "ESP32_DHT22_WOKWI",
  "temperature": 25.5,
  "humidity": 60.0
}
```

## 🛠️ Tecnologias

- FastAPI
- PostgreSQL 
- Pydantic
- Uvicorn
- Psycopg2