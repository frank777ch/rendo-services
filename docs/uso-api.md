# Cómo hacer llamadas a la API

La API entrega datos crudos (consumo, montos por concepto, tarifas, lecturas y PDF) de agua
(Sedapal), gas (Cálidda) y luz (Luz del Sur). Todas las llamadas son **GET** y llevan el header
`Authorization: Bearer <API_TOKEN>`, salvo `/health`.

- **Base en producción**: `https://rendo-services.duckdns.org`
- **Base local** (si corres `python -m rendo serve`): `http://localhost:8000`
- `proveedor` = `sedapal` (agua) | `calidda` (gas) | `luzdelsur` (luz)
- `suministro` = tu número de suministro / código de cliente
- `periodo` = un mes en formato `YYYY-MM` (p.ej. `2026-07`)

En los ejemplos:

```bash
TOKEN=pega-aqui-tu-API_TOKEN
BASE=https://rendo-services.duckdns.org
AUTH="Authorization: Bearer $TOKEN"
```

## 1. Estado del servicio (sin token)

```bash
curl "$BASE/health"
# {"ok":true,"proveedores":["sedapal","calidda","luzdelsur"]}
```

## 2. Qué suministros ve la cuenta

```bash
curl -H "$AUTH" "$BASE/proveedores"
```

## 3. Últimos N recibos

```bash
curl -H "$AUTH" "$BASE/sedapal/5998198/recibos?limit=3"
```

`limit` por defecto 12. Agrega `&pdf=true` para incluir el PDF en base64 dentro del JSON.

## 4. Recibos por rango de meses

```bash
curl -H "$AUTH" "$BASE/luzdelsur/1491533/recibos?desde=2026-01&hasta=2026-08"
```

Devuelve una lista de recibos, del más reciente al más antiguo.

## 5. Un recibo de un mes exacto

```bash
curl -H "$AUTH" "$BASE/sedapal/5998198/recibo/2026-07"
```

Devuelve un solo recibo con todos sus campos. Si no existe, responde 404.

## 6. Consumo mensual

```bash
curl -H "$AUTH" "$BASE/luzdelsur/1491533/consumo"
# [{"periodo":"2026-08","consumo":267.3,"importe":240.81}, ...]
```

## 7. PDF de un recibo

```bash
# por mes:
curl -H "$AUTH" "$BASE/sedapal/5998198/recibo/2026-07/pdf" -o recibo.pdf
# por número de recibo:
curl -H "$AUTH" "$BASE/sedapal/5998198/recibo/5998198198/pdf" -o recibo.pdf
```

## 8. Todo de una (para volcar a una hoja)

```bash
# JSON anidado (recibos + consumo de todos los suministros del .env):
curl -H "$AUTH" "$BASE/sync?limit=1"

# filas planas, una por recibo (ideal para Google Sheets / n8n):
curl -H "$AUTH" "$BASE/sync/rows?limit=1"
```

## Campos de cada recibo

```
proveedor, servicio, suministro, titular, direccion, periodo,
fecha_emision, fecha_vencimiento, numero_recibo,
consumo, unidad, lectura_anterior, lectura_actual, lectura_diferencia,
precio_unitario, importe_total, moneda, estado,
conceptos: [ {descripcion, monto} ],
tarifa:    [ {rango, agua, alcantarillado} ]   (solo agua)
# parseados del PDF:
fecha_tarifa, periodo_inicio, periodo_fin            (agua)
fecha_lectura_actual, fecha_lectura_anterior         (luz)
```

## Desde n8n

Nodo **HTTP Request**: método GET, la URL del endpoint, y Authentication tipo *Header Auth*
con header `Authorization` = `Bearer <API_TOKEN>`. Para volcar a Sheets, usa `/sync/rows`
y conéctalo al nodo de Google Sheets. Ver [google-sheets.md](google-sheets.md).

## Notas de alcance

- **Agua**: cualquier NIS, cualquier mes desde ~2010, sin DNI.
- **Luz**: el recibo del mes actual es público por suministro; el historial (desde ~2006)
  requiere que el suministro esté en tu cuenta.
- **Gas**: por mes/año, solo suministros de tu cuenta.
- No se usa OCR: los montos salen del JSON de las empresas y lo que solo está en el PDF se lee
  de su **texto**.
