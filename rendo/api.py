"""API HTTP con bearer token. Llamable desde n8n, Google Sheets (Apps Script), o cualquier app.

Arranca con:  python -m rendo serve       (o uvicorn rendo.api:app)
Protegida con el header:  Authorization: Bearer <API_TOKEN de tu .env>
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import Response

from .config import get_settings
from .providers import build_providers

app = FastAPI(title="rendo-services", version="1.0.0",
              description="Consumo y recibos de Sedapal (agua), Cálidda (gas) y Luz del Sur (luz).")

_settings = get_settings()
_providers = build_providers(_settings)


def auth(authorization: str = Header(default="")) -> None:
    token = _settings.api.token
    if not token:
        raise HTTPException(500, "API_TOKEN no configurado en .env; la API no arranca protegida.")
    if authorization != f"Bearer {token}":
        raise HTTPException(401, "Token inválido. Usa: Authorization: Bearer <API_TOKEN>")


def _prov(nombre: str):
    p = _providers.get(nombre)
    if not p:
        raise HTTPException(404, f"proveedor '{nombre}' no habilitado. Disponibles: {list(_providers)}")
    return p


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "proveedores": list(_providers)}


@app.get("/proveedores", dependencies=[Depends(auth)])
def proveedores() -> dict[str, Any]:
    out = {}
    for nombre, p in _providers.items():
        try:
            out[nombre] = {"servicio": p.servicio, "suministros": p.suministros()}
        except Exception as e:  # noqa: BLE001
            out[nombre] = {"servicio": p.servicio, "error": str(e)}
    return out


@app.get("/{proveedor}/suministros", dependencies=[Depends(auth)])
def suministros(proveedor: str) -> list[str]:
    return _prov(proveedor).suministros()


@app.get("/{proveedor}/{suministro}/consumo", dependencies=[Depends(auth)])
def consumo(proveedor: str, suministro: str) -> list[dict[str, Any]]:
    return _prov(proveedor).consumo(suministro)


@app.get("/{proveedor}/{suministro}/recibos", dependencies=[Depends(auth)])
def recibos(proveedor: str, suministro: str,
            limit: int = Query(12, ge=1, le=48),
            pdf: bool = Query(False, description="incluir el PDF en base64")) -> list[dict[str, Any]]:
    return _prov(proveedor).recibos(suministro, limit=limit, incluir_pdf=pdf)


@app.get("/{proveedor}/{suministro}/recibo/{recibo_id}/pdf", dependencies=[Depends(auth)])
def recibo_pdf(proveedor: str, suministro: str, recibo_id: str) -> Response:
    data = _prov(proveedor).pdf(suministro, recibo_id)
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{proveedor}_{suministro}_{recibo_id}.pdf"'})


@app.get("/sync", dependencies=[Depends(auth)])
def sync(limit: int = Query(1, ge=1, le=24),
         incluir_consumo: bool = Query(True)) -> dict[str, Any]:
    """Todo de una: por cada proveedor y suministro configurado, sus últimos recibos (y consumo).
    Pensado para que n8n lo llame una vez y vuelque a Google Sheets."""
    result: dict[str, Any] = {"recibos": [], "consumo": []}
    for nombre, p in _providers.items():
        try:
            subs = p.suministros()
        except Exception as e:  # noqa: BLE001
            result.setdefault("errores", []).append({"proveedor": nombre, "error": str(e)})
            continue
        for s in subs:
            try:
                result["recibos"] += p.recibos(s, limit=limit)
                if incluir_consumo:
                    for c in p.consumo(s):
                        result["consumo"].append({"proveedor": nombre, "servicio": p.servicio,
                                                  "suministro": s, **c})
            except Exception as e:  # noqa: BLE001
                result.setdefault("errores", []).append({"proveedor": nombre, "suministro": s, "error": str(e)})
    return result


@app.get("/sync/rows", dependencies=[Depends(auth)])
def sync_rows(limit: int = Query(1, ge=1, le=24)) -> list[dict[str, Any]]:
    """Filas planas (una por recibo) listas para una hoja de cálculo."""
    rows = []
    data = sync(limit=limit, incluir_consumo=False)
    for r in data["recibos"]:
        rows.append({
            "proveedor": r["proveedor"], "servicio": r["servicio"], "suministro": r["suministro"],
            "periodo": r["periodo"], "fecha_emision": r["fecha_emision"],
            "fecha_vencimiento": r["fecha_vencimiento"], "numero_recibo": r["numero_recibo"],
            "consumo": r["consumo"], "unidad": r["unidad"],
            "lectura_anterior": r["lectura_anterior"], "lectura_actual": r["lectura_actual"],
            "lectura_diferencia": r["lectura_diferencia"], "precio_unitario": r["precio_unitario"],
            "importe_total": r["importe_total"], "estado": r["estado"],
        })
    return rows
