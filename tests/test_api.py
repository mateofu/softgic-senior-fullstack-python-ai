import httpx
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import Settings
from app.main import create_app


def test_api_persiste_valida_y_controla_duplicados(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
                        crm_max_attempts=1)
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    app = create_app(settings, crm_transport=transport)
    body = {"id": "s1", "texto": "No funciona", "cliente_id": "c1"}
    with TestClient(app) as client:
        assert client.get("/solicitudes/no-existe").status_code == 404
        response = client.post("/solicitudes/analizar", json=body)
        assert response.status_code == 201
        assert client.get("/solicitudes/s1").json() == response.json()
        assert client.post("/solicitudes/analizar", json=body).status_code == 409
        assert client.post("/solicitudes/analizar", json={**body, "texto": " "}).status_code == 422
    with TestClient(create_app(settings, crm_transport=transport)) as client:
        assert client.get("/solicitudes/s1").json() == response.json()


def test_error_modelo_no_persiste(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    app = create_app(settings, model_factory=lambda: FakeListChatModel(responses=["no es JSON"]))
    with TestClient(app) as client:
        result = client.post("/solicitudes/analizar", json={"id": "s1", "texto": "Ayuda", "cliente_id": "c1"})
        assert result.status_code == 502
        assert client.get("/solicitudes/s1").status_code == 404
