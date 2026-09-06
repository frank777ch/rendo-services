# Despliegue en el VPS y CI/CD

## Estado actual (activo)

- App desplegada en el VPS (IONOS, Ubuntu) en `/opt/rendo-services`, contenedor Docker `rendo`
  detrás de Caddy en `https://rendo-services.duckdns.org`.
- **CI/CD ACTIVO**: cada `git push` a `main` dispara `.github/workflows/deploy.yml`, que entra por
  SSH al VPS y corre `scripts/deploy.sh` (git pull + rebuild + health). Probado de punta a punta.
- Secrets configurados en GitHub: `VPS_HOST`, `VPS_USER`, `VPS_PORT`, `VPS_APP_DIR`, `VPS_SSH_KEY`.
- El `.env` de producción vive solo en el VPS (no en git).


## Seguridad primero (léelo)

- **NUNCA** pongas tu clave SSH privada en `.env`, en el repo, ni la pegues en un chat.
- El `.env` con tus credenciales **no se sube a git** (está en `.gitignore`). Vive solo en el servidor.
- El único lugar seguro para una clave de despliegue automático es **GitHub → Settings → Secrets**
  (cifrado), no el repositorio.

## 1. Primer despliegue (manual, una vez)

En el VPS, con Docker y Docker Compose ya instalados:

```bash
# como el usuario de tu VPS
sudo mkdir -p /opt/rendo-services && sudo chown $USER /opt/rendo-services
git clone <URL_DEL_REPO> /opt/rendo-services
cd /opt/rendo-services
cp .env.example .env
nano .env         # completa credenciales y un API_TOKEN largo y secreto
docker compose up -d --build
curl -s http://127.0.0.1:8000/health   # {"ok":true,...}
```

`rendo` queda escuchando en `127.0.0.1:8000` (solo dentro del servidor).

## 2. Exponerlo con Caddy

### Caso A — ya tienes Caddy (el que sirve n8n)  ← lo más probable
Añade a tu `Caddyfile` el bloque de `deploy/Caddyfile.snippet` (cambia el subdominio) y recarga:

```caddy
servicios.TU-DOMINIO.com {
    reverse_proxy 127.0.0.1:8000
}
```
```bash
caddy reload --config /etc/caddy/Caddyfile     # o: systemctl reload caddy
```
Apunta el DNS `servicios.TU-DOMINIO.com` a la IP del VPS. Caddy saca el HTTPS solo.

### Caso B — no tienes ningún proxy en 80/443
Usa el stack con Caddy incluido:
```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.caddy.yml up -d --build
```
(edita `deploy/Caddyfile` con tu subdominio).

## 3. Actualizaciones

### Manual
```bash
cd /opt/rendo-services && bash scripts/deploy.sh   # git pull + build + health
```

### CI/CD automático (push a main despliega solo)
1. En GitHub: **Settings → Secrets and variables → Actions → New repository secret**, crea:
   - `VPS_HOST` = IP o dominio del VPS
   - `VPS_USER` = usuario SSH
   - `VPS_PORT` = 22 (o el tuyo)
   - `VPS_APP_DIR` = `/opt/rendo-services`
   - `VPS_SSH_KEY` = **clave privada de una llave DEDICADA de despliegue** (ver abajo)
2. Genera una llave de despliegue solo para esto (no reutilices tu llave personal):
   ```bash
   ssh-keygen -t ed25519 -f deploy_key -N "" -C "rendo-deploy"
   # sube deploy_key.pub al VPS:
   ssh-copy-id -i deploy_key.pub usuario@IP_DEL_VPS
   # pega el CONTENIDO de deploy_key (privada) en el secret VPS_SSH_KEY, y luego borra deploy_key local
   ```
3. Listo: cada `git push` a `main` ejecuta `.github/workflows/deploy.yml`, que entra por SSH y
   corre `scripts/deploy.sh` en el VPS. El `.env` del servidor no se toca.

## Notas
- `docker compose logs -f rendo` para ver logs.
- El `.env` del servidor es la fuente de verdad de credenciales; cambia ahí y `docker compose up -d`.
- La imagen no incluye Playwright (la API no lo necesita), solo httpx + FastAPI + poppler.
