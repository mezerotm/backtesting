import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import get_widget_logger, list_log_files, cleanup_old_logs

# Initialize logger for main server
logger = get_widget_logger('server')

app = FastAPI(title="Backtesting Dashboard", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="server"), name="static")
app.mount("/js", StaticFiles(directory="public/js"), name="js")

# Import and include routers
from server.api.portfolio import router as portfolio_router
from server.api.profit_loss import router as profit_loss_router
from server.api.robinhood import router as robinhood_router
from server.api.orders import router as orders_router
from server.api.dividends import router as dividends_router
from server.api.report import router as report_router
from server.api.dashboard import router as dashboard_router

app.include_router(portfolio_router)
app.include_router(profit_loss_router)
app.include_router(robinhood_router)
app.include_router(orders_router)
app.include_router(dividends_router)
app.include_router(report_router)
app.include_router(dashboard_router)

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root():
    logger.debug("Serving main dashboard page")
    with open("server/dashboard.html", "r") as f:
        return f.read()

@app.get("/logs")
async def list_logs():
    """List all available log files with their sizes and modification times."""
    try:
        log_files = list_log_files()
        return {
            "logs": log_files,
            "total_files": len(log_files),
            "total_size_mb": sum(log['size_mb'] for log in log_files)
        }
    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{log_name}")
async def get_log_content(log_name: str, lines: int = 100):
    """Get the content of a specific log file."""
    try:
        log_path = os.path.join("logs", log_name)
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail="Log file not found")
        
        with open(log_path, 'r') as f:
            content = f.readlines()
        
        # Return last N lines
        last_lines = content[-lines:] if len(content) > lines else content
        
        return {
            "log_name": log_name,
            "total_lines": len(content),
            "returned_lines": len(last_lines),
            "content": last_lines
        }
    except Exception as e:
        logger.error(f"Error reading log {log_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/cleanup")
async def cleanup_logs(days_to_keep: int = 7):
    """Clean up old log files."""
    try:
        cleanup_old_logs(days_to_keep)
        return {"message": f"Cleaned up logs older than {days_to_keep} days"}
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 