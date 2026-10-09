from sqlalchemy import JSON, String
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalisisGuardado(Base):
    __tablename__ = "analisis"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    contenido: Mapped[dict] = mapped_column(JSON, nullable=False)


def crear_engine(url: str):
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return create_async_engine(url, pool_pre_ping=True)
