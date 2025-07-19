from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.api.report import router as report_router
from server.api.portfolio import router as portfolio_router
from server.api.dividends import router as dividends_router
from server.api.profit_loss import router as profit_loss_router
from server.api.trades import router as trades_router
from server.api.robinhood import router as robinhood_router
import webbrowser
import logging
import os
from server.dashboard_generator import generate_dashboard
from market_workflow_cli import run_market_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"server/api directory contents: {os.listdir(os.path.dirname(__file__))}")
public_results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../public/results'))
logger.info(f"public/results directory: {public_results_path}")
if os.path.exists(public_results_path):
    logger.info(f"public/results contents: {os.listdir(public_results_path)}")
else:
    logger.warning(f"public/results does not exist!")

app = FastAPI()

# Log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
    return response

# Serve static files from /static
app.mount("/static", StaticFiles(directory="public", html=True), name="public")
app.mount("/results", StaticFiles(directory="public/results", html=True), name="results")
# Serve widget JS files from /js
app.mount("/js", StaticFiles(directory=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../public/js'))), name="js")

# Serve dashboard at root
@app.get("/")
def serve_dashboard():
    return FileResponse("public/index.html")

# Register routers with logs
logger.info("Registering report_router at /api/report")
app.include_router(report_router)
logger.info("Registering portfolio_router at /api/portfolio")
app.include_router(portfolio_router)
logger.info("Registering dividends_router at /api/dividends")
app.include_router(dividends_router)
logger.info("Registering profit_loss_router at /api/profit_loss")
app.include_router(profit_loss_router)
logger.info("Registering trades_router at /api/trades")
app.include_router(trades_router)
logger.info("Registering robinhood_router at /api/robinhood")
app.include_router(robinhood_router)

# Health check endpoint
@app.get("/api/dashboard/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}

# On startup, generate the dashboard
try:
    generate_dashboard()
    logging.info('Dashboard generated successfully.')
except Exception as e:
    logging.error(f'Error generating dashboard: {e}')

@app.post("/api/market/generate-report")
def generate_market_report_api(
    output_dir: str = Query('public/results', description='Directory to save the report'),
    force_refresh: bool = Query(False, description='Force refresh of data (bypass cache)')
):
    """Trigger market report generation and return the report path."""
    path = run_market_report(output_dir=output_dir, force_refresh=force_refresh)
    return {"report_path": path} 