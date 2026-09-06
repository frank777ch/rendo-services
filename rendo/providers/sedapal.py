"""Sedapal (agua). API abierta con token de aplicación fijo; sin captcha ni navegador.

JSON: consumo histórico, lista de recibos, detalle por concepto, PDF (base64).
PDF (texto): estructura tarifaria y lecturas del medidor (no vienen en el JSON).
"""
from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from ..config import SedapalCfg
from ..pdf_utils import num, pdf_to_text

API = "https://webapp16.sedapal.com.pe/OficinaComercialVirtual/api"
APP_USER, APP_PASS = "OCV_Sedapal", "OCV0109"


class SedapalProvider:
    servicio = "agua"

    def __init__(self, cfg: SedapalCfg):
        self.cfg = cfg
        self._http = httpx.Client(timeout=60, headers={
            "Origin": "https://webapp16.sedapal.com.pe",
            "Referer": "https://webapp16.sedapal.com.pe/socv/",
            "Accept": "application/json",
        })
        self._token: str | None = None

    # ---- auth ----
    def _tok(self) -> str:
        if not self._token:
            r = self._http.post(f"{API}/login",
                                data={"username": APP_USER, "password": APP_PASS},
                                headers={"Content-Type": "application/x-www-form-urlencoded"})
            r.raise_for_status()
            self._token = r.json()["bRESP"]["token"]
        return self._token

    def _post(self, path: str, body: dict) -> Any:
        r = self._http.post(f"{API}{path}", json=body, headers={"Authorization": self._tok()})
        r.raise_for_status()
        return r.json()

    # ---- api ----
    def suministros(self) -> list[str]:
        return list(self.cfg.suministros)

    def consumo(self, suministro: str) -> list[dict[str, Any]]:
        j = self._post("/suministros/historico-consumo", {"nis_rad": int(suministro)})
        out = []
        for x in j.get("bRESP") or []:
            mf = str(x.get("mes_fact", ""))
            periodo = f"{mf[:4]}-{mf[4:6]}" if len(mf) >= 6 else mf
            out.append({"periodo": periodo, "consumo": x.get("volumen"), "importe": x.get("monto")})
        return out

    def _lista_pagados(self, suministro: str, limit: int) -> list[dict]:
        j = self._post("/recibos/lista-recibos-pagados-nis",
                       {"nis_rad": int(suministro), "page_num": 1, "page_size": limit})
        return j.get("bRESP") or []

    def _lista_deudas(self, suministro: str, limit: int) -> list[dict]:
        j = self._post("/recibos/lista-recibos-deudas-nis",
                       {"nis_rad": int(suministro), "page_num": 1, "page_size": limit})
        return j.get("bRESP") or []

    def recibos(self, suministro: str, limit: int = 12, incluir_pdf: bool = False,
                detalle_pdf: bool = True) -> list[dict[str, Any]]:
        crudos = self._lista_deudas(suministro, limit) + self._lista_pagados(suministro, limit)
        crudos = crudos[:limit]
        consumo_por_periodo = {c["periodo"]: c for c in self.consumo(suministro)}
        out = []
        for rec in crudos:
            ff = str(rec.get("f_fact", ""))
            periodo = ff[:7] if len(ff) >= 7 else ff
            conceptos = []
            try:
                det = self._post("/recibos/detalle-recibo", rec).get("bRESP") or []
                conceptos = [{"descripcion": c.get("desc_concepto"), "monto": c.get("monto_concepto")} for c in det]
            except Exception:
                pass
            r: dict[str, Any] = {
                "proveedor": "sedapal", "servicio": "agua",
                "suministro": str(suministro), "titular": rec.get("nom_cliente"),
                "direccion": None, "periodo": periodo,
                "fecha_emision": rec.get("f_fact"), "fecha_vencimiento": rec.get("vencimiento"),
                "numero_recibo": str(rec.get("recibo")) if rec.get("recibo") is not None else None,
                "consumo": (consumo_por_periodo.get(periodo) or {}).get("consumo"),
                "unidad": "m3",
                "lectura_anterior": None, "lectura_actual": None, "lectura_diferencia": None,
                "precio_unitario": None,
                "importe_total": rec.get("total_fact"), "moneda": "PEN",
                "estado": rec.get("estado"),
                "conceptos": conceptos, "tarifa": None, "pdf_base64": None,
                "_raw": rec,
            }
            if detalle_pdf or incluir_pdf:
                try:
                    pdf = self._pdf_bytes(rec)
                    if incluir_pdf:
                        r["pdf_base64"] = base64.b64encode(pdf).decode()
                    self._merge_pdf(r, pdf_to_text(pdf))
                except Exception:
                    pass
            out.append(r)
        return out

    def _pdf_bytes(self, rec: dict) -> bytes:
        j = self._post("/recibos/recibo-pdf", rec)
        return base64.b64decode(j["bRESP"])

    def pdf(self, suministro: str, recibo_id: str) -> bytes:
        for rec in self._lista_pagados(suministro, 24) + self._lista_deudas(suministro, 24):
            if str(rec.get("recibo")) == str(recibo_id):
                return self._pdf_bytes(rec)
        raise KeyError(f"recibo {recibo_id} no encontrado para suministro {suministro}")

    # ---- parseo del texto del PDF: tarifa + lecturas ----
    @staticmethod
    def _merge_pdf(r: dict, text: str) -> None:
        if not text:
            return
        # lecturas: linea con el medidor (E + digitos) seguido de anterior/actual/consumo
        m = re.search(r"E\d+\s+(\d+)\s+(\d+)\s+(\d+)", text)
        if m:
            r["lectura_anterior"] = float(m.group(1))
            r["lectura_actual"] = float(m.group(2))
            r["lectura_diferencia"] = float(m.group(3))
        # estructura tarifaria: rangos con precio agua y alcantarillado
        tarifa = []
        for mm in re.finditer(r"(\d+\s*a\s*\d+|\d+\s*a\s*m[aá]s)\s+([\d.,]+)\s+([\d.,]+)", text):
            tarifa.append({
                "rango": re.sub(r"\s+", " ", mm.group(1)).strip(),
                "agua": num(mm.group(2)),
                "alcantarillado": num(mm.group(3)),
            })
        if tarifa:
            r["tarifa"] = tarifa
