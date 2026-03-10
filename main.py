from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional
import logging
import uvicorn
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Banco SQLite
DATABASE_URL = "sqlite:///./esp32_iot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# modelos / tabelas do banco
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

# Dependencias do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# schemaas
class SensorDataRequest(BaseModel):
    device_id:         str
    temperature:       float
    humidity:          float
    media_temperatura: Optional[float] = None
    media_umidade:     Optional[float] = None
    max_temperatura:   Optional[float] = None
    min_temperatura:   Optional[float] = None
    leitura_num:       Optional[int]   = None

class CodespacesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["x-github-token"]               = ""
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

# textin de incio
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando API ESP32 IoT v2.0...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Banco SQLite pronto: esp32_iot.db")

    codespace_name = os.environ.get("CODESPACE_NAME", "")
    if codespace_name:
        public_url = f"https://{codespace_name}-8000.app.github.dev"
        logger.info("=" * 60)
        logger.info("🌐 RODANDO NO GITHUB CODESPACES")
        logger.info(f"📡 URL PÚBLICA: {public_url}")
        logger.info(f"📡 URL /sensors:   {public_url}/sensors")
        logger.info(f"📡 URL /dashboard: {public_url}/dashboard")
        logger.info("⚠️ Deixa a porta como publico zé ruela")
        logger.info("=" * 60)
    else:
        logger.info("💻 Rodando localmente na porta 8000")

    yield
    logger.info("🛑 Encerrando API...")

# app
app = FastAPI(
    title="ESP32 IoT API",
    description="API para receber dados de sensores ESP32",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(CodespacesMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# rotas / retorna a lista de endpoints disponivel
# confirma se a api ta on

@app.get("/")
async def root():
    codespace_name = os.environ.get("CODESPACE_NAME", "")
    url_publica = f"https://{codespace_name}-8000.app.github.dev" if codespace_name else "http://localhost:8000"
    return {
        "status":    "online",
        "message":   "🎯 ESP32 IoT API v2.0 funcionando!",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /sensors":  f"{url_publica}/sensors",
            "GET /sensors":   f"{url_publica}/sensors",
            "GET /dashboard": f"{url_publica}/dashboard",
            "GET /dados":     f"{url_publica}/dados",
            "GET /health":    f"{url_publica}/health",
        }
    }


@app.get("/health")
async def health():
    return {"status": "OK", "timestamp": datetime.now().isoformat()}

# aqui recebe o post do esp a cada 10 segundos

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

        return {"status": "success", "message": "OK", "saved": True, "id": registro.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao salvar: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")

@app.get("/sensors")
async def get_sensor_data(limit: int = 20, db: Session = Depends(get_db)):
    try:
        dados = db.query(SensorData).order_by(SensorData.timestamp.desc()).limit(limit).all()
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
        dados = db.query(SensorData).order_by(SensorData.timestamp.desc()).limit(10).all()
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

# dashboard só para mostrar para a sala + html usando f-string pra mostrar

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(db: Session = Depends(get_db)):
    try:
        dados = db.query(SensorData).order_by(SensorData.timestamp.desc()).limit(30).all()

        total      = db.query(func.count(SensorData.id)).scalar() or 0
        avg_temp   = db.query(func.round(func.avg(SensorData.temperature), 2)).scalar() or 0
        avg_umid   = db.query(func.round(func.avg(SensorData.humidity), 2)).scalar() or 0
        max_temp   = db.query(func.round(func.max(SensorData.temperature), 2)).scalar() or 0
        min_temp   = db.query(func.round(func.min(SensorData.temperature), 2)).scalar() or 0

        ultimo = dados[0] if dados else None
        ultima_temp = f"{ultimo.temperature}°C" if ultimo else "—"
        ultima_umid = f"{ultimo.humidity}%" if ultimo else "—"
        ultimo_ts   = ultimo.timestamp.strftime("%d/%m/%Y %H:%M:%S") if ultimo and ultimo.timestamp else "—"

        linhas_html = ""
        for i, d in enumerate(dados):
            ts    = d.timestamp.strftime("%d/%m/%Y %H:%M:%S") if d.timestamp else "—"
            temp  = d.temperature if d.temperature is not None else "—"
            umid  = d.humidity if d.humidity is not None else "—"
            alerta = "🔴" if isinstance(temp, float) and temp >= 40 else ("🟡" if isinstance(temp, float) and temp >= 30 else "🟢")
            delay = i * 40
            linhas_html += f"""
            <tr class="fade-row" style="animation-delay:{delay}ms">
                <td><span class="badge-id">#{d.id}</span></td>
                <td><span class="device-tag">{d.device_id or '—'}</span></td>
                <td class="temp-cell">{alerta} {temp}°C</td>
                <td class="umid-cell">💧 {umid}%</td>
                <td>{d.media_temperatura if d.media_temperatura is not None else '—'}°C</td>
                <td>{d.max_temperatura if d.max_temperatura is not None else '—'}°C</td>
                <td>{d.min_temperatura if d.min_temperatura is not None else '—'}°C</td>
                <td>{d.leitura_num if d.leitura_num is not None else '—'}</td>
                <td>{d.ip_origem or '—'}</td>
                <td class="ts-cell">{ts}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 IoT — Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #060b14;
            color: #e2e8f0;
            min-height: 100vh;
            overflow-x: hidden;
        }}

        /* ── Fundo animado ── */
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background:
                radial-gradient(ellipse at 20% 20%, rgba(56,189,248,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(168,85,247,0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}

        .container {{
            position: relative;
            z-index: 1;
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px 24px;
        }}

        /* ── Header ── */
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 40px;
            animation: fadeDown 0.6s ease both;
        }}

        .logo {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .logo-icon {{
            width: 52px; height: 52px;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            border-radius: 16px;
            display: flex; align-items: center; justify-content: center;
            font-size: 26px;
            box-shadow: 0 0 24px rgba(56,189,248,0.4);
            animation: pulse-glow 2.5s ease-in-out infinite;
        }}

        h1 {{
            font-size: 1.7rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        h1 span {{
            display: block;
            font-size: 0.8rem;
            font-weight: 400;
            -webkit-text-fill-color: #64748b;
            color: #64748b;
            margin-top: 2px;
        }}

        .live-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(34,197,94,0.12);
            border: 1px solid rgba(34,197,94,0.3);
            color: #4ade80;
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}

        .live-dot {{
            width: 8px; height: 8px;
            background: #4ade80;
            border-radius: 50%;
            animation: blink 1.2s ease-in-out infinite;
        }}

        /* ── Cards de estatísticas ── */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 18px;
            margin-bottom: 36px;
        }}

        .stat-card {{
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
            padding: 24px 20px;
            position: relative;
            overflow: hidden;
            animation: zoomIn 0.5s ease both;
            transition: transform 0.25s, box-shadow 0.25s;
        }}

        .stat-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 40px rgba(56,189,248,0.15);
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: 20px 20px 0 0;
        }}

        .stat-card.blue::before   {{ background: linear-gradient(90deg, #38bdf8, #0ea5e9); }}
        .stat-card.purple::before {{ background: linear-gradient(90deg, #818cf8, #a78bfa); }}
        .stat-card.green::before  {{ background: linear-gradient(90deg, #4ade80, #22c55e); }}
        .stat-card.orange::before {{ background: linear-gradient(90deg, #fb923c, #f97316); }}
        .stat-card.red::before    {{ background: linear-gradient(90deg, #f87171, #ef4444); }}
        .stat-card.cyan::before   {{ background: linear-gradient(90deg, #22d3ee, #06b6d4); }}

        .stat-icon {{
            font-size: 1.6rem;
            margin-bottom: 12px;
            display: block;
        }}

        .stat-label {{
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            margin-bottom: 6px;
        }}

        .stat-value {{
            font-size: 1.7rem;
            font-weight: 700;
            color: #f1f5f9;
        }}

        .stat-sub {{
            font-size: 0.75rem;
            color: #475569;
            margin-top: 4px;
        }}

        /* ── Tabela ── */
        .table-section {{
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 24px;
            overflow: hidden;
            animation: fadeUp 0.6s ease 0.2s both;
        }}

        .table-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 22px 28px;
            border-bottom: 1px solid rgba(255,255,255,0.07);
            flex-wrap: wrap;
            gap: 12px;
        }}

        .table-title {{
            font-size: 1rem;
            font-weight: 600;
            color: #cbd5e1;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .refresh-info {{
            font-size: 0.78rem;
            color: #475569;
        }}

        .table-wrap {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}

        thead th {{
            background: rgba(255,255,255,0.04);
            color: #64748b;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            padding: 14px 16px;
            text-align: left;
            white-space: nowrap;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}

        tbody tr {{
            border-bottom: 1px solid rgba(255,255,255,0.04);
            transition: background 0.2s;
        }}

        tbody tr:last-child {{ border-bottom: none; }}

        tbody tr:hover {{ background: rgba(56,189,248,0.05); }}

        td {{
            padding: 14px 16px;
            color: #cbd5e1;
            white-space: nowrap;
        }}

        .badge-id {{
            background: rgba(129,140,248,0.15);
            color: #818cf8;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .device-tag {{
            background: rgba(56,189,248,0.12);
            color: #38bdf8;
            padding: 3px 10px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
        }}

        .temp-cell {{ color: #fb923c; font-weight: 600; }}
        .umid-cell {{ color: #38bdf8; font-weight: 600; }}
        .ts-cell   {{ color: #475569; font-size: 0.8rem; }}

        /* ── Linha vazia ── */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #475569;
        }}

        .empty-state .empty-icon {{ font-size: 3rem; margin-bottom: 12px; }}

        /* ── Footer ── */
        footer {{
            text-align: center;
            color: #334155;
            font-size: 0.78rem;
            margin-top: 40px;
            animation: fadeUp 0.6s ease 0.4s both;
        }}

        /* ── Animações ── */
        @keyframes fadeDown {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(24px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes zoomIn {{
            from {{ opacity: 0; transform: scale(0.88); }}
            to   {{ opacity: 1; transform: scale(1); }}
        }}

        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50%       {{ opacity: 0.2; }}
        }}

        @keyframes pulse-glow {{
            0%, 100% {{ box-shadow: 0 0 24px rgba(56,189,248,0.4); }}
            50%       {{ box-shadow: 0 0 40px rgba(56,189,248,0.8); }}
        }}

        .fade-row {{
            animation: fadeUp 0.4s ease both;
        }}

        /* ── Atraso nos cards ── */
        .stat-card:nth-child(1) {{ animation-delay: 0.05s; }}
        .stat-card:nth-child(2) {{ animation-delay: 0.10s; }}
        .stat-card:nth-child(3) {{ animation-delay: 0.15s; }}
        .stat-card:nth-child(4) {{ animation-delay: 0.20s; }}
        .stat-card:nth-child(5) {{ animation-delay: 0.25s; }}
        .stat-card:nth-child(6) {{ animation-delay: 0.30s; }}
    </style>
    <meta http-equiv="refresh" content="10">
</head>
<body>
<div class="container">

    <!-- Header -->
    <header>
        <div class="logo">
            <div class="logo-icon">📡</div>
            <h1>ESP32 IoT Dashboard
                <span>Monitoramento em tempo real · SQLite</span>
            </h1>
        </div>
        <div class="live-badge">
            <div class="live-dot"></div>
            LIVE · atualiza em 10s
        </div>
    </header>

    <!-- Stats -->
    <div class="stats-grid">
        <div class="stat-card blue">
            <span class="stat-icon">📊</span>
            <div class="stat-label">Total de Leituras</div>
            <div class="stat-value">{total}</div>
            <div class="stat-sub">registros no banco</div>
        </div>
        <div class="stat-card orange">
            <span class="stat-icon">🌡️</span>
            <div class="stat-label">Última Temperatura</div>
            <div class="stat-value">{ultima_temp}</div>
            <div class="stat-sub">{ultimo_ts}</div>
        </div>
        <div class="stat-card cyan">
            <span class="stat-icon">💧</span>
            <div class="stat-label">Última Umidade</div>
            <div class="stat-value">{ultima_umid}</div>
            <div class="stat-sub">{ultimo_ts}</div>
        </div>
        <div class="stat-card purple">
            <span class="stat-icon">📈</span>
            <div class="stat-label">Média Temperatura</div>
            <div class="stat-value">{avg_temp}°C</div>
            <div class="stat-sub">histórico geral</div>
        </div>
        <div class="stat-card red">
            <span class="stat-icon">🔺</span>
            <div class="stat-label">Máxima Registrada</div>
            <div class="stat-value">{max_temp}°C</div>
            <div class="stat-sub">pico histórico</div>
        </div>
        <div class="stat-card green">
            <span class="stat-icon">🔻</span>
            <div class="stat-label">Mínima Registrada</div>
            <div class="stat-value">{min_temp}°C</div>
            <div class="stat-sub">mínimo histórico</div>
        </div>
    </div>

    <!-- Tabela -->
    <div class="table-section">
        <div class="table-header">
            <div class="table-title">🗄️ Últimas 30 leituras</div>
            <div class="refresh-info">🔄 Página recarrega automaticamente a cada 10 segundos</div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Device</th>
                        <th>Temperatura</th>
                        <th>Umidade</th>
                        <th>Média Temp</th>
                        <th>Máxima</th>
                        <th>Mínima</th>
                        <th>Leitura #</th>
                        <th>IP Origem</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([linhas_html]) if dados else '''
                    <tr>
                        <td colspan="10">
                            <div class="empty-state">
                                <div class="empty-icon">📭</div>
                                <div>Nenhuma leitura ainda. Aguardando dados do ESP32...</div>
                            </div>
                        </td>
                    </tr>'''}
                </tbody>
            </table>
        </div>
    </div>

    <footer>
        ESP32 IoT API v8.0 · GitHub Codespaces · SQLite · FastAPI · {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    </footer>

</div>
</body>
</html>"""

        return HTMLResponse(content=html)

    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar dashboard: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)