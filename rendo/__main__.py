"""CLI: python -m rendo <comando>

  fetch [--limit N] [--pdf]   Descarga todo a data/ (JSON por proveedor + CSV de recibos)
  serve                       Levanta la API (uvicorn) con bearer token
  probar                      Prueba de conexión: lista suministros de cada proveedor
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .config import DATA_DIR, get_settings
from .providers import build_providers

ROWS_FIELDS = ["proveedor", "servicio", "suministro", "periodo", "fecha_emision",
               "fecha_vencimiento", "numero_recibo", "consumo", "unidad",
               "lectura_anterior", "lectura_actual", "lectura_diferencia",
               "precio_unitario", "importe_total", "estado"]


def cmd_fetch(limit: int, pdf: bool) -> int:
    settings = get_settings()
    providers = build_providers(settings)
    if not providers:
        print("No hay proveedores habilitados. Completa el .env.", file=sys.stderr)
        return 1
    DATA_DIR.mkdir(exist_ok=True)
    todos_recibos = []
    for nombre, p in providers.items():
        data = {"proveedor": nombre, "servicio": p.servicio, "suministros": {}}
        for s in p.suministros():
            print(f"[{nombre}] suministro {s}...", file=sys.stderr)
            try:
                recibos = p.recibos(s, limit=limit, incluir_pdf=pdf)
                consumo = p.consumo(s)
                data["suministros"][s] = {"recibos": recibos, "consumo": consumo}
                todos_recibos += recibos
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR: {e}", file=sys.stderr)
                data["suministros"][s] = {"error": str(e)}
        (DATA_DIR / f"{nombre}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> data/{nombre}.json", file=sys.stderr)
    # CSV plano de todos los recibos
    csv_path = DATA_DIR / "recibos.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ROWS_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in todos_recibos:
            w.writerow(r)
    print(f"CSV: {csv_path}  ({len(todos_recibos)} recibos)", file=sys.stderr)
    return 0


def cmd_probar() -> int:
    providers = build_providers(get_settings())
    if not providers:
        print("No hay proveedores habilitados. Completa el .env.")
        return 1
    for nombre, p in providers.items():
        try:
            subs = p.suministros()
            print(f"[OK] {nombre} ({p.servicio}): {subs}")
        except Exception as e:  # noqa: BLE001
            print(f"[FALLO] {nombre}: {e}")
    return 0


def cmd_serve() -> int:
    import uvicorn
    s = get_settings()
    if not s.api.token:
        print("Configura API_TOKEN en .env antes de exponer la API.", file=sys.stderr)
        return 1
    uvicorn.run("rendo.api:app", host=s.api.host, port=s.api.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rendo", description="Conector de servicios (agua/gas/luz) para rendo")
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="descarga todo a data/ (JSON + CSV)")
    f.add_argument("--limit", type=int, default=12)
    f.add_argument("--pdf", action="store_true", help="incluir PDF en base64 en el JSON")
    sub.add_parser("serve", help="levanta la API")
    sub.add_parser("probar", help="prueba de conexión")
    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        return cmd_fetch(args.limit, args.pdf)
    if args.cmd == "serve":
        return cmd_serve()
    if args.cmd == "probar":
        return cmd_probar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
