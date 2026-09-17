# AGENTS.md — Finance Dashboard

## Overview

Personal investment dashboard: portfolio tracking, Robinhood sync, market data,
dividend reporting, profit/loss analysis, and backtesting.  Serves an Alpine.js
single-page frontend from the same FastAPI server (no separate build step).

Live at: https://finance.mezerotm.com  (Docker container on Portainer host)
Development on host at: http://127.0.0.1:8000

## Stack

- **Backend**: Python 3.12, FastAPI (uvicorn), served via Docker
- **Frontend**: Alpine.js CDN — single `public/index.html`, no build step
- **Database**: PocketBase v0.21.3 (Go binary, port 8090) on Docker network
- **Deployment**: Docker containers on Portainer host (npm network), Nginx Proxy Manager
- **Data sources**: Polygon.io, Yahoo Finance (yfinance), FRED, CoinGecko, Robinhood API

## Key Files & Directories

### Backend (`server/`)

| Path | Purpose |
|------|---------|
| `server/api/main.py` | FastAPI app factory — mounts all routers, static files, CORS |
| `server/api/dashboard.py` | Health check endpoint |
| `server/api/portfolio.py` | Portfolio holdings, positions, performance |
| `server/api/orders.py` | Order history |
| `server/api/dividends.py` | Dividend records |
| `server/api/profit_loss.py` | P&L calculations (by symbol, date range) |
| `server/api/market_data.py` | Price data, market overview |
| `server/api/report.py` | PDF/CSV report generation |
| `server/api/workflows.py` | Backtest/market workflow endpoints |
| `server/api/robinhood.py` | Robinhood login, sync, 2FA |
| `server/api/auth.py` | Auth endpoints (PocketBase session) |
| `server/api/files.py` | File upload/download |
| `server/api/logs.py` | Log viewer endpoints |
| `server/services/` | Business logic layer (auth, portfolio, report, robinhood, workflow) |
| `server/models/` | Pydantic data models + ModelManager for DB ops |
| `server/utils/` | Database client, utility modules |

### Frontend (`public/`)

| Path | Purpose |
|------|---------|
| `public/index.html` | Single-page Alpine.js dashboard. All UI is inline HTML+Alpine |
| `public/css/` | Stylesheets |
| `public/js/` | JavaScript helpers |
| `public/assets/` | Static assets, icons |
| `public/results/` | Generated reports (PDFs, CSVs) mounted from host |

### Config & Deployment

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | Finance dashboard + PocketBase service stack |
| `Dockerfile` | Python runtime image (Python 3.12-slim + TA-Lib) |
| `Dockerfile.pocketbase` | PocketBase Go binary image |
| `Makefile` | All dev/run/test/build commands |
| `config/` | Settings (backend, frontend, shared .env, logging) |
| `requirements.in` / `requirements.txt` | Python dependencies (pip-compile managed) |

### Workflows & Scripts

| Path | Purpose |
|------|---------|
| `workflows/backtest/` | Backtesting workflows (SMA, EMA, experimental strategies) |
| `workflows/market/` | Market data collection workflows |
| `workflows/comparison/` | Strategy comparison workflows |
| `workflows/financial/` | Financial report workflows |
| `backtest_workflow_cli.py` | CLI entry for one-off backtests |
| `market_workflow_cli.py` | CLI entry for market data runs |
| `comparison_workflow_cli.py` | CLI entry for strategy comparison |
| `financial_workflow_cli.py` | CLI entry for financial reports |
| `scripts/` | Utilities: DB backup, repo backup, security config, key rotation |

### Other

| Path | Purpose |
|------|---------|
| `strategies/` | Trading strategy implementations (SMA, EMA, buy-hold, etc.) |
| `pb_data/` | PocketBase data files (Docker volume mount) |
| `pb_migrations/` | PocketBase schema migrations |
| `data/` | Cached market data |

## Running

### Production (Docker)

```bash
make deploy                 # Build & start: docker compose up -d --build
make server-start           # Start containers
make server-stop            # Stop containers
make server-restart         # Restart containers
make server-logs            # Tail container logs
```

Container runs on `npm` Docker network, bound to `192.168.1.184:9129`.
Nginx Proxy Manager routes `finance.mezerotm.com` -> `finance-dashboard:8000`.

### Development

```bash
make dev-server             # Uvicorn with hot-reload on host :8000
```

Dev server reads from `config/backend/settings.py` (DEV_MODE config).
Frontend is the same Alpine.js `index.html` - no separate frontend dev server.

### Dependencies

```bash
make setup                  # Create venv + pip install
make deps                   # pip-compile requirements.in -> requirements.txt + install
```

## Structure & Conventions

### Architecture

- **API layer** (`server/api/`) - FastAPI routers, one file per domain. Thin.
  Business logic lives in `server/services/`.
- **Service layer** (`server/services/`) - RobinhoodService, PortfolioService,
  AuthService, ReportWorkflowService, etc. Each initialized with a
  PocketBase client from ModelManager.
- **Model layer** (`server/models/`) - Pydantic schemas (requests, responses)
  + ModelManager (DB wrapper over PocketBase REST API).
- **All API calls synchronous** (no async routes). FastAPI threaded by uvicorn workers.
- **Frontend communicates** via `fetch()` to `/api/...`. No WebSocket.
- **Secrets** live in `config/shared/.env` (API keys, PB credentials). Not in Docker image.

### Coding Style

- Python: type hints everywhere, Google-style docstrings, 4-space indent.
- Imports: stdlib -> third-party -> project modules, blank-separated.
- f-strings: all {expressions} on the same logical line (no break inside braces).
- API routes: `/api/{domain}/{action}` - e.g. `/api/portfolio/holdings`.
- Frontend: Alpine.js `x-data`, `x-text`, `x-effect`, `x-init`. No Vue/Vite.
- CSS: custom properties on `:root`, dark theme, responsive.

### Git

- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `refactor:`).
- Branch: `main` for production. Feature branches via git worktrees (Kanban tasks).

## Testing

- No formal test suite. Manual testing via browser at `http://127.0.0.1:8000`.
- Health check: `curl http://127.0.0.1:8000/api/dashboard/health`.
- Docker health checks defined in `docker-compose.yml`.
- Browser self-test: run `scripts/browser_check.py` against the live dashboard URL.

## Where To Find Things

| What you need | Look in |
|---------------|---------|
| Add an API endpoint | `server/api/` - pick the router file for the domain, or add a new one and mount it in `main.py` |
| Modify business logic | `server/services/` - same domain pattern |
| Change DB schema | Pydantic models in `server/models/data_models.py`; PocketBase migrations in `pb_migrations/` |
| Add a frontend tab/panel | `public/index.html` - Alpine.js x-data section near other tabs |
| Change deployment config | `docker-compose.yml`, `Dockerfile`, NPM config in Portainer |
| Run a backtest | `backtest_workflow_cli.py --symbol NVDA --strategies sma` |
| Check logs | `make server-logs` or `/api/logs/` endpoint |
