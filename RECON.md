# RECON – Aquanet (SOCV) de Sedapal

Estado: **preliminar**. Fuentes: (a) lectura del bundle Angular sin minificar
(`https://webapp16.sedapal.com.pe/socv/main.js`, `environment.ts`, `api.service.ts`,
`auth.service.ts`, interceptores); (b) dry-run headless de la página de login sin credenciales.
Lo marcado como ⏳ se confirma al correr `python -m aquanet recon` con tu sesión
(ver `recon/endpoints_summary.md` y `recon/api_calls.json`).

## 1. URLs

| Qué                | URL |
|--------------------|-----|
| SPA (Angular 7/8)  | `https://webapp16.sedapal.com.pe/socv/` (hash routing: `#/iniciar-sesion`, `#/`, `#/consulta-recibos`, `#/cobranzas`, …) |
| API base           | `https://webapp16.sedapal.com.pe/OficinaComercialVirtual/api` |

`aquanet.sedapal.com.pe` **no resuelve** por DNS; la URL correcta es la de arriba.

## 2. Mecanismo de autenticación (dos niveles)

### 2.1 Token de aplicación (confirmado ✅ en dry-run)

Al cargar la SPA, antes de cualquier login de usuario, `MainService.setToken()` hace:

```
POST /OficinaComercialVirtual/api/login
Content-Type: application/x-www-form-urlencoded
username=OCV_Sedapal&password=OCV0109        <- credenciales fijas embebidas en environment.ts
```

Respuesta:

```json
{"cRESP_SP": "Ejecución Correcta", "nRESP_SP": 1, "bRESP": {"token": "eyJhbGciOiJIUzI1NiJ9...."}}
```

- El token es un **JWT HS256** (~116 chars). La SPA lo guarda en `localStorage["sedtoken"]` como
  `{"token": "...", "expires_at": <epoch ms>}` con expiración local de **60 min**; lo renueva
  llamando otra vez a `/login` cuando expira (`verifyToken`).
- `BasicAuthInterceptor` añade a **toda** petición a la API el header
  `Authorization: <token>` (sin prefijo `Bearer`), salvo a `/login`, vnforapps (Visa) e ipify.
- El servidor también setea cookie `JSESSIONID` (Java/Spring). ⏳ Verificar si es necesaria
  además del header, o si con solo el header basta.

### 2.2 Login de usuario (⏳ confirmar con HAR)

```
POST /OficinaComercialVirtual/api/autenticacion-usuario/aut-nuevo-usu
Authorization: <token app>
Content-Type: application/json
{"correo": "<SEDAPAL_USER>", "clave": "<SEDAPAL_PASS>", "flagChannel": "1"}
```

Respuesta esperada (`AuthService.login`):

- `nRESP_SP == 1` y `bRESP.flagRespuesta != 'B'` → login OK. `bRESP` es el objeto usuario
  (incluye `nis_rad` = suministro por defecto, `admin_com`, `admin_etic`, `tipo_docu`, `nro_doc`…).
  La SPA guarda `localStorage["sedapal"] = {"user": bRESP, "correo": ..., "type": "mail", "expires_at": now+60min}`
  y `localStorage["suministro"] = bRESP.nis_rad`.
- `nRESP_SP == 2` → **código de verificación por correo** (diálogo `app-code-confirm`, 4 dígitos).
  Se confirma con `POST /registro-usuario/valida-codigo-confirmacion {"codeVerify": "1234", "correo": ...}`;
  reenvío con `POST /registro-usuario/enviar-codigo-confirmacion {"correo": ...}`.
  **Este es el punto donde el flujo cae a manual** (`page.pause()` en `browser.login`).
- `bRESP.flagRespuesta == 'A'` → correo no registrado.
- `nRESP_SP == 0` → error (`cRESP_SP` trae el mensaje).

**No hay captcha en el formulario de login** (dry-run: 0 iframes de reCAPTCHA). `ngx-recaptcha2`
(site key `6Le5QKMU…`) solo está en registro y olvido de contraseña.

Importante: la "sesión de usuario" **no parece devolver un token propio**; las llamadas de datos
siguen usando el token de aplicación y envían `nis_rad` + `auth_correo` en el body. ⏳ Confirmar
en el HAR si el backend valida realmente `auth_correo` contra una sesión servidor (JSESSIONID) o si
cualquier `nis_rad` es consultable solo con el token de app.

## 3. Endpoints de datos (todos `POST`, JSON, header `Authorization`)

Formato común de respuesta: `{"nRESP_SP": 1|0|2, "cRESP_SP": "mensaje", "cRESP_SP2": ..., "bRESP": <payload>}`.

| Propósito | Path (relativo a API base) | Body (según el código de la SPA) |
|-----------|----------------------------|----------------------------------|
| Lista de suministros de la cuenta | `/suministros/lista-nis` | `{"nis_rad": "<7 dígitos>", "auth_correo": "<correo>", "flagChannel": 1, "login_type": "mail"}` |
| Detalle del suministro (dirección, deuda total, cliente) | `/suministros/detalle-nis` | `{"nis_rad", "auth_correo", "flag_multiple", "flagChannel"}` |
| **Histórico de consumo** (gráfico "Ver gráficos de consumo") | `/suministros/historico-consumo` | `{"nis_rad": "<NIS>"}` |
| **Recibos pagados** (paginado) | `/recibos/lista-recibos-pagados-nis` | `{"nis_rad": "<NIS>", "page_num": 1, "page_size": 10}` |
| **Recibos pendientes / deuda** (paginado) | `/recibos/lista-recibos-deudas-nis` | `{"nis_rad": "<NIS>", "page_num": 1, "page_size": 10}` |
| Detalle de un recibo | `/recibos/detalle-recibo` | el objeto recibo tal cual viene en la lista |
| Detalle de pagos | `/recibos/detalle-pagos` | objeto recibo |
| PDF del recibo | `/recibos/recibo-pdf` | objeto recibo |
| Datos del usuario | `/registro-usuario/obtener-datos` | ⏳ |

⏳ **Forma exacta del JSON de `bRESP`** para consumo y recibos: se documenta tras el recon
(auto-generado en `recon/endpoints_summary.md`). La UI del gráfico usa dos series:
"Consumo Metros Cubicos" e "Importe de Consumo" por periodo, así que `bRESP` de
`historico-consumo` debería ser una lista con al menos periodo, m³ e importe.

## 4. Navegación que dispara las llamadas (para `browser.visit_data_sections`)

1. `#/` (dashboard `SuministroComponent`): al cargar → `lista-nis` y `detalle-nis`.
   Botón **"Ver gráficos de consumo"** → diálogo `HistoricoConsumoComponent` → `historico-consumo`.
2. `#/consulta-recibos`: → `lista-recibos-deudas-nis` y `lista-recibos-pagados-nis`
   (`page_size` 10, paginador Material).

## 5. Pendientes que resuelve el recon con tu sesión

- [ ] Confirmar path y respuesta de `aut-nuevo-usu`, y si tu cuenta cae en `nRESP_SP = 2` (código por correo).
- [ ] Capturar `bRESP` real de `historico-consumo`, `lista-recibos-pagados-nis`, `lista-recibos-deudas-nis`.
- [ ] Verificar si `JSESSIONID` es obligatoria para las llamadas de datos (probar con httpx solo con header).
- [ ] Verificar si `auth_correo`/sesión de usuario es validada server-side (seguridad del endpoint).
