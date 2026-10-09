# Microsoft Entra ID (propuesta; autenticación no implementada)
Registraría la SPA y la API en Entra ID, con redirect URI de tipo SPA y un scope delegado `Solicitudes.Analizar`.
Usaría MSAL Angular/MSAL Browser con Authorization Code + PKCE; tenant ID y client ID son configuración pública.
Nunca incluiría client secrets, claves del modelo ni credenciales de la API en el navegador.
Tras iniciar sesión, solicitaría un access token para el scope de la API con `acquireTokenSilent`; si requiere interacción, usaría redirect.
Un interceptor MSAL añadiría `Authorization: Bearer <access_token>` exclusivamente a las peticiones de nuestra API en su mapa de recursos protegidos.
El interceptor no enviaría tokens a otros destinos; no usaría el ID token como credencial de la API.
La API validaría firma mediante JWKS, issuer, audience, expiración, tenant y scope, y autorizaría el acceso al recurso.
Usaría HTTPS, permisos mínimos y caché en memoria; un guard mejora la navegación, pero la autorización corresponde al servidor.
Referencia: [flujo oficial con PKCE](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow).
