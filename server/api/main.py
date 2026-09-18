from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import time
from config.backend.settings import ENV, DEV_MODE
from config.backend.logger import get_api_logger

# Import API routers
from server.api.auth import router as auth_router
from server.api.portfolio import router as portfolio_router
from server.api.market_data import router as market_data_router
from server.api.orders import router as orders_router
from server.api.dividends import router as dividends_router
from server.api.profit_loss import router as profit_loss_router
from server.api.report import router as report_router
from server.api.workflows import router as workflows_router
from server.api.dashboard import router as dashboard_router
from server.api.logs import router as logs_router
from server.api.robinhood import router as robinhood_router
from server.api.files import router as files_router
from server.api.income import router as income_router

# Initialize logger
logger = get_api_logger("main")

# Create FastAPI app
app = FastAPI(
    title="Finance Dashboard",
    description="Backend API for Finance Dashboard",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(CORSMiddleware,
                   allow_origins=["https://finance.mezerotm.com"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   expose_headers=["*"],
                   )

# Request/Response logging middleware


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    start_time = time.time()

    # Log request with headers for debugging
    origin = request.headers.get("origin", "no-origin")
    user_agent = request.headers.get("user-agent", "no-ua")
    logger.info(
        f"Request: {request.method} {request.url.path} - Client: "
        f"{request.client.host if request.client else 'unknown'} - Origin: {origin} - UA: {user_agent[:50]}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    status_code = response.status_code
    if status_code >= 400:
        logger.error(
            f"Response: {request.method} "
            f"{request.url.path} - Status: {status_code} - Duration: {duration:.3f}s")
    else:
        logger.info(
            f"Response: {request.method} "
            f"{request.url.path} - Status: {status_code} - Duration: {duration:.3f}s")

    return response

# Include API routers
app.include_router(auth_router)
app.include_router(portfolio_router)
app.include_router(market_data_router)
app.include_router(orders_router)
app.include_router(dividends_router)
app.include_router(profit_loss_router)
app.include_router(report_router)
app.include_router(workflows_router)
app.include_router(dashboard_router)
app.include_router(logs_router)
app.include_router(robinhood_router)
app.include_router(files_router)
app.include_router(income_router)

# Mount static files in production
if not DEV_MODE:
    app.mount("/static", StaticFiles(directory="public"), name="static")
    app.mount("/icons", StaticFiles(directory="public/icons"), name="icons")
    app.mount("/js", StaticFiles(directory="public/js"), name="js")
    app.mount("/css", StaticFiles(directory="public/css"), name="css")
    # Alias /assets/icons -> public/icons so generated reports that reference
    # /assets/icons/... (a path baked into already-written report HTML) resolve.
    # MUST be mounted before /assets (longer prefix wins by registration
    # order).
    app.mount(
        "/assets/icons",
        StaticFiles(
            directory="public/icons"),
        name="assets-icons")
    app.mount("/assets", StaticFiles(directory="public/assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serves the Alpine.js single-page app."""
    try:
        with open("public/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("GET / - Production mode - index.html not found")
        return HTMLResponse(
            content="<h1>Frontend not built</h1>",
            status_code=404)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("GET /health - Health check")
    return {"status": "healthy", "environment": ENV}

# SPA fallback: serve index.html for any non-API, non-static route
# Must be registered AFTER the root / handler to not shadow it


@app.api_route("/{path:path}", methods=["GET"])
async def spa_fallback(path: str):
    if not path:
        raise HTTPException(status_code=404)
    if path.startswith(
        ("api/",
         "static/",
         "js/",
         "css/",
         "icons/",
         "assets/")):
        raise HTTPException(status_code=404)
    try:
        with open("public/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Frontend not built</h1>",
            status_code=404)

# Startup event


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(f"Application starting up - Environment: {ENV}")

# Shutdown event


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("Application shutting down")

if __name__ == "__main__":
    import uvicorn
    import time
    logger.info("Starting server with uvicorn")
    uvicorn.run(app, host="0.0.0.0", port=8000)
