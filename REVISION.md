# Parte 3: revisión de código

Revisión del fragmento del enunciado. Los ejemplos siguientes son propuestas para
ese servicio de tickets; no añaden una ruta ni dependencias al backend de la parte 1.

## Problemas, de mayor a menor gravedad

1. **Crítico: inyección SQL.** `ticket_id` se interpola en SQL; permite alterar el
   filtro y consultar datos ajenos. `text()` no protege una cadena ya interpolada.
   Usar parámetros vinculados.
2. **Crítico: credenciales en código y cuenta de BD privilegiada.** La clave del
   proveedor y la contraseña de PostgreSQL quedan expuestas a cualquiera con acceso
   al repositorio. Si fueron reales, revocarlas/rotarlas y revisar su uso; quitarlas
   del archivo no elimina la exposición histórica. Inyectar secretos desde el entorno
   o Key Vault y usar una cuenta con permisos mínimos.
3. **Alto: ausencia de autenticación y autorización por ticket.** Cualquier consumidor
   puede solicitar un resumen de cualquier identificador y generar gasto. Validar el
   token y su permiso, y limitar la consulta al propietario y tenant autenticados.
4. **Alto: inyección de instrucciones en el prompt.** Se pide expresamente obedecer
   el contenido del ticket. Separar instrucciones del sistema y contenido no confiable,
   pedir únicamente un resumen y validar la salida. Esa separación reduce el riesgo,
   pero no garantiza inmunidad; probar tickets adversariales y no otorgar herramientas
   ni secretos al modelo.
5. **Alto: E/S bloqueante dentro de `async def`.** SQLAlchemy síncrono, `requests.get`
   y `llm.invoke` bloquean el event loop. Usar clientes asíncronos y `ainvoke`, o una
   ruta `def` con E/S síncrona y concurrencia acotada. No basta con declarar `async`.
6. **Alto: latencia y reintentos sin control explícito.** La llamada de Requests no
   tiene timeout y no existe un presupuesto total del flujo. Definir timeouts por
   dependencia, plazo total y reintentos acotados con espera progresiva para errores
   transitorios; evitar multiplicar reintentos entre capas.
7. **Alto: costo y carga crecen con cada línea.** La traducción hace una llamada por
   línea, pierde contexto y aumenta latencia y gasto. Traducir el resumen completo
   en una llamada; limitar entrada, salida, concurrencia y cuota por usuario, y medir
   tokens/costo de todas las llamadas, incluidos reintentos.
8. **Medio: ticket inexistente o texto inválido.** `fetchone()` puede devolver `None`
   y `fila[0]` provoca un 500. Responder 404 antes de invocar dependencias; rechazar
   texto nulo, vacío o demasiado largo con un error controlado.
9. **Medio: respuesta del CRM sin validación.** No se verifica el estado HTTP ni el
   esquema JSON; se puede devolver un cuerpo de error como cliente o fallar al
   decodificarlo. Usar `raise_for_status()`, un modelo de respuesta y degradación
   explícita si el CRM es opcional. Construir la query con `params`, pues el ID
   interpolado también puede introducir parámetros adicionales.
10. **Medio: errores de dependencias y contrato de respuesta sin definir.** Fallos
    de BD/modelo/CRM terminan como errores genéricos; `respuesta.content` tampoco
    tiene garantizado ser una cadena. Validar el resultado y declarar un modelo de
    respuesta; mapear fallos a estados documentados sin devolver detalles internos.
11. **Medio: exposición de información y observabilidad insuficiente.** Se envía
    el ticket completo a un proveedor y se devuelve todo el JSON del CRM. Minimizar
    datos personales y seleccionar campos permitidos. Sustituir `print` de metadatos
    completos por logs estructurados con ID de correlación, duración, uso y estado,
    sin texto sensible ni secretos.
12. **Medio: acoplamiento y recursos sin ciclo de vida explícito.** La ruta concentra
    consulta, IA, traducción y CRM; los clientes globales dificultan sustitución y
    pruebas. Separar funciones pequeñas, inyectar clientes, cerrarlos al apagar y
    probar con dobles SQL malicioso, acceso ajeno, 404, timeout, CRM inválido y costo.

## Código propuesto para los tres problemas más graves

Son fragmentos de integración, no una aplicación completa. El ejemplo de autorización
supone Entra ID con tokens de acceso v2 y permiso delegado `Tickets.Read`; requiere
`PyJWT[crypto]`. El proveedor real del fragmento requiere `langchain-openai`.
La tabla original solo muestra `id` y `texto`: para el tercer cambio se deben agregar
y poblar `tenant_id` y `propietario_id` mediante una migración. No deben recibirse
estos valores del cuerpo ni de parámetros enviados por el usuario.

### 1. Consulta parametrizada y caso inexistente

```python
from fastapi import HTTPException
from sqlalchemy import Engine, text


def obtener_texto(engine: Engine, ticket_id: str) -> str:
    with engine.connect() as connection:
        fila = connection.execute(
            text("SELECT texto FROM tickets WHERE id = :ticket_id"),
            {"ticket_id": ticket_id},
        ).mappings().first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return fila["texto"]
```

La consulta conserva el identificador como dato, incluso si contiene comillas o SQL.
El tercer fragmento sustituye esta función para añadir el control de acceso.
Referencia: [parámetros vinculados de SQLAlchemy](https://docs.sqlalchemy.org/en/21/core/connections.html).

### 2. Configuración sin secretos incrustados

```python
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine


class Settings(BaseSettings):
    database_url: SecretStr
    openai_api_key: SecretStr
    model_config = SettingsConfigDict(extra="ignore")


def crear_clientes(settings: Settings):
    engine = create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        hide_parameters=True,
    )
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=10,
        max_retries=2,
        max_tokens=500,
    )
    return engine, llm
```

Crear estos clientes durante el arranque con `Settings()` y liberar el engine con
`engine.dispose()` al apagar. Las variables obligatorias ausentes impiden arrancar.
Los límites del modelo son iniciales; todavía se necesita un plazo total del flujo.
`SecretStr` oculta la representación del valor, no cifra ni reemplaza un gestor de
secretos. No registrar la URL ni el resultado de `get_secret_value()`.
Referencia: [integración oficial de LangChain](https://reference.langchain.com/python/langchain-openai/langchain_openai).

### 3. Identidad verificada y autorización en la consulta

```python
import os
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine, text

TENANT_ID = str(UUID(os.environ["ENTRA_TENANT_ID"]))
AUDIENCE = os.environ["ENTRA_API_AUDIENCE"]
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
keys = jwt.PyJWKClient(
    f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
    timeout=5,
)
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    usuario_id: str


def autenticar(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
) -> Principal:
    unauthorized = HTTPException(
        status_code=401,
        detail="Token inválido o ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        key = keys.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "nbf", "tid", "oid"]},
        )
        tenant_id = str(UUID(claims["tid"]))
        usuario_id = str(UUID(claims["oid"]))
        if tenant_id != TENANT_ID:
            raise unauthorized
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(503, "Proveedor de identidad no disponible") from exc
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
        raise unauthorized from exc
    scopes = claims.get("scp", "")
    if not isinstance(scopes, str) or "Tickets.Read" not in scopes.split():
        raise HTTPException(403, "Permiso insuficiente")
    return Principal(tenant_id=tenant_id, usuario_id=usuario_id)


def obtener_texto_autorizado(
    engine: Engine, ticket_id: str, principal: Principal
) -> str:
    with engine.connect() as connection:
        fila = connection.execute(
            text(
                "SELECT texto FROM tickets WHERE id = :ticket_id "
                "AND tenant_id = :tenant_id AND propietario_id = :usuario_id"
            ),
            {
                "ticket_id": ticket_id,
                "tenant_id": principal.tenant_id,
                "usuario_id": principal.usuario_id,
            },
        ).mappings().first()
    if fila is None:
        raise HTTPException(404, "Ticket no encontrado")
    return fila["texto"]
```

En la ruta, inyectar `principal: Annotated[Principal, Depends(autenticar)]` y llamar
a `obtener_texto_autorizado(engine, ticket_id, principal)` antes del modelo o CRM.
Usar una ruta `def` si se mantienen estos clientes síncronos; no ejecutar esta consulta
directamente en el event loop. El 404 también cubre tickets ajenos para no revelar su
existencia. El ejemplo aplica propiedad individual; permisos de agentes de soporte
requerirían una política explícita. Validar con tokens de prueba firmados: firma,
issuer o audience incorrectos, expiración, scope ausente y propietario/tenant ajenos.
Referencias: [validación de claims en Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation)
y [API de PyJWT](https://pyjwt.readthedocs.io/en/latest/api.html).

## Comentario para la solicitud de cambio

Gracias por dejar visible el flujo completo de resumen, traducción y consulta al CRM.
Antes de integrar necesitamos resolver la consulta SQL interpolada, extraer y rotar
las credenciales si fueron reales, y verificar identidad y acceso a cada ticket.
Adjunto propuestas concretas para esos tres cambios. Después acotemos las llamadas
externas, eliminemos el bloqueo del event loop y traduzcamos el resumen en una sola
llamada. Agreguemos pruebas sin servicios reales para acceso ajeno, ticket inexistente,
entrada maliciosa y fallos del proveedor. Podemos revisar juntos la primera prueba
y usarla como guía para los demás casos.
