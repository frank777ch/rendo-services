#!/usr/bin/env bash
# Despliegue/actualización en el servidor. Uso: bash scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Falta .env en el servidor. Cópialo desde .env.example y complétalo." >&2
  exit 1
fi

echo "==> git pull"
git pull --ff-only

echo "==> build + up"
docker compose up -d --build

echo "==> esperando health..."
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "OK: $(curl -s http://127.0.0.1:8000/health)"; exit 0
  fi
  sleep 2
done
echo "La API no respondió a /health a tiempo. Revisa: docker compose logs rendo" >&2
exit 1
