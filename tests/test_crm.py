import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.crm import CRMClient


@pytest.mark.parametrize("statuses,expected_calls,expected_delays,success", [
    ([429, 500, 200], 3, [0.25, 0.5], True),
    ([500, 500, 500], 3, [0.25, 0.5], False),
    ([404], 1, [], False),
])
async def test_reintentos_progresivos(monkeypatch, statuses, expected_calls, expected_delays, success):
    calls = []
    sleep = AsyncMock()
    monkeypatch.setattr("app.crm.asyncio.sleep", sleep)

    def handler(request):
        calls.append(request)
        return httpx.Response(statuses[len(calls) - 1], json={
            "id": "c1", "nombre": "Cliente", "plan": "basico",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CRMClient(client, Settings(_env_file=None)).consultar("c1")
    assert (result is not None) == success
    assert len(calls) == expected_calls
    assert [call.args[0] for call in sleep.await_args_list] == expected_delays


async def test_tiempo_total_limita_espera_y_peticiones():
    calls = []

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(10)
        return httpx.Response(200)

    settings = Settings(_env_file=None, crm_total_timeout=0.02)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        async with asyncio.timeout(1):
            assert await CRMClient(client, settings).consultar("c1") is None
    assert len(calls) == 1


async def test_error_transporte_reintenta(monkeypatch):
    calls = []
    monkeypatch.setattr("app.crm.asyncio.sleep", AsyncMock())

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("Sin conexion", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await CRMClient(client, Settings(_env_file=None)).consultar("c1") is None
    assert len(calls) == 3
