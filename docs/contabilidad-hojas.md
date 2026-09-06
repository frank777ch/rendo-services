# Hojas de contabilidad (agua y luz) — mapeo de celdas

Los Excel de contabilidad (`CONTABILIDAD UPIS AGUA/LUZ - ROSA (2026).xlsx`) tienen **una pestaña
por mes**. Cada pestaña tiene tres tipos de celda:

- 🟨 **Entrada del recibo**: la llena la API (según el recibo del mes).
- 🟦 **Manual**: consumos de inquilinos (vienen del WhatsApp, la empresa no los da).
- ⬜ **Fórmula**: se calcula sola, no se toca.

La regla de oro para copiar/reordenar estas hojas: **no mover las celdas de cálculo ni cambiar
las fórmulas**; solo así el resultado queda idéntico. La limpieza que se hizo conserva la
cuadrícula y cambia únicamente el formato (colores, títulos, bordes) y llena las celdas de entrada.

## AGUA — celdas de entrada → campo de la API

| Celda | Concepto | Campo API (`/sedapal/{nis}/recibo/{YYYY-MM}`) |
|---|---|---|
| B2 | Fecha de la estructura tarifaria | `fecha_tarifa` |
| D4:E7 | Tarifas agua/alcantarillado por rango (0-10, 10-20, 20-50, 50+) | `tarifa[]` |
| G3 | Fecha de emisión | `fecha_emision` |
| H3 / I3 | Periodo de consumo (inicio / fin) | `periodo_inicio` / `periodo_fin` |
| H4 / I4 | Lectura anterior / actual | `lectura_anterior` / `lectura_actual` |
| H16 | Cargo Fijo | concepto "Cargo Fijo" |
| D13 | Cantidad de personas | manual |
| M10:M13 | Consumo m³ por inquilino | manual (WhatsApp) |

`J4` (consumo = I4-H4) y todo el reparto por rango/inquilino son fórmulas.

## LUZ — celdas de entrada → campo de la API

| Celda | Concepto | Campo API (`/luzdelsur/{sum}/recibo/{YYYY-MM}`) |
|---|---|---|
| J4 | Monto total | `importe_total` |
| C5 | Precio por kWh | `precio_unitario` |
| E6 / F6 | Última / anterior lectura | `lectura_actual` / `lectura_anterior` |
| E4 / F4 | Fechas de lectura | `fecha_lectura_actual` / `fecha_lectura_anterior` |
| C10 | Cargo fijo | concepto "Cargo Fijo" |
| C11 | Mant. y Repo. | concepto "Mant. y Reposición de Conexión" |
| C12 | Alumbrado Púb. | concepto "Alumbrado Público" |
| C13 | Interés Comp. | concepto "Interés Compensatorio" |
| C23 | Electrificación Rural (Ley N° 28749) | concepto "Electrificación Rural (Ley N° 28749)" |
| F11:F14 | Consumo kWh por inquilino | manual (WhatsApp) |
| C27 | Cantidad de inquilinos | manual |

El resto (consumo S/, IGV, subtotales, totales, reparto por inquilino) son fórmulas.

## Copias limpias generadas

`scripts/limpiar_hojas.py` genera la copia: toma el .xlsx original, aplica el estilo,
llena las celdas 🟨 con la API y conserva fórmulas y resultados. Se verificó celda por celda que
los valores de la API coinciden con los originales de cada mes de 2026 (por eso el total no cambia).

Los archivos son `.xlsx` (no Google Sheets nativos), en Drive: carpeta
`Documentos Personales Nuevo/CONTABILIDAD` (cuenta kevinwx501@gmail.com).

## Automatizar la escritura (pendiente)

El servicio del VPS no tiene credenciales de Google. La escritura a Drive/Sheets debe correr por:

1. **n8n** (recomendado): HTTP Request a `/sync/rows` o a `/{prov}/{sum}/recibo/{mes}`, y nodo de
   Google Sheets/Drive para escribir. Requiere que las hojas sean Google Sheets nativas para
   escritura por celda, o subir el .xlsx completo.
2. **Cuenta de servicio de Google** dentro del servicio rendo, para un endpoint que haga todo.
