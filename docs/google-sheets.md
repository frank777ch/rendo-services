# Conectar la API a Google Sheets

Tu API expone JSON protegido con un bearer token. Hay dos formas de llevarlo a Sheets.

## Opción A — n8n (recomendada, ya tienes n8n en tu VPS)

Flujo en n8n:

1. **Schedule** o **Webhook** (tu "botón").
2. **HTTP Request**:
   - Método: `GET`
   - URL: `https://TU-DOMINIO/sync/rows?limit=1`
   - Authentication: *Header Auth* → Header `Authorization`, valor `Bearer <API_TOKEN>`.
3. **Google Sheets → Append or Update Row**: mapea las columnas del JSON
   (`proveedor`, `servicio`, `suministro`, `periodo`, `consumo`, `importe_total`, ...).

n8n hace la orquestación y la escritura; la API solo entrega los datos.

## Opción B — Google Apps Script (directo, sin servidor extra)

`IMPORTDATA` de Sheets no puede mandar el header del token, así que se usa Apps Script.
En tu hoja: **Extensiones → Apps Script**, pega esto, cambia la URL y el token, y ejecútalo
(o prográmalo con un disparador de tiempo). Escribe una fila por recibo.

```javascript
const API_URL = 'https://TU-DOMINIO';        // tu API
const API_TOKEN = 'pon-tu-token-secreto';    // el API_TOKEN del .env

function actualizarRecibos() {
  const resp = UrlFetchApp.fetch(API_URL + '/sync/rows?limit=1', {
    method: 'get',
    headers: { Authorization: 'Bearer ' + API_TOKEN },
    muteHttpExceptions: true,
  });
  const filas = JSON.parse(resp.getContentText());
  const hoja = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Recibos')
            || SpreadsheetApp.getActiveSpreadsheet().insertSheet('Recibos');

  const cols = ['proveedor','servicio','suministro','periodo','fecha_emision',
    'fecha_vencimiento','numero_recibo','consumo','unidad','lectura_anterior',
    'lectura_actual','lectura_diferencia','precio_unitario','importe_total','estado'];

  if (hoja.getLastRow() === 0) hoja.appendRow(cols);       // encabezados una vez
  filas.forEach(f => hoja.appendRow(cols.map(c => f[c])));
}
```

Para el consumo histórico (12 meses) usa el endpoint `/{proveedor}/{suministro}/consumo`
o `/sync` (que trae `recibos` y `consumo`) y adapta el script.

## Endpoints disponibles

| Endpoint | Qué devuelve |
|---|---|
| `GET /health` | estado (sin token) |
| `GET /proveedores` | proveedores y sus suministros |
| `GET /{proveedor}/{suministro}/recibos?limit=N&pdf=false` | recibos normalizados (todos los campos) |
| `GET /{proveedor}/{suministro}/consumo` | consumo mensual |
| `GET /{proveedor}/{suministro}/recibo/{numero}/pdf` | PDF del recibo |
| `GET /sync?limit=N` | todo: recibos + consumo de todos los suministros |
| `GET /sync/rows?limit=N` | filas planas (una por recibo) para hoja de cálculo |

`proveedor` = `sedapal` | `calidda` | `luzdelsur`. Todos requieren el header
`Authorization: Bearer <API_TOKEN>` salvo `/health`.
