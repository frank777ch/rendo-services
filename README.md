# rendo-services

Conector de servicios para la app **rendo** (gestión de arrendamientos). Extrae datos crudos
(consumo, recibos, montos por concepto y PDF) de:

| Proveedor | Servicio | Login | Captcha | Navegador |
|---|---|---|---|---|
| **Sedapal** | agua | token de app fijo | no | no |
| **Cálidda** | gas | tu cuenta | no | no |
| **Luz del Sur** | luz | tu cuenta | no | no |

Todo por HTTP (`httpx`). **No usa OCR**: los montos salen del JSON de las APIs y los campos
que solo están en el PDF (tarifas, lecturas, desglose de luz) se leen del **texto** del PDF con
`pdftotext`. Se expone como una **API con bearer token** llamable desde n8n, Google Sheets o
cualquier app.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# poppler (pdftotext) para leer el texto de los PDF:
sudo dnf install poppler-utils     # Fedora   (Debian/Ubuntu: sudo apt install poppler-utils)
cp .env.example .env               # y completa tus credenciales
```

Playwright solo se necesitó para el reconocimiento inicial; **la API no lo usa**.

## Configuración (.env)

- **Sedapal**: `SUMINISTRO` (NIS de 7 dígitos, p.ej. `5998198`).
- **Cálidda**: `CALIDDA_USER`, `CALIDDA_PASS`, `CALIDDA_CLIENTES` (una cuenta ve varios).
- **Luz del Sur**: `LUZDELSUR_USER`, `LUZDELSUR_PASS`, `LUZDELSUR_SUMINISTROS`.
- **API**: `API_TOKEN` (secreto para proteger tu servicio), `API_PORT`.

## Uso

```bash
# Prueba de conexión (lista los suministros de cada proveedor)
python -m rendo probar

# Descarga todo a data/ (un JSON por proveedor + data/recibos.csv)
python -m rendo fetch --limit 12
python -m rendo fetch --limit 12 --pdf     # incluye el PDF en base64

# Levanta la API (requiere API_TOKEN en .env)
python -m rendo serve
```

## API

Protegida con `Authorization: Bearer <API_TOKEN>` (salvo `/health`).

| Endpoint | Devuelve |
|---|---|
| `GET /health` | estado (sin token) |
| `GET /proveedores` | proveedores y suministros |
| `GET /{proveedor}/{suministro}/recibos?limit=N&pdf=false` | recibos normalizados |
| `GET /{proveedor}/{suministro}/consumo` | consumo mensual |
| `GET /{proveedor}/{suministro}/recibo/{numero}/pdf` | PDF del recibo |
| `GET /sync?limit=N` | recibos + consumo de todo |
| `GET /sync/rows?limit=N` | filas planas para hoja de cálculo |

`proveedor` = `sedapal` | `calidda` | `luzdelsur`.

Cada recibo trae: `proveedor, servicio, suministro, titular, direccion, periodo, fecha_emision,
fecha_vencimiento, numero_recibo, consumo, unidad, lectura_anterior, lectura_actual,
lectura_diferencia, precio_unitario, importe_total, moneda, estado, conceptos[], tarifa[]`.

## Docker (para tu VPS junto a n8n)

```bash
docker build -t rendo-services .
docker run -d --name rendo -p 8000:8000 --env-file .env rendo-services
```

Ponlo detrás de tu proxy (Caddy/Traefik/nginx) en un subdominio, p.ej. `servicios.tudominio.com`.

## Google Sheets

Ver [docs/google-sheets.md](docs/google-sheets.md): flujo con n8n (recomendado) o script de
Apps Script listo para pegar.

## Estructura

```
rendo/
  config.py            # carga .env
  pdf_utils.py         # pdftotext + parseo numérico (sin OCR)
  providers/
    base.py            # interfaz común + esquema del recibo
    sedapal.py         # agua
    calidda.py         # gas
    luzdelsur.py       # luz
  api.py               # FastAPI + bearer token
  __main__.py          # CLI: probar / fetch / serve
docs/google-sheets.md  # integración con Sheets
Dockerfile
```

`.env`, `auth_state.json`, `data/` y `recon/` están en `.gitignore`. Nunca los commitees.
