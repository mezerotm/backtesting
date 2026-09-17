from fastapi import APIRouter, HTTPException, Query
from config.backend.logger import get_server_logger
from config.backend.settings import POLYGON_API_KEY
from typing import List, Dict, Optional
from datetime import datetime
import os
import json
import requests
import shutil
from server.services.report_workflow_service import generate_market_report as _service_market, generate_financial_report as _service_financial

logger = get_server_logger("report")

router = APIRouter(prefix="/api/report", tags=["report"])

# This module provides endpoints for report management (listing, cleaning, deleting).
# Report metadata schema: see get_report_metadata in dashboard_server.py
# Endpoints:
#   GET /api/report/list - List all reports
#   POST /api/report/clean - Clean all results
#   POST /api/report/delete/{dir} - Delete a specific report
#   GET /api/report/search-symbols - Search for symbols (Polygon API)
#   POST /api/report/generate-market - Trigger market report generation
#   POST /api/report/generate-finance - Trigger financial report generation
#   GET /api/report/data/{symbol}/{filename} - Serve JSON data files

REPORTS_DIR = os.path.join("public", "results")

# Strategies the dashboard understands (class names from strategies/__init__.py).
# Maps lowercase lookup key -> canonical class name for clear error messages.
VALID_STRATEGIES = {
    "buyandholdstrategy": "BuyAndHoldStrategy",
    "simplemovingaveragecrossover": "SimpleMovingAverageCrossover",
    "exponentialmovingaveragecrossover": "ExponentialMovingAverageCrossover",
    "macdrsistrategy": "MACDRSIStrategy",
    "bollingerrsistrategy": "BollingerRSIStrategy",
    "combinedstrategy": "CombinedStrategy",
}


def _clean_error_message(err: Exception) -> str:
    """Return a short, human-readable message from a generator exception."""
    msg = str(err).strip() or err.__class__.__name__
    # Keep just the first useful line; deep tracebacks are not user-friendly.
    first_line = msg.splitlines()[0] if msg else err.__class__.__name__
    return first_line[:400]


def _parse_date(value: str, field: str) -> datetime:
    """Parse a YYYY-MM-DD date string or raise a 422 HTTPException."""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field} '{value}'. Expected format YYYY-MM-DD.")


def _validate_date_range(start: Optional[str], end: Optional[str]) -> None:
    """Validate an optional date range, raising 400 on a broken range."""
    if start is None and end is None:
        return
    start_dt = _parse_date(start, "start_date") if start else None
    end_dt = _parse_date(end, "end_date") if end else None
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date range: start_date {start} is after end_date {end}.")


def _validate_symbol(symbol: Optional[str]) -> str:
    """Validate a stock symbol, returning the normalized (uppercased) value."""
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        raise HTTPException(
            status_code=400,
            detail="Symbol is required for finance reports.")
    symbol = symbol.strip().upper()
    if not symbol.replace("-", "").replace(".", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid symbol '{symbol}'. Symbols may contain only letters, numbers, '.' and '-'.")
    return symbol


def _validate_strategy(strategy: Optional[str]) -> None:
    """Reject unknown strategy values with a clear 400 message."""
    if strategy is None or not strategy.strip():
        return
    if strategy.strip().lower() not in VALID_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{strategy}'. Supported strategies: "
                   f"{', '.join(sorted(VALID_STRATEGIES.values()))}.")


def get_report_metadata(report_dir: str) -> Dict:
    try:
        metadata_path = os.path.join(report_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                metadata['dir'] = os.path.basename(report_dir)
                if 'created' in metadata:
                    metadata['created'] = metadata['created']
                if 'path' not in metadata:
                    metadata['path'] = f"static/results/{metadata['dir']}/index.html"
                return metadata
        return {
            'dir': os.path.basename(report_dir),
            'path': f"static/results/{os.path.basename(report_dir)}/index.html"}
    except Exception as e:
        logger.error(f"Error reading report metadata from {report_dir}: {e}")
        return {
            'dir': os.path.basename(report_dir),
            'path': f"static/results/{os.path.basename(report_dir)}/index.html",
            'error': str(e)}


@router.get("/list")
def list_reports() -> List[Dict]:
    try:
        if not os.path.exists(REPORTS_DIR):
            return []
        report_dirs = [
            os.path.join(
                REPORTS_DIR,
                d) for d in os.listdir(REPORTS_DIR) if os.path.isdir(
                os.path.join(
                    REPORTS_DIR,
                    d))]
        reports = [get_report_metadata(d) for d in report_dirs]
        reports.sort(key=lambda x: x.get('created', ''), reverse=True)
        return reports
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return []


@router.post("/clean")
def clean_results():
    try:
        if os.path.exists(REPORTS_DIR):
            for item in os.listdir(REPORTS_DIR):
                item_path = os.path.join(REPORTS_DIR, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error deleting {item_path}: {e}")
        return {"message": "Results cleaned successfully"}
    except Exception as e:
        logger.error(f"Error cleaning results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning results: {e}")


@router.post("/delete/{dir}")
def delete_report(dir: str):
    try:
        report_path = os.path.join(REPORTS_DIR, dir)
        if os.path.exists(report_path) and os.path.commonprefix(
                [os.path.abspath(report_path), REPORTS_DIR]) == REPORTS_DIR:
            shutil.rmtree(report_path)
            return {"message": "Report deleted successfully"}
        raise HTTPException(status_code=404, detail="Report not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {dir}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting report: {e}")


@router.get("/data/{symbol}/{filename}")
def get_report_data(symbol: str, filename: str):
    """Serve JSON data files for financial reports."""
    # Find the most recent report directory for this symbol
    if not os.path.exists(REPORTS_DIR):
        raise HTTPException(
            status_code=404,
            detail="Reports directory not found")

    # Look for financial report directories for this symbol
    symbol_dirs = []
    for item in os.listdir(REPORTS_DIR):
        if item.startswith(
                f"financial_{symbol}_") and os.path.isdir(
                os.path.join(
                REPORTS_DIR,
                item)):
            symbol_dirs.append(item)

    if not symbol_dirs:
        raise HTTPException(
            status_code=404,
            detail=f"No financial reports found for {symbol}")

    # Get the most recent directory (sort by date)
    symbol_dirs.sort(reverse=True)
    latest_dir = symbol_dirs[0]
    file_path = os.path.join(REPORTS_DIR, latest_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404,
                            detail=f"File {filename} not found for {symbol}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}")


@router.get("/search-symbols")
def search_symbols(query: str = Query(..., min_length=1,
                   description="Symbol search query")):
    """Search for symbols using Polygon.io's ticker search API."""
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "search": query,
        "active": "true",
        "apiKey": POLYGON_API_KEY,
        "limit": 10
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach Polygon API: {_clean_error_message(e)}")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Polygon API error: {resp.text}")
    data = resp.json()
    # Return a list of {symbol, name}
    results = [{"symbol": t["ticker"], "name": t.get(
        "name", "")} for t in data.get("results", [])]
    return results


@router.post("/generate-market")
async def generate_market_report_api(
    output_dir: str = 'public/results',
        force_refresh: bool = False):
    """Trigger market report generation and return the report path."""
    logger.info(
        f"[API] /api/report/generate-market called with output_dir={output_dir}, force_refresh={force_refresh}")
    try:
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, lambda: _service_market(
            output_dir=output_dir,
            force_refresh=force_refresh))
        logger.info(f"[API] Market report generated at: {path}")
        return {"report_path": path}
    except Exception as e:
        logger.error(
            f"[API] Error generating market report: {e}",
            exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Market report generation failed: {_clean_error_message(e)}")


@router.post("/generate-finance")
def generate_finance_report_api(
    symbol: Optional[str] = None,
    output_dir: str = 'public/results',
    force_refresh: bool = False,
    strategy: Optional[str] = Query(
        None,
        description="Optional backtest strategy to validate"),
        start_date: Optional[str] = Query(
            None,
            description="Optional start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(
        None,
        description="Optional end date (YYYY-MM-DD)")):
    """Trigger finance report generation and return the report path.

    Validates symbol, strategy and date range before delegating to the
    financial workflow generator. Failures are surfaced as a clear 4xx/5xx
    JSON error body ({detail: ...}) instead of a generic server error.
    """
    symbol = _validate_symbol(symbol)
    _validate_strategy(strategy)
    _validate_date_range(start_date, end_date)

    logger.info(
        f"[API] /api/report/generate-finance called with symbol={symbol}, output_dir={output_dir}, force_refresh={force_refresh}, strategy={strategy}, start_date={start_date}, end_date={end_date}")

    try:
        path = _service_financial(
            symbol=symbol,
            output_dir=output_dir,
            force_refresh=force_refresh)
        logger.info(f"[API] Finance report generated at: {path}")
        return {"report_path": path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[API] Error generating finance report for {symbol}: {e}",
            exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Finance report generation failed for {symbol}: {_clean_error_message(e)}")
