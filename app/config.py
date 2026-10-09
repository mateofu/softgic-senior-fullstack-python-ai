from decimal import Decimal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./solicitudes.db"
    crm_url: HttpUrl = "http://localhost:9000"
    crm_max_attempts: int = Field(default=3, ge=1, le=10)
    crm_base_delay: float = Field(default=0.25, gt=0, le=10)
    crm_request_timeout: float = Field(default=2, gt=0, le=30)
    crm_total_timeout: float = Field(default=5, gt=0, le=60)
    input_price_per_million: Decimal = Field(default=Decimal("0"), ge=0)
    output_price_per_million: Decimal = Field(default=Decimal("0"), ge=0)
