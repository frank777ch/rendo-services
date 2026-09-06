"""Extracción de texto de PDF (sin OCR) con pdftotext -layout, y helpers de parseo."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HAS_PDFTOTEXT = shutil.which("pdftotext") is not None


def pdf_to_text(pdf_bytes: bytes) -> str:
    """Devuelve el texto del PDF conservando el layout. Requiere poppler (pdftotext)."""
    if not HAS_PDFTOTEXT:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp = Path(f.name)
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", str(tmp), "-"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout
    except Exception:
        return ""
    finally:
        tmp.unlink(missing_ok=True)


def num(s: str) -> float | None:
    """Convierte '1,713' o '1.713' o 'S/ 192.05' a float."""
    if s is None:
        return None
    s = s.strip().replace("S/", "").replace("s/", "").strip()
    if not s:
        return None
    # formato peruano: coma decimal si hay coma y no punto
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None
