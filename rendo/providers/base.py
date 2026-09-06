"""Interfaz común de un proveedor y el esquema normalizado de un recibo.

Cada recibo normalizado (dict) tiene estos campos:

    proveedor            "sedapal" | "calidda" | "luzdelsur"
    servicio             "agua" | "gas" | "luz"
    suministro           str (nº de suministro / código de cliente)
    titular              str | None
    direccion            str | None
    periodo              "YYYY-MM"
    fecha_emision        "YYYY-MM-DD" | str
    fecha_vencimiento    "YYYY-MM-DD" | str
    numero_recibo        str | None
    consumo              float          (m³ para agua/gas, kWh para luz)
    unidad               "m3" | "kWh"
    lectura_anterior     float | None
    lectura_actual       float | None
    lectura_diferencia   float | None
    precio_unitario      float | None   (S/ por kWh; None en agua/gas)
    importe_total        float
    moneda               "PEN"
    estado               str | None     ("Cobrado" | "Pendiente" | ...)
    conceptos            [ {"descripcion": str, "monto": float} ]
    tarifa               [ {...} ] | None   (estructura tarifaria; agua)
    pdf_base64           str | None     (solo si se pide con incluir_pdf=True)

Y un consumo histórico (dict): { "periodo": "YYYY-MM", "consumo": float, "importe": float }
"""
from __future__ import annotations

from typing import Any, Protocol


class Provider(Protocol):
    servicio: str  # "agua" | "gas" | "luz"

    def suministros(self) -> list[str]:
        """Lista de suministros/códigos disponibles para esta cuenta."""
        ...

    def recibos(self, suministro: str, limit: int = 12, incluir_pdf: bool = False) -> list[dict[str, Any]]:
        """Recibos normalizados (JSON + campos parseados del PDF), del más reciente al más antiguo."""
        ...

    def consumo(self, suministro: str) -> list[dict[str, Any]]:
        """Historial de consumo mensual: [{periodo, consumo, importe}]."""
        ...

    def pdf(self, suministro: str, recibo_id: str) -> bytes:
        """Bytes del PDF de un recibo (recibo_id = numero_recibo del objeto recibo)."""
        ...
