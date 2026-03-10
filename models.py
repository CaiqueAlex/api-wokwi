from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class SensorReading(Base):
    """
    Modelo SQLAlchemy para tabela sensor_readings
    Compatível com sua estrutura atual do PostgreSQL
    """
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id = Column(String(100), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    ip_origem = Column(String(45), nullable=True)  # Para IPv4 e IPv6
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SensorReading(id={self.id}, device={self.device_id}, temp={self.temperature}°C, humidity={self.humidity}%)>"

    def to_dict(self):
        """
        Converte o objeto para dicionário para serialização JSON
        """
        return {
            "id": self.id,
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "ip_origem": self.ip_origem,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

# Modelo adicional para estatísticas (opcional)
class DeviceStats(Base):
    """
    Modelo para armazenar estatísticas por dispositivo (opcional)
    """
    __tablename__ = "device_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, index=True)
    total_readings = Column(Integer, default=0)
    avg_temperature = Column(Float)
    avg_humidity = Column(Float)
    last_reading = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())