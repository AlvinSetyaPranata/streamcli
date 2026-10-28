# streamcli

Anime scraper for `otakudesu.blog`, with an interactive terminal client and a
dependency-free JSON HTTP API.

## Project structure

| File | Description |
| --- | --- |
| `api.py` | JSON HTTP API server (standard library only). **This is the deployable service.** |
| `main.py` | Interactive terminal CLI (requires `requests` and `beautifulsoup4`). |
| `requirements.txt` | Dependencies for the CLI. |
| `deploy.sh` | One-command VPS deployment script (systemd + nginx, port `8001`). |
| `deploy/` | systemd unit and nginx config used by `deploy.sh`. |

## API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Health check. |
| `GET /health` | Health check. |
| `GET /anime` | List all anime. |
| `GET /anime?search=naruto` | Filter the anime list by title. |
| `GET /anime/detail?url=<anime-url>` | Anime detail (info, synopsis, genres, episodes). |
| `GET /anime/stream?url=<episode-url>` | Resolve the episode stream iframe URL. |

All responses are JSON with CORS enabled.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address. `deploy.sh` sets `127.0.0.1`. |
| `PORT` | `8080` | Bind port. `deploy.sh` sets `8001`. |
| `ANIME_BASE_URL` | `https://otakudesu.blog` | Upstream site used for scraping. |
| `ALLOWED_HOSTS` | host of `ANIME_BASE_URL` | Comma-separated hosts accepted by the `url` parameters. Prevents the API from fetching arbitrary URLs (SSRF). |

## Run locally

API (no dependencies):

```bash
PORT=8001 python3 api.py
# http://localhost:8001
```

CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Deploy

The API has no runtime dependencies, so it runs directly on the VPS. It binds to
`127.0.0.1:8001`; nginx proxies public traffic to it.

1. Copy the project to the server:

   ```bash
   rsync -av --exclude .git ./ user@your-vps:/tmp/streamcli/
   ```

2. On the VPS, run the deployment script:

   ```bash
   cd /tmp/streamcli
   sudo sh deploy.sh
   ```

   The script:
   - creates the `streamcli` system user
   - installs the app to `/opt/streamcli` and writes `/opt/streamcli/.env`
     with `HOST=127.0.0.1` and `PORT=8001`
   - installs and starts `streamcli-api.service` (systemd)
   - installs the nginx site and reloads nginx (if nginx is installed)

3. Edit `/opt/streamcli/.env` if needed, then restart:

   ```bash
   sudo systemctl restart streamcli-api
   sudo systemctl status streamcli-api
   curl http://127.0.0.1:8001/health
   ```

4. Replace `server_name _;` in `/etc/nginx/sites-available/streamcli` with your
   domain, then add HTTPS:

   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

5. Open ports `80`/`443` in the VPS firewall. Do **not** expose port `8001`
   publicly; only nginx should reach it.

Useful commands:

```bash
sudo systemctl restart streamcli-api
sudo journalctl -u streamcli-api -f
```

## Notes

- Scraping depends on the upstream site's markup. If `otakudesu.blog` changes its
  HTML structure or blocks cloud provider IPs, the API may return empty results
  or upstream errors. Override `ANIME_BASE_URL` to point at a working mirror.
- Only deploy where scraping the upstream site is permitted.
