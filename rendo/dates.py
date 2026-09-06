"""Utilidades de periodos "YYYY-MM" para consultas por fecha y rango."""
from __future__ import annotations

import re

_PERIODO = re.compile(r"^\d{4}-\d{2}$")


def valido(periodo: str) -> bool:
    if not periodo or not _PERIODO.match(periodo):
        return False
    m = int(periodo[5:7])
    return 1 <= m <= 12


def _clave(periodo: str) -> int:
    return int(periodo[:4]) * 12 + (int(periodo[5:7]) - 1)


def en_rango(periodo: str | None, desde: str | None, hasta: str | None) -> bool:
    """True si periodo está dentro de [desde, hasta] (cualquiera puede ser None = sin límite)."""
    if not periodo or len(periodo) < 7:
        return False
    p = _clave(periodo[:7])
    if desde and valido(desde) and p < _clave(desde):
        return False
    if hasta and valido(hasta) and p > _clave(hasta):
        return False
    return True


def periodos_en_rango(desde: str, hasta: str) -> list[str]:
    """Lista de 'YYYY-MM' desde..hasta inclusive, del más reciente al más antiguo."""
    a, b = _clave(desde), _clave(hasta)
    if a > b:
        a, b = b, a
    out = []
    for k in range(a, b + 1):
        out.append(f"{k // 12:04d}-{k % 12 + 1:02d}")
    return list(reversed(out))


def anios_en_rango(desde: str, hasta: str) -> list[str]:
    y0, y1 = int(desde[:4]), int(hasta[:4])
    if y0 > y1:
        y0, y1 = y1, y0
    return [str(y) for y in range(y1, y0 - 1, -1)]
