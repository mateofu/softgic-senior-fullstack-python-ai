from decimal import Decimal

import httpx
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import ValidationError

from app.config import Settings
from app.crm import CRMClient
from app.graph import analizar
from app.schemas import Solicitud


@pytest.mark.parametrize("prioridad,consultas", [("alta", 1), ("media", 0), ("baja", 0)])
async def test_grafo_enruta_y_calcula_costo(prioridad, consultas):
    llamadas = []

    def handler(request):
        llamadas.append(request)
        return httpx.Response(200, json={"id": "c1", "nombre": "Ana", "plan": "premium"})

    model = FakeListChatModel(responses=[
        '{"categoria":"técnico","prioridad":"' + prioridad + '"}', "Respuesta sugerida",
    ])
    settings = Settings(_env_file=None, input_price_per_million=Decimal("2"),
                        output_price_per_million=Decimal("4"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await analizar(Solicitud(id="s1", texto="No funciona", cliente_id="c1"),
                                model, CRMClient(client, settings), settings)
    assert len(llamadas) == consultas
    assert (result.cliente is not None) == (prioridad == "alta")
    assert result.respuesta == "Respuesta sugerida"
    assert result.tokens_entrada > 0 and result.tokens_salida > 0
    assert result.uso_estimado
    assert result.costo_estimado == (Decimal(result.tokens_entrada) * 2
                                     + Decimal(result.tokens_salida) * 4) / 1_000_000


async def test_grafo_continua_si_crm_falla():
    settings = Settings(_env_file=None, crm_max_attempts=1)
    model = FakeListChatModel(responses=[
        '{"categoria":"otro","prioridad":"alta"}', "Seguiremos revisando",
    ])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        result = await analizar(Solicitud(id="s1", texto="Ayuda", cliente_id="c1"),
                                model, CRMClient(client, settings), settings)
    assert result.cliente is None
    assert result.respuesta == "Seguiremos revisando"


async def test_clasificacion_invalida_se_rechaza():
    settings = Settings(_env_file=None)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as client:
        with pytest.raises(ValidationError):
            await analizar(Solicitud(id="s1", texto="Ayuda", cliente_id="c1"),
                           FakeListChatModel(responses=['{"categoria":"inventada","prioridad":"alta"}']),
                           CRMClient(client, settings), settings)


async def test_datos_crm_llegan_al_prompt_de_respuesta():
    prompts = []

    class CapturarPrompt(BaseCallbackHandler):
        def on_chat_model_start(self, serialized, messages, **kwargs):
            prompts.append(messages[0][-1].content)

    model = FakeListChatModel(responses=[
        '{"categoria":"facturación","prioridad":"alta"}', "Revisaremos su factura",
    ], callbacks=[CapturarPrompt()])
    settings = Settings(_env_file=None)
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={
        "id": "c1", "nombre": "Ana", "plan": "premium",
    }))
    async with httpx.AsyncClient(transport=transport) as client:
        await analizar(Solicitud(id="s1", texto="Factura incorrecta", cliente_id="c1"),
                       model, CRMClient(client, settings), settings)
    assert '"nombre": "Ana"' in prompts[1]
    assert '"plan": "premium"' in prompts[1]


async def test_uso_reportado_acumula_ambos_nodos_sin_estimacion():
    model = FakeMessagesListChatModel(responses=[
        AIMessage(content='{"categoria":"otro","prioridad":"baja"}',
                  usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}),
        AIMessage(content="Respuesta sugerida",
                  usage_metadata={"input_tokens": 200, "output_tokens": 30, "total_tokens": 230}),
    ])
    settings = Settings(_env_file=None, input_price_per_million=Decimal("2"),
                        output_price_per_million=Decimal("4"))

    def handler(request):
        pytest.fail("Una solicitud de prioridad baja no debe consultar el CRM")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await analizar(Solicitud(id="s1", texto="Ayuda", cliente_id="c1"),
                                model, CRMClient(client, settings), settings)
    assert result.tokens_entrada == 300
    assert result.tokens_salida == 50
    assert result.costo_estimado == Decimal("0.0008")
    assert result.uso_estimado is False
