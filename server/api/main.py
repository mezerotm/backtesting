import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import get_widget_logger, list_log_files, cleanup_old_logs, auto_cleanup_logs, get_log_stats

# Initialize logger for main server
logger = get_widget_logger('server')

app = FastAPI(title="Backtesting Dashboard", version="1.0.0")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="server")

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

# Logging middleware - only log errors to terminal, everything else goes to log files
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    # Only log errors to terminal
    if response.status_code >= 400:
        logger.error(f"HTTP {response.status_code}: {request.method} {request.url}")
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.debug("Serving main dashboard page")
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Add startup event to show server is running
@app.on_event("startup")
async def startup_event():
    print("🚀 Backtesting Dashboard server is running on http://localhost:8000/")
    print("📊 Dashboard: http://localhost:8000/")
    print("📝 Logs: ./logs/")
    print("Press Ctrl+C to stop the server")
    
    # Run automatic log cleanup on startup
    try:
        deleted_count = auto_cleanup_logs()
        if deleted_count > 0:
            print(f"🧹 Cleaned up {deleted_count} old log files on startup")
    except Exception as e:
        print(f"⚠️  Log cleanup failed: {e}")

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
        deleted_count = cleanup_old_logs(days_to_keep)
        return {"message": f"Cleaned up {deleted_count} log files older than {days_to_keep} days"}
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/logs/auto-cleanup")
async def auto_cleanup():
    """Run automatic log cleanup (age + size based)."""
    try:
        deleted_count = auto_cleanup_logs()
        return {"message": f"Auto cleanup complete. Deleted {deleted_count} files."}
    except Exception as e:
        logger.error(f"Error in auto cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/stats")
async def get_logs_stats():
    """Get log file statistics."""
    try:
        stats = get_log_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 