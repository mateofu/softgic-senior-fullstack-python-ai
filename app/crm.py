import asyncio
import logging
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import Cliente

logger = logging.getLogger(__name__)


class CRMClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client = client
        self.settings = settings

    async def consultar(self, cliente_id: str) -> Cliente | None:
        try:
            async with asyncio.timeout(self.settings.crm_total_timeout):
                return await self._consultar(cliente_id)
        except TimeoutError:
            logger.warning("CRM: tiempo total agotado")
            return None

    async def _consultar(self, cliente_id: str) -> Cliente | None:
        url = f"{str(self.settings.crm_url).rstrip('/')}/clientes/{quote(cliente_id, safe='')}"
        for attempt in range(self.settings.crm_max_attempts):
            try:
                response = await self.client.get(url, timeout=self.settings.crm_request_timeout)
                response.raise_for_status()
                cliente = Cliente.model_validate(response.json())
                if cliente.id != cliente_id:
                    logger.warning("CRM: identificador inesperado")
                    return None
                return cliente
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 and exc.response.status_code < 500:
                    logger.warning("CRM: error HTTP no reintentable")
                    return None
            except httpx.TransportError:
                pass
            except (ValidationError, ValueError):
                logger.warning("CRM: respuesta invalida")
                return None
            if attempt + 1 < self.settings.crm_max_attempts:
                await asyncio.sleep(self.settings.crm_base_delay * 2**attempt)
        logger.warning("CRM: intentos agotados")
        return None
