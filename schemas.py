from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List

# ===== SCHEMAS BASE =====

class SensorBase(BaseModel):
    """Schema base para sensor readings"""
    device_id: str = Field(..., min_length=1, max_length=100, description="ID único do dispositivo")
    temperature: float = Field(..., ge=-50, le=100, description="Temperatura em Celsius (-50 a 100)")
    humidity: float = Field(..., ge=0, le=100, description="Umidade relativa (0 a 100%)")

    @validator('device_id')
    def validate_device_id(cls, v):
        if not v or v.strip() == "":
            raise ValueError('Device ID não pode estar vazio')
        return v.strip()

    @validator('temperature')
    def validate_temperature(cls, v):
        if v < -50 or v > 100:
            raise ValueError('Temperatura deve estar entre -50°C e 100°C')
        return round(v, 2)

    @validator('humidity')
    def validate_humidity(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Umidade deve estar entre 0% e 100%')
        return round(v, 2)

# ===== SCHEMAS DE CRIAÇÃO =====

class SensorCreate(SensorBase):
    """Schema para criar nova leitura de sensor"""
    pass

class SensorCreateWithIP(SensorBase):
    """Schema para criar com IP (uso interno)"""
    ip_origem: Optional[str] = None

# ===== SCHEMAS DE RESPOSTA =====

class SensorResponse(SensorBase):
    """Schema de resposta com dados completos"""
    id: int
    ip_origem: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# ===== SCHEMAS DE ATUALIZAÇÃO =====

class SensorUpdate(BaseModel):
    """Schema para atualizar dados do sensor"""
    device_id: Optional[str] = Field(None, min_length=1, max_length=100)
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)

# ===== SCHEMAS DE LISTAGEM =====

class SensorList(BaseModel):
    """Schema para listagem paginada"""
    total: int
    dados: List[SensorResponse]

# ===== SCHEMAS DE ESTATÍSTICAS =====

class TemperatureStats(BaseModel):
    """Estatísticas de temperatura"""
    média: float
    mínima: float
    máxima: float

class HumidityStats(BaseModel):
    """Estatísticas de umidade"""
    média: float
    mínima: float
    máxima: float

class StatisticsResponse(BaseModel):
    """Schema de resposta para estatísticas"""
    total_leituras: int
    dispositivos_únicos: int
    temperatura: TemperatureStats
    umidade: HumidityStats

# ===== SCHEMAS DE FILTROS =====

class SensorFilter(BaseModel):
    """Schema para filtros de consulta"""
    device_id: Optional[str] = None
    temp_min: Optional[float] = Field(None, ge=-50)
    temp_max: Optional[float] = Field(None, le=100)
    humidity_min: Optional[float] = Field(None, ge=0)
    humidity_max: Optional[float] = Field(None, le=100)
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)