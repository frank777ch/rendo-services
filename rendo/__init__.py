"""rendo-services: conectores de servicios (agua, gas, luz) para la app rendo.

Extrae datos crudos (consumo, recibos, montos por concepto y PDF) de:
- Sedapal (agua)     -> rendo.providers.sedapal
- Cálidda (gas)      -> rendo.providers.calidda
- Luz del Sur (luz)  -> rendo.providers.luzdelsur

Todo por HTTP (httpx). No usa navegador ni OCR: los montos salen del JSON de las
APIs y los campos que solo están en el PDF se leen del texto del PDF.
"""

__version__ = "1.0.0"
