from fastapi import APIRouter, HTTPException
from config.backend.logger import get_server_logger
from config.backend.settings import POLYGON_API_KEY
from typing import List, Dict
import os
import json
import requests
import shutil
from market_workflow_cli import run_market_report
from financial_workflow_cli import create_financial_report

logger = get_server_logger("report")

# This module provides endpoints for report management (listing, cleaning, deleting).
# Report metadata schema: see get_report_metadata in dashboard_server.py
# Endpoints:
#   GET /api/report/list - List all reports
#   POST /api/report/clean - Clean all results
#   POST /api/report/delete/{dir} - Delete a specific report
#   GET /api/report/search-symbols - Search for symbols (Polygon API)

REPORTS_DIR = os.path.join("public", "results")

router = APIRouter(prefix="/api/report", tags=["report"])


def get_report_metadata(report_dir: str) -> Dict:
    metadata_path = os.path.join(report_dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            metadata['dir'] = os.path.basename(report_dir)
            if 'created' in metadata:
                metadata['created'] = metadata['created']
            if 'path' not in metadata:
                metadata['path'] = f"static/results/{
                    metadata['dir']}/index.html"
            return metadata
    return {'dir': os.path.basename(
        report_dir), 'path': f"static/results/{os.path.basename(report_dir)}/index.html"}


@router.get("/list")
def list_reports() -> List[Dict]:
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


@router.post("/clean")
def clean_results():
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


@router.post("/delete/{dir}")
def delete_report(dir: str):
    report_path = os.path.join(REPORTS_DIR, dir)
    if os.path.exists(report_path) and os.path.commonprefix(
            [os.path.abspath(report_path), REPORTS_DIR]) == REPORTS_DIR:
        shutil.rmtree(report_path)
        return {"message": "Report deleted successfully"}
    raise HTTPException(status_code=404, detail="Report not found")


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
        raise HTTPException(status_code=404, detail=f"File {
                            filename} not found for {symbol}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {
                str(e)}")


@router.get("/search-symbols")
def search_symbols(query: str):
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
    resp = requests.get(url, params=params)
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
def generate_market_report_api(
    output_dir: str = 'public/results',
        force_refresh: bool = False):
    """Trigger market report generation and return the report path."""
    logger.info(f"[API] /api/report/generate-market called with output_dir={
                output_dir}, force_refresh={force_refresh}")
    try:
        path = run_market_report(
            output_dir=output_dir,
            force_refresh=force_refresh)
        logger.info(f"[API] Market report generated at: {path}")
        return {"report_path": path}
    except Exception as e:
        logger.error(
            f"[API] Error generating market report: {e}",
            exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Error generating market report: {e}")


@router.post("/generate-finance")
def generate_finance_report_api(
        symbol: str = None,
        output_dir: str = 'public/results',
        force_refresh: bool = False):
    """Trigger finance report generation and return the report path."""
    logger.info(f"[API] /api/report/generate-finance called with symbol={
                symbol}, output_dir={output_dir}, force_refresh={force_refresh}")

    if not symbol:
        raise HTTPException(status_code=400,
                            detail="Symbol is required for finance reports")

    try:
        # Create a simple args object for the financial workflow
        class Args:
            def __init__(self, output_dir, force_refresh):
                self.output_dir = output_dir
                self.force_refresh = force_refresh

        args = Args(output_dir, force_refresh)
        path = create_financial_report(symbol, args)
        logger.info(f"[API] Finance report generated at: {path}")
        return {"report_path": path}
    except Exception as e:
        logger.error(
            f"[API] Error generating finance report: {e}",
            exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Error generating finance report: {e}")
