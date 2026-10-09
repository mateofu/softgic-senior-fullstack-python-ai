# Softgic — Parte 1

Servicio de análisis con Python 3.11+, FastAPI, LangGraph y SQLAlchemy.

## Instalar y ejecutar (PowerShell)

```powershell
uv venv --python 3.12
uv pip install -r requirements.txt
Copy-Item .env.example .env
uv run uvicorn mock_crm:app --port 9000
```

En otra terminal:

```powershell
uv run uvicorn app.main:app --reload
```

También puede usar `python -m venv .venv`, activar el entorno e instalar con
`python -m pip install -r requirements.txt`. La documentación interactiva está
en http://localhost:8000/docs.

```powershell
$body = @{ id = 's1'; texto = 'No puedo acceder al sistema'; cliente_id = 'c1' } | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/solicitudes/analizar -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
Invoke-RestMethod http://localhost:8000/solicitudes/s1
```

POST devuelve 201; un identificador repetido devuelve 409 y nunca sobrescribe
el análisis. GET devuelve 404 si no existe. Entradas inválidas devuelven 422;
errores del modelo 502; errores de almacenamiento 503.

## Configuración

Consulte `.env.example`. No incluya `.env` ni secretos en Git.
`DATABASE_URL` admite `sqlite:///...`, `sqlite+aiosqlite:///...`,
`postgresql://usuario:clave@host/base` o `postgresql+psycopg://...`.
Las tablas se crean al iniciar para esta prueba; en producción usaría migraciones.
`CRM_URL` es la URL base del CRM. Se reintentan 429, 5xx y errores de transporte,
hasta `CRM_MAX_ATTEMPTS` intentos totales, con espera
`CRM_BASE_DELAY * 2**intento`, timeout por petición y límite total incluyendo esperas.
Respuestas inválidas o errores 4xx distintos de 429 no se reintentan.
Si el CRM falla, la respuesta incluye `cliente: null` y el análisis continúa.

Se utiliza `FakeListChatModel`, permitido por el enunciado, sin clave ni llamadas
a proveedores. Devuelve una clasificación fija técnico/alta y una respuesta fija;
no representa calidad real de clasificación. Cada solicitud crea su propia instancia.
La clasificación JSON se valida con Pydantic. El grafo consulta al CRM solamente
para prioridad alta y entrega sus datos al nodo que propone la respuesta.
Puede inyectarse otro `BaseChatModel` mediante `model_factory` en `create_app`.

Se acumulan los tokens de ambos nodos. Si el modelo reporta uso se utiliza ese dato;
en el simulado se estiman contando palabras y se marca `uso_estimado: true`.
El costo estimado en USD es `(entrada * precio_entrada + salida * precio_salida) / 1000000`.
Los precios son configurables y valen cero por defecto porque el modelo es simulado.
Uso y costo quedan persistidos junto al análisis y se registran sin texto del cliente.
El análisis tiene un límite total de 30 segundos.

## Pruebas

```powershell
uv run pytest -q
```

No requieren CRM, PostgreSQL, claves ni acceso a Internet. Usan `MockTransport`,
modelo simulado y SQLite temporal. Cubren rutas por prioridad, costo, degradación,
salida inválida, reintentos, tiempos límite, validación, duplicados y persistencia.

## Docker

```powershell
docker build -t softgic-api .
docker run --rm -p 8000:8000 -e CRM_URL=http://host.docker.internal:9000 -v softgic-data:/data softgic-api
```

Ejecute el CRM en el host con `--host 0.0.0.0` para que el contenedor pueda acceder.
La API corre como usuario sin privilegios; SQLite se conserva en el volumen.
Para PostgreSQL proporcione `DATABASE_URL` al contenedor mediante un archivo de
entorno local protegido o el gestor de secretos del entorno de despliegue.

La parte 1 está implementada. La propuesta de la parte 2 está en
[ARQUITECTURA.md](ARQUITECTURA.md). La revisión de código de la parte 3 está en
[REVISION.md](REVISION.md). La parte 4 está en [frontend/](frontend/) y la parte 5
en [RESPUESTAS.md](RESPUESTAS.md).

## Frontend (parte 4)

Se entregan un componente standalone, su plantilla y un servicio, como permite el
enunciado; no se incluye un proyecto Angular completo ni scripts de compilación.
Para integrarlos en una aplicación Angular 21, copie los tres archivos, registre
`provideHttpClient()` en los providers de `bootstrapApplication` e importe
`SolicitudesComponent` en el componente padre para usar `<app-solicitudes />`.
Requiere `@angular/core`, `@angular/common`, `@angular/forms` y `rxjs` del proyecto
anfitrión, con versiones compatibles (consulte [Angular](https://angular.dev/reference/versions)).

El servicio usa la ruta relativa `/solicitudes/analizar`. En desarrollo configure
el proxy de `ng serve` para `/solicitudes/**` hacia `http://localhost:8000`;
en producción configure el proxy inverso para enviar `/solicitudes/` a la API
bajo el mismo origen. Así no se necesita modificar CORS en el backend.
El formulario envía `id`, `texto` y `cliente_id`, bloquea envíos simultáneos y muestra
carga, errores y resultado. No reintenta automáticamente el POST.
La integración propuesta de identidad está en [frontend/README.md](frontend/README.md).
