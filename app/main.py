import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.crm import CRMClient
from app.database import AnalisisGuardado, Base, crear_engine
from app.graph import analizar, crear_modelo_simulado
from app.schemas import Analisis, Solicitud

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_app(settings: Settings | None = None, model_factory=crear_modelo_simulado,
               crm_transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = crear_engine(config.database_url)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with httpx.AsyncClient(transport=crm_transport) as client:
                app.state.crm = CRMClient(client, config)
                yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Softgic - Analisis de solicitudes", lifespan=lifespan)

    @app.post("/solicitudes/analizar", response_model=Analisis, status_code=201)
    async def analizar_solicitud(solicitud: Solicitud):
        try:
            async with app.state.sessions() as session:
                if await session.get(AnalisisGuardado, solicitud.id):
                    raise HTTPException(409, "El id ya tiene un analisis guardado")
            try:
                async with asyncio.timeout(30):
                    resultado = await analizar(solicitud, model_factory(), app.state.crm, config)
            except Exception:
                logger.error("No se pudo completar el analisis")
                raise HTTPException(502, "No se pudo completar el analisis") from None
            async with app.state.sessions.begin() as session:
                session.add(AnalisisGuardado(id=solicitud.id, contenido=resultado.model_dump(mode="json")))
        except IntegrityError:
            raise HTTPException(409, "El id ya tiene un analisis guardado") from None
        except SQLAlchemyError:
            logger.error("Fallo de persistencia")
            raise HTTPException(503, "Almacenamiento temporalmente no disponible") from None
        logger.info("Analisis guardado: tokens_entrada=%d tokens_salida=%d costo_estimado=%s",
                    resultado.tokens_entrada, resultado.tokens_salida, resultado.costo_estimado)
        return resultado

    @app.get("/solicitudes/{id}", response_model=Analisis)
    async def obtener_solicitud(id: str):
        try:
            async with app.state.sessions() as session:
                registro = await session.get(AnalisisGuardado, id)
                if registro is None:
                    raise HTTPException(404, "Solicitud no encontrada")
                return Analisis.model_validate(registro.contenido)
        except SQLAlchemyError:
            raise HTTPException(503, "Almacenamiento temporalmente no disponible") from None

    return app


app = create_app()
