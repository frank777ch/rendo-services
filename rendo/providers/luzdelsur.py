"""Luz del Sur (luz). Login por httpx (sin captcha) y área privada por token en el body.

JSON: lista de suministros, consumo mensual (kWh + monto), historial de recibos.
PDF (texto): desglose de conceptos (precio kWh, cargo fijo, alumbrado, IGV...) y lecturas,
que no vienen en el JSON.
"""
from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from ..config import LuzDelSurCfg
from ..dates import en_rango
from ..pdf_utils import num, pdf_to_text

_MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

_CONCEPTOS = [
    ("Consumo de energía", "consumo_energia"),
    ("Cargo Fijo", "cargo_fijo"),
    ("Mant. y Reposición de Conexión", "mantenimiento_reposicion"),
    ("Alumbrado Público", "alumbrado_publico"),
    ("Interés Compensatorio", "interes_compensatorio"),
    ("SUBTOTAL", "subtotal"),
    ("IGV", "igv"),
    ("Interés Moratorio", "interes_moratorio"),
    ("TOTAL DEL MES", "total_del_mes"),
]


class LuzDelSurProvider:
    servicio = "luz"

    def __init__(self, cfg: LuzDelSurCfg):
        self.cfg = cfg
        self.base = cfg.base_url
        self._http = httpx.Client(timeout=60, headers={
            "Content-Type": "application/json; charset=utf-8",
            "Origin": "https://www.luzdelsur.pe",
            "Referer": self.base + "/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*",
            "User-Agent": "Mozilla/5.0",
        })
        self._token: str | None = None

    def _tok(self) -> str:
        if not self._token:
            r = self._http.post(self.base + "/Login/ValidarAcceso",
                                json={"request": {"Correo": self.cfg.user,
                                                  "password": self.cfg.password,
                                                  "Plataforma": "WEB"}})
            r.raise_for_status()
            j = r.json()
            if not j.get("datos", {}).get("token"):
                raise RuntimeError(f"Login Luz del Sur falló: {j.get('datos', {}).get('mensajeUsuario')}")
            self._token = j["datos"]["token"]
        return self._token

    def _post(self, path: str, req: dict) -> Any:
        req = {**req, "Token": self._tok(), "Correo": self.cfg.user}
        r = self._http.post(self.base + path, json={"request": req})
        r.raise_for_status()
        return r.json()

    # ---- api ----
    def suministros(self) -> list[str]:
        j = self._post("/InformacionGuardada/ListarSuministros", {})
        subs = [str(s.get("suministro")) for s in (j.get("datos", {}).get("suministros") or [])]
        return subs or list(self.cfg.suministros)

    def consumo(self, suministro: str) -> list[dict[str, Any]]:
        j = self._post("/InformacionGuardada/ObtenerConsumo", {"Suministro": str(suministro)})
        out = []
        for x in j.get("datos", {}).get("listadoConsumo") or []:
            out.append({"periodo": self._periodo(x.get("fecha")),
                        "consumo": num(str(x.get("consumo"))),
                        "importe": num(str(x.get("mesActual")))})
        return out

    @staticmethod
    def _periodo(fecha: str | None) -> str | None:
        # "Jul. 26" -> "2026-07"
        if not fecha:
            return None
        m = re.match(r"([A-Za-z]{3})\.?\s*(\d{2})", fecha.strip())
        if not m:
            return fecha
        mes = _MESES.get(m.group(1).lower())
        return f"20{m.group(2)}-{mes:02d}" if mes else fecha

    def _historial(self, suministro: str, anios: list[str]) -> list[dict]:
        rows = []
        for anio in anios:
            j = self._post("/InformacionGuardada/ObtenerHistorialFacturacion",
                           {"Suministro": str(suministro), "Anio": str(anio)})
            rows += j.get("datos", {}).get("listadoHistoriaFacturacion") or []
        return rows

    def _build(self, suministro: str, h: dict, cons: dict, incluir_pdf: bool, detalle_pdf: bool) -> dict[str, Any]:
        periodo = self._fecha_periodo(h.get("fechaEmision"))
        c = cons.get(periodo, {})
        r: dict[str, Any] = {
            "proveedor": "luzdelsur", "servicio": "luz",
            "suministro": str(suministro), "titular": None, "direccion": None,
            "periodo": periodo,
            "fecha_emision": h.get("fechaEmision"), "fecha_vencimiento": h.get("fechaVencimiento"),
            "numero_recibo": str(h.get("corrFacturacion")),
            "consumo": c.get("consumo"), "unidad": "kWh",
            "lectura_anterior": None, "lectura_actual": None, "lectura_diferencia": None,
            "precio_unitario": None,
            "importe_total": c.get("importe") if c.get("importe") is not None else h.get("total"),
            "moneda": "PEN",
            "estado": None, "conceptos": [], "tarifa": None, "pdf_base64": None,
            "_raw": h,
        }
        if detalle_pdf or incluir_pdf:
            try:
                pdf = self._boleta(suministro, str(h.get("corrFacturacion")))
                if incluir_pdf:
                    r["pdf_base64"] = base64.b64encode(pdf).decode()
                self._merge_pdf(r, pdf_to_text(pdf))
            except Exception:
                pass
        return r

    def recibos(self, suministro: str, limit: int = 12, incluir_pdf: bool = False,
                desde: str | None = None, hasta: str | None = None,
                detalle_pdf: bool = True) -> list[dict[str, Any]]:
        import datetime
        cons = {c["periodo"]: c for c in self.consumo(suministro)}
        if desde or hasta:
            y1 = int((hasta or desde)[:4]); y0 = int((desde or hasta)[:4])
            anios = [str(y) for y in range(max(y0, y1), min(y0, y1) - 1, -1)]
            hist = [h for h in self._historial(suministro, anios)
                    if en_rango(self._fecha_periodo(h.get("fechaEmision")), desde, hasta)]
        else:
            y = datetime.date.today().year
            hist = self._historial(suministro, [str(y), str(y - 1)])[:limit]
        return [self._build(suministro, h, cons, incluir_pdf, detalle_pdf) for h in hist]

    def recibo(self, suministro: str, periodo: str, incluir_pdf: bool = False) -> dict[str, Any] | None:
        cons = {c["periodo"]: c for c in self.consumo(suministro)}
        for h in self._historial(suministro, [periodo[:4]]):
            if self._fecha_periodo(h.get("fechaEmision")) == periodo:
                return self._build(suministro, h, cons, incluir_pdf, True)
        return None

    def pdf_periodo(self, suministro: str, periodo: str) -> bytes:
        for h in self._historial(suministro, [periodo[:4]]):
            if self._fecha_periodo(h.get("fechaEmision")) == periodo:
                return self._boleta(suministro, str(h.get("corrFacturacion")))
        raise KeyError(f"no hay recibo de luz del periodo {periodo} para {suministro}")

    @staticmethod
    def _fecha_periodo(fecha: str | None) -> str | None:
        # "25/07/2026" -> "2026-07"
        if not fecha:
            return None
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", fecha)
        return f"{m.group(3)}-{m.group(2)}" if m else fecha

    def _boleta(self, suministro: str, corr: str) -> bytes:
        j = self._post("/InformacionGuardada/ObtenerBoletaPorMes",
                       {"Suministro": str(suministro), "CorrFacturacion": str(corr)})
        b64 = j.get("datos", {}).get("archivoBase64")
        if not b64:
            raise RuntimeError("sin PDF para ese correlativo")
        return base64.b64decode(b64)

    def pdf(self, suministro: str, recibo_id: str) -> bytes:
        return self._boleta(suministro, recibo_id)

    @staticmethod
    def _merge_pdf(r: dict, text: str) -> None:
        if not text:
            return
        # lecturas y precio kWh: "12719.20 - 12405.60 = 313.60 X 1.0000 = 313.60 X 0.6124"
        m = re.search(r"([\d.]+)\s*-\s*([\d.]+)\s*=\s*([\d.]+)\s*X\s*[\d.]+\s*=\s*[\d.]+\s*X\s*([\d.]+)", text)
        if m:
            r["lectura_actual"] = num(m.group(1))
            r["lectura_anterior"] = num(m.group(2))
            r["lectura_diferencia"] = num(m.group(3))
            r["precio_unitario"] = num(m.group(4))
        conceptos = []
        for label, _key in _CONCEPTOS:
            mm = re.search(re.escape(label) + r"\s+([\d.,]+)", text)
            if mm:
                conceptos.append({"descripcion": label, "monto": num(mm.group(1))})
        if conceptos:
            r["conceptos"] = conceptos
            total = next((c["monto"] for c in conceptos if c["descripcion"] == "TOTAL DEL MES"), None)
            if total is not None:
                r["importe_total"] = total
