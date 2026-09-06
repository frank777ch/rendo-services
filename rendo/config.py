"""Configuración desde .env. Nunca se hardcodean credenciales."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

load_dotenv(ROOT / ".env")


def _list(name: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, "").split(",") if x.strip()]


@dataclass
class SedapalCfg:
    suministros: list[str] = field(default_factory=lambda: _list("SUMINISTRO") or _list("SEDAPAL_SUMINISTROS"))
    # credenciales de usuario (opcionales: la lectura funciona con el token de app fijo)
    user: str = os.getenv("SEDAPAL_USER", "").strip()
    password: str = os.getenv("SEDAPAL_PASS", "").strip()
    enabled: bool = bool(_list("SUMINISTRO") or _list("SEDAPAL_SUMINISTROS"))


@dataclass
class CaliddaCfg:
    user: str = os.getenv("CALIDDA_USER", "").strip()
    password: str = os.getenv("CALIDDA_PASS", "").strip()
    clientes: list[str] = field(default_factory=lambda: _list("CALIDDA_CLIENTES"))

    @property
    def enabled(self) -> bool:
        return bool(self.user and self.password)


@dataclass
class LuzDelSurCfg:
    base_url: str = os.getenv("LUZDELSUR_BASE_URL", "https://www.luzdelsur.pe/es").strip().rstrip("/")
    user: str = os.getenv("LUZDELSUR_USER", "").strip()
    password: str = os.getenv("LUZDELSUR_PASS", "").strip()
    suministros: list[str] = field(default_factory=lambda: _list("LUZDELSUR_SUMINISTROS"))

    @property
    def enabled(self) -> bool:
        return bool(self.user and self.password)


@dataclass
class ApiCfg:
    # Token bearer para proteger tu API (cualquiera puede consultar cualquier suministro con el token de Sedapal)
    token: str = os.getenv("API_TOKEN", "").strip()
    host: str = os.getenv("API_HOST", "0.0.0.0").strip()
    port: int = int(os.getenv("API_PORT", "8000"))


@dataclass
class Settings:
    sedapal: SedapalCfg = field(default_factory=SedapalCfg)
    calidda: CaliddaCfg = field(default_factory=CaliddaCfg)
    luzdelsur: LuzDelSurCfg = field(default_factory=LuzDelSurCfg)
    api: ApiCfg = field(default_factory=ApiCfg)


def get_settings() -> Settings:
    return Settings()
