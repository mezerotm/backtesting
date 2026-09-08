# Finance Dashboard — Docker / Portainer deployment

The Finance Dashboard now runs as a two-container stack in Docker, on the shared
`npm` docker network so Nginx Proxy Manager (NPM) can terminate TLS and proxy a
public domain to it.

## Services

| Container            | Image                              | Runs                                                    | Reachable at        |
|----------------------|------------------------------------|---------------------------------------------------------|---------------------|
| `finance-dashboard`  | `finance-dashboard:latest`         | FastAPI + built Vue frontend (same origin) on :8000    | host `127.0.0.1:9127` |
| `finance-pocketbase` | `finance-dashboard-pocketbase:0.21.3` | PocketBase v0.21.3 (exact bundled binary), DB volume `finance-dashboard_pb_data` | network `pocketbase:8090` |

- Both containers on the external `npm` docker network (so NPM reaches them by
  service name: `http://finance-dashboard:8000`).
- **Port 8000 is NOT published on the host** — Portainer owns it. Local
  smoke-test port is `127.0.0.1:9127 -> 8000`.
- **PocketBase 8090 is NOT published** — a native dev PocketBase still runs on
  the host at `127.0.0.1:8090` and is left untouched.
- The stack's PocketBase DB lives on the named volume `finance-dashboard_pb_data`,
  seeded once from a snapshot of the existing `pb_data/`. The native instance is
  never written to.

## Files

- `docker-compose.yml` — the stack definition.
- `Dockerfile` — backend runtime image (installs Python deps from
  `requirements.txt`, but uses the modern `TA-Lib==0.7.1` binding because the
  pinned `ta-lib==0.6.3` does not compile against numpy>=2). Frontend is built
  on the host (`npm run build`) and copied in as `public/`.
- `Dockerfile.pocketbase` — minimal PocketBase image from the exact bundled binary.
- `.dockerignore` — secrets (`.env`, `cookies.txt`, tokens) and heavy dirs are
  excluded from the image. Runtime secrets come from the read-only bind mount
  `./config/shared:/app/config/shared:ro`.

## Common operations

```bash
cd /home/mezerotm/workspaces/finance

# Rebuild the frontend with an empty API base so it works from any host/domain
# (the built JS calls relative /api, so a phone/domain needs no reconfig):
cd client && ../node_modules/vite/bin/vite.js build && cd ..

# Rebuild + restart the stack after a frontend/source change:
docker compose up -d --build

# Logs
docker compose logs -f finance-dashboard
docker compose logs -f finance-pocketbase

# Verify
curl -s http://127.0.0.1:9127/health      # -> {"status":"healthy",...}
curl -s http://127.0.0.1:9127/            # -> index.html (Vue app)
```

## Public domain via Nginx Proxy Manager

Pre-requisites (need user input):
- A public domain name you control.
- DNS method — because this host is behind NAT'd IPv4 (192.168.1.184) you reach
  it via either **DDNS**(dynamic DNS record to the public IP of the NAT/ISP)
  or a **tunnel** (Cloudflare / Tailscale / frp). NPM must resolve the domain to
  this box.

Steps once the domain resolves to this box:

1. NPM can already reach the dashboard: open NPM admin (`http://<host>:1025`).
2. **Hosts > Add Proxy Host**:
   - Domain: `<your-domain>`
   - Scheme/Target: `http` / `finance-dashboard` / port `8000`
   - (leave Websockets enabled — FastAPI benefits from it)
3. **SSL tab**: Request a new Let's Encrypt certificate, enable "Force SSL",
   tick HTTP/2.
4. NPM proxies `https://<your-domain>` → `finance-dashboard:8000`.

Fallback raw nginx server block (if you bypass NPM):

```nginx
server {
    listen 443 ssl;
    server_name your.domain;
    ssl_certificate     /path/fullchain.pem;
    ssl_certificate_key /path/privkey.pem;
    location / {
        proxy_pass http://finance-dashboard:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
location /_/ {  # optional: expose PocketBase admin UI
    proxy_pass http://pocketbase:8090;
}
```

Verified: `/health` 200, frontend + hashed JS/CSS 200, and `/api/auth/login`
returns PocketBase's own 401 for bad creds (backend↔PocketBase wired). Both
containers report `healthy`.