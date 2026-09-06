"""Cálidda (gas). Login por httpx (sin captcha) con bearer token. Una cuenta ve varios suministros.

JSON: estado de cuenta, consumo, lista de recibos, detalle. PDF por recibo (issueDate).
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from ..config import CaliddaCfg
from ..pdf_utils import num

BACK = "https://appadmin.calidda.com.pe/Back/api"
BACKOV = "https://appadmin.calidda.com.pe/BackOV/api"


def _cc(code: str) -> str:
    """Código de cliente con ceros a la izquierda a 12 dígitos, como lo usa la web."""
    return str(code).strip().zfill(12)


class CaliddaProvider:
    servicio = "gas"

    def __init__(self, cfg: CaliddaCfg):
        self.cfg = cfg
        self._http = httpx.Client(timeout=60, headers={
            "Content-Type": "application/json",
            "Origin": "https://appadmin.calidda.com.pe",
            "Referer": "https://appadmin.calidda.com.pe/frontov/",
            "Accept": "application/json",
        })
        self._token: str | None = None

    def _tok(self) -> str:
        if not self._token:
            r = self._http.post(f"{BACK}/Login/Access",
                                json={"username": self.cfg.user, "password": self.cfg.password})
            r.raise_for_status()
            j = r.json()
            if not j.get("data", {}).get("token"):
                raise RuntimeError(f"Login Cálidda falló: {j.get('message')}")
            self._token = j["data"]["token"]
        return self._token

    def _get(self, base: str, path: str, params: dict | None = None, accept: str | None = None) -> httpx.Response:
        h = {"Authorization": "Bearer " + self._tok()}
        if accept:
            h["Accept"] = accept
        r = self._http.get(f"{base}/{path}", params=params, headers=h)
        r.raise_for_status()
        return r

    # ---- api ----
    def suministros(self) -> list[str]:
        try:
            j = self._get(BACKOV, "Account/List").json()
            subs = [str(a.get("clientCode")).lstrip("0") for a in (j.get("data") or [])]
            if subs:
                return subs
        except Exception:
            pass
        return list(self.cfg.clientes)

    def consumo(self, suministro: str) -> list[dict[str, Any]]:
        j = self._get(BACKOV, "MeterReading/listLastConsumptions", {"clientCode": _cc(suministro)}).json()
        out = []
        for x in j.get("data") or []:
            fecha = str(x.get("date", ""))
            out.append({"periodo": fecha[:7], "consumo": x.get("billedAmount"),
                        "importe": None, "lectura": x.get("readAmount"),
                        "medidor": x.get("meterNumber")})
        return out

    def estado_cuenta(self, suministro: str) -> dict[str, Any]:
        return self._get(BACKOV, "Account/GetAccountStatement", {"clientCode": _cc(suministro)}).json().get("data", {})

    def _bills(self, suministro: str) -> list[dict]:
        return self._get(BACKOV, "Bill/ListLastBills", {"clientCode": _cc(suministro)}).json().get("data") or []

    def recibos(self, suministro: str, limit: int = 12, incluir_pdf: bool = False,
                detalle_pdf: bool = False) -> list[dict[str, Any]]:
        bills = self._bills(suministro)[:limit]
        cons = {c["periodo"]: c for c in self.consumo(suministro)}
        out = []
        for b in bills:
            issue = str(b.get("issueDate", ""))
            c = cons.get(issue[:7], {})
            r: dict[str, Any] = {
                "proveedor": "calidda", "servicio": "gas",
                "suministro": str(suministro), "titular": None, "direccion": None,
                "periodo": issue[:7],
                "fecha_emision": b.get("issueDate"), "fecha_vencimiento": b.get("expiryDate"),
                "numero_recibo": b.get("number"),
                "consumo": c.get("consumo"), "unidad": "m3",
                "lectura_anterior": None, "lectura_actual": c.get("lectura"), "lectura_diferencia": None,
                "precio_unitario": None,
                "importe_total": b.get("billedAmount"), "moneda": "PEN",
                "estado": "Pagado" if b.get("paidAmount") else "Pendiente",
                "conceptos": [], "tarifa": None, "pdf_base64": None,
                "_raw": b,
            }
            if incluir_pdf and b.get("hasDocument"):
                try:
                    r["pdf_base64"] = base64.b64encode(self._pdf(suministro, issue)).decode()
                except Exception:
                    pass
            out.append(r)
        return out

    def _pdf(self, suministro: str, issue_date: str) -> bytes:
        r = self._get(BACKOV, "Bill/download",
                      {"issueDate": issue_date, "clientCode": _cc(suministro)}, accept="application/pdf")
        return r.content

    def pdf(self, suministro: str, recibo_id: str) -> bytes:
        for b in self._bills(suministro):
            if str(b.get("number")) == str(recibo_id):
                return self._pdf(suministro, str(b.get("issueDate")))
        raise KeyError(f"recibo {recibo_id} no encontrado")
