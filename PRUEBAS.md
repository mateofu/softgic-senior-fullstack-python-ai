# Validación previa a entrega

Ejecutada el 9 de octubre de 2026.

## Backend y Docker

- `python -m pytest -q`: **17 pruebas aprobadas**.
- `docker build -t softgic-api:validation .`: construcción correcta, con capas en caché.
- Contenedores independientes para API y CRM simulado, conectados mediante una red Docker de prueba.
- API expuesta únicamente en `127.0.0.1:18000`; ejecución como `appuser` (UID 1000).
- Verificados POST 201, GET 200 con contenido idéntico, duplicado 409, entrada inválida 422 y solicitud inexistente 404.
- Respuesta con datos del CRM recibidos correctamente.
- Persistencia SQLite verificada después de eliminar y recrear el contenedor API con el mismo volumen.

## Angular

Aplicación temporal en `.validation-angular/`, excluida de Git y del contexto Docker.
Se copiaron sin cambios los tres archivos de `frontend/` y se registró `provideHttpClient()`.

- Angular 21, TypeScript 5.9 y Node 24.18.0.
- `ng build`: compilación correcta con `strict` y `strictTemplates` activados.
- `ng serve --host 127.0.0.1 --port 14200`: inicio correcto; proxy `/solicitudes/**` hacia `http://127.0.0.1:18000`.
- `ng test`: **2 pruebas aprobadas** con Vitest y jsdom.
- Integración real: evento submit del formulario → servicio Angular → proxy de desarrollo → API Docker; se verificaron estado de carga, botón deshabilitado, resultado renderizado y consulta del registro persistido.
- Segundo envío del mismo ID: mensaje de duplicado y botón habilitado nuevamente.
- Texto compuesto únicamente por espacios: rechazo antes del envío.

La prueba utiliza `withFetch()` y un interceptor de prueba que antepone el origen del servidor Angular a la URL relativa, necesario al ejecutarse desde Node. No sustituye la API ni simula sus respuestas HTTP.

No se realizó una revisión visual en un navegador real: no había navegador conectado. El DOM y los eventos se validaron con jsdom. El modelo sigue siendo el simulado previsto por el proyecto.

## Resultado

No fue necesario modificar el código de la API ni los archivos Angular. Los servidores y contenedores de prueba se detuvieron al terminar. La aplicación temporal y el volumen de prueba se conservan para inspección local.
