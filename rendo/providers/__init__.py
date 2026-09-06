"""Conectores por proveedor. Todos exponen la misma interfaz (ver base.Provider)."""
from __future__ import annotations

from ..config import Settings
from .base import Provider
from .calidda import CaliddaProvider
from .luzdelsur import LuzDelSurProvider
from .sedapal import SedapalProvider


def build_providers(settings: Settings) -> dict[str, Provider]:
    """Instancia solo los proveedores habilitados en .env."""
    out: dict[str, Provider] = {}
    if settings.sedapal.enabled:
        out["sedapal"] = SedapalProvider(settings.sedapal)
    if settings.calidda.enabled:
        out["calidda"] = CaliddaProvider(settings.calidda)
    if settings.luzdelsur.enabled:
        out["luzdelsur"] = LuzDelSurProvider(settings.luzdelsur)
    return out


__all__ = ["Provider", "SedapalProvider", "CaliddaProvider", "LuzDelSurProvider", "build_providers"]
