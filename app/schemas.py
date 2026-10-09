from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Solicitud(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: str = Field(min_length=1, max_length=100, pattern=r"^[\w-]+$")
    texto: str = Field(min_length=1, max_length=20000)
    cliente_id: str = Field(min_length=1, max_length=100, pattern=r"^[\w-]+$")


class Clasificacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: Literal["facturación", "técnico", "comercial", "otro"]
    prioridad: Literal["alta", "media", "baja"]


class Cliente(BaseModel):
    id: str
    nombre: str = Field(max_length=200)
    plan: Literal["basico", "premium"]


class Analisis(Solicitud, Clasificacion):
    respuesta: str
    cliente: Cliente | None = None
    tokens_entrada: int = Field(ge=0)
    tokens_salida: int = Field(ge=0)
    costo_estimado: Decimal = Field(ge=0)
    uso_estimado: bool = True
