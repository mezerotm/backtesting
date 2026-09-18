"""
Report workflow service — report generation logic extracted from CLI scripts.

Both CLI scripts and API endpoints call this service instead of each other,
breaking the tangled API→CLI dependency. The CLI scripts remain as thin
wrappers (backward compatible), and the API endpoints call this service directly.

Functions:
    generate_market_report(output_dir, force_refresh) -> str
    generate_financial_report(symbol, output_dir, force_refresh) -> str
"""

import os
import logging
from datetime import datetime
from typing import Optional

from workflows.market.market_data import MarketDataFetcher
from workflows.market.market_report_generator import (
    generate_market_report as _generate_market_html,
    generate_gdp_chart,
    generate_inflation_chart,
    generate_unemployment_chart,
    generate_bond_chart,
)
from workflows.metadata_generator import generate_metadata, save_metadata
from workflows.market.market_chart_generator import (
    generate_market_index_chart,
    generate_single_bond_chart,
    generate_style_box_heatmap,
)
from workflows.financial.financial_data import FinancialDataFetcher
from workflows.financial.financial_report_generator import (
    generate_financial_report as _generate_financial_html,
)

logger = logging.getLogger(__name__)

# Project root — the parent of server/ and public/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /app/server
APP_ROOT = os.path.dirname(PROJECT_ROOT)  # /app


# ── Market report ──────────────────────────────────────────────────────────

def generate_market_report(
    output_dir: str = "public/results",
    force_refresh: bool = False,
) -> str:
    """Generate the full market analysis report.

    Args:
        output_dir:  Directory under the project root where the
                     timestamped report folder is created.
        force_refresh: If True, bypass data cache.

    Returns:
        Absolute path to the generated ``index.html``.
    """
    output_base_dir = os.path.join(APP_ROOT, output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir_name = f"market_{timestamp}"
    report_dir = os.path.join(output_base_dir, report_dir_name)

    os.makedirs(report_dir, exist_ok=True)

    data_fetcher = MarketDataFetcher(force_refresh=force_refresh)

    data: dict = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": datetime.now().strftime("%B %d, %Y"),
        "current_year": datetime.now().year,
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gdp_chart_path": None,
        "inflation_chart_path": None,
        "unemployment_chart_path": None,
        "bond_chart_path": None,
    }

    # ── Naming Convention ──
    # For all 10Y and 2Y Treasury references, use ONLY these keys:
    TEN_YEAR_KEY = "10-Year Treasury"
    TWO_YEAR_KEY = "2-Year Treasury"

    # Fetch additional data
    if hasattr(data_fetcher, "fetch_interest_rates"):
        data["interest_rates"] = data_fetcher.fetch_interest_rates()
    if hasattr(data_fetcher, "fetch_market_indices"):
        data["indices"] = data_fetcher.fetch_market_indices()
    if hasattr(data_fetcher, "fetch_economic_indicators"):
        data["economic_indicators"] = data_fetcher.fetch_economic_indicators()

    # ── Generate market index charts ──
    market_index_charts: dict = {}
    index_tickers = {
        "S&P 500": "SPY",
        "Dow Jones": "DIA",
        "Nasdaq-100": "QQQ",
        "S&P 400 MidCap": "MDY",
        "Russell 2000": "IWM",
        "S&P 500 Growth": "IVW",
        "S&P 500 Value": "IVE",
        "Dollar Index": "UUP",
        "Oil (WTI)": "USO",
        "VIX": "VIXY",
    }
    indices = data.get("indices", {})
    for group, group_indices in indices.items():
        for idx in group_indices:
            name = idx.get("name")
            ticker = index_tickers.get(name)
            if ticker:
                hist_data = data_fetcher.fetch_index_history(
                    ticker, periods=60)
                chart_path = generate_market_index_chart(
                    hist_data, report_dir, name)
                market_index_charts[name] = chart_path
    data["market_index_charts"] = market_index_charts

    try:
        gdp_growth_data = data_fetcher.get_gdp_data()
        inflation_data = data_fetcher.get_inflation_data()
        unemployment_data = data_fetcher.get_unemployment_data()
        bond_10y_data = data_fetcher.get_bond_data()
        bond_2y_data = bond_10y_data.get(
            "values_2y", []) if bond_10y_data else []

        # Combine bond data if 2Y is available
        if bond_10y_data and bond_2y_data:
            bond_data = {
                "labels": bond_10y_data["labels"],
                "values": bond_10y_data["values"],
                "values_2y": bond_2y_data,
                "title": "Treasury Yields",
            }
        else:
            bond_data = bond_10y_data

        # Generate charts
        if gdp_growth_data and gdp_growth_data.get("values"):
            data["gdp_chart_path"] = generate_gdp_chart(
                gdp_growth_data, report_dir)
        if inflation_data and inflation_data.get("values"):
            data["inflation_chart_path"] = generate_inflation_chart(
                inflation_data, report_dir)
        if unemployment_data and unemployment_data.get("values"):
            data["unemployment_chart_path"] = generate_unemployment_chart(
                unemployment_data, report_dir)
        if bond_data and bond_data.get("values"):
            data["bond_chart_path"] = generate_bond_chart(
                bond_data, report_dir)

        # Separate 10Y / 2Y Treasury charts
        if bond_10y_data and bond_10y_data.get(
                "labels") and bond_10y_data.get("values"):
            ten_year_data = {
                "labels": bond_10y_data["labels"],
                "values": bond_10y_data["values"],
            }
            data["ten_year_chart_path"] = generate_single_bond_chart(
                ten_year_data, report_dir, "ten_year_chart.html", TEN_YEAR_KEY + " Yield")
        if bond_10y_data and bond_10y_data.get(
                "labels") and bond_10y_data.get("values_2y"):
            two_year_data = {
                "labels": bond_10y_data["labels"],
                "values": bond_10y_data["values_2y"],
            }
            data["two_year_chart_path"] = generate_single_bond_chart(
                two_year_data, report_dir, "two_year_chart.html", TWO_YEAR_KEY + " Yield")

        # Style box heatmap
        style_box_data = data_fetcher.fetch_style_box_etf_data()
        style_box_heatmap_path = None
        if style_box_data and style_box_data.get("z"):
            style_box_heatmap_path = generate_style_box_heatmap(
                style_box_data, report_dir)
        data["style_box_heatmap_path"] = style_box_heatmap_path

        # Store historical data
        data.update({
            "gdp_history": gdp_growth_data,
            "inflation_history": inflation_data,
            "unemployment_history": unemployment_data,
            "bond_history": bond_data,
        })

        # Generate report HTML
        logger.info("Generating market report...")
        report_path = _generate_market_html(data, report_dir)

        if not report_path:
            raise RuntimeError("Failed to generate market report")

        # Generate metadata
        metadata = generate_metadata(
            symbol="MARKET",
            timeframe="snapshot",
            start_date=datetime.now().strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
            initial_capital=0,
            commission=0,
            report_type="market",
            directory_name=report_dir_name,
            additional_data={
                "status": "finished",
                "title": f"Market Analysis - {datetime.now().strftime('%Y-%m-%d')}",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "report_type": "snapshot",
            },
        )
        save_metadata(metadata, report_dir)

        # Post-process: inject interpretation sidebar + signal badges
        try:
            import subprocess, sys
            enhance_script = os.path.join(os.path.dirname(__file__), '../../scripts/enhance_market_report.py')
            subprocess.run([sys.executable, enhance_script, report_path],
                         capture_output=True, timeout=30)
        except Exception:
            logger.warning("Enhancement script failed (non-fatal)", exc_info=True)

        return report_path

    except Exception:
        logger.exception("Failed to generate market report")
        raise


# ── Financial report ───────────────────────────────────────────────────────

def generate_financial_report(
    symbol: str,
    output_dir: str = "public/results",
    force_refresh: bool = False,
) -> str:
    """Generate the full financial analysis report for a single symbol.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL").
        output_dir: Directory under the project root where the
                    dated report folder is created.
        force_refresh: If True, bypass data cache and regenerate
                       even if today's report already exists.

    Returns:
        Absolute path to the generated ``index.html``.
    """
    output_base_dir = os.path.join(APP_ROOT, output_dir)

    today = datetime.now().strftime("%Y%m%d")
    report_dir_name = f"financial_{symbol}_{today}"
    report_dir = os.path.join(output_base_dir, report_dir_name)

    # Short-circuit if report exists and force_refresh is not set
    if os.path.exists(report_dir) and not force_refresh:
        logger.info(
            "Report for %s on %s already exists and force_refresh is False. "
            "Using existing report.",
            symbol,
            today,
        )
        return os.path.join(report_dir, "index.html")

    os.makedirs(report_dir, exist_ok=True)

    data_fetcher = FinancialDataFetcher(force_refresh=force_refresh)

    logger.info("Fetching financial data for %s ...", symbol)
    data = data_fetcher.fetch_financial_statements(symbol, 4)
    metrics = data_fetcher.fetch_key_metrics(symbol)

    logger.info("Generating financial report for %s ...", symbol)
    report_path = _generate_financial_html(symbol, data, metrics)

    if not report_path:
        raise RuntimeError(f"Failed to generate report for {symbol}")

    return report_path
