from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPAuthorizationCredentials
from server.models import get_model_manager
from server.api.auth import get_current_user_id, security
from config.backend.logger import get_api_logger
from typing import List, Dict
from datetime import datetime, timedelta

logger = get_api_logger("income")

router = APIRouter(prefix="/api/income", tags=["income"])

# Map period labels to months
PERIOD_MONTHS = {
    "1m": 1,
    "3m": 3,
    "6m": 6,
    "1y": 12,
    "3y": 36,
}


@router.get("/history")
async def get_income_history(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    period: str = Query(
        "1y", description="Time period: 1m, 3m, 6m, 1y, 3y")
) -> Dict:
    """Get income history aggregated by month for the given period.

    Income sources: dividends (paid), interest payments, and other credits.
    Returns monthly totals for charting and summary stats.
    """
    try:
        user_id = await get_current_user_id(credentials)
        if not user_id:
            logger.warning("No user ID provided, returning empty income history")
            return {
                "monthly": [],
                "summary": {
                    "total": 0.0,
                    "monthly_avg": 0.0,
                    "best_month": None,
                    "months_count": 0,
                },
                "period": period,
            }

        # Determine date range
        months = PERIOD_MONTHS.get(period, 12)
        cutoff = datetime.now() - timedelta(days=months * 30)

        model_manager = get_model_manager()

        # Fetch dividends (primary income source)
        dividends = model_manager.get_dividends(user_id)

        # Filter to paid/received dividends within the period
        monthly = {}  # "YYYY-MM" -> total

        for d in dividends:
            state = d.get("state", "")
            # Include paid dividends (Robinhood dividends often have state=None)
            if state not in ("paid", None, ""):
                continue

            # Use payable_date or date field
            raw_date = d.get("payable_date") or d.get("date") or ""
            if not raw_date:
                continue

            try:
                dt = datetime.strptime(raw_date[:10], "%Y-%m-%d")
            except (ValueError, IndexError):
                continue

            if dt < cutoff:
                continue

            amount = float(d.get("amount", 0))
            if amount <= 0:
                continue

            month_key = raw_date[:7]  # "YYYY-MM"
            if month_key not in monthly:
                monthly[month_key] = {"total": 0.0, "count": 0, "sources": {}}
            monthly[month_key]["total"] += amount
            monthly[month_key]["count"] += 1
            sym = d.get("symbol", "UNKNOWN")
            monthly[month_key]["sources"][sym] = (
                monthly[month_key]["sources"].get(sym, 0) + amount
            )

        # Sort monthly keys chronologically
        sorted_keys = sorted(monthly.keys())

        # Build monthly array
        monthly_data = []
        for key in sorted_keys:
            m = monthly[key]
            monthly_data.append({
                "month": key,
                "total": round(m["total"], 2),
                "count": m["count"],
                "sources": m["sources"],
            })

        # Compute summary
        totals = [m["total"] for m in monthly_data]
        total_income = sum(totals)
        months_count = len(monthly_data)
        monthly_avg = round(total_income / months_count, 2) if months_count > 0 else 0.0

        best_month = None
        if monthly_data:
            best = max(monthly_data, key=lambda x: x["total"])
            best_month = {"month": best["month"], "total": best["total"]}

        result = {
            "monthly": monthly_data,
            "summary": {
                "total": round(total_income, 2),
                "monthly_avg": monthly_avg,
                "best_month": best_month,
                "months_count": months_count,
            },
            "period": period,
        }

        logger.info(
            f"Income history for user {user_id}, period {period}: "
            f"{months_count} months, total={total_income:.2f}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting income history: {e}")
        return {
            "monthly": [],
            "summary": {
                "total": 0.0,
                "monthly_avg": 0.0,
                "best_month": None,
                "months_count": 0,
            },
            "period": period,
        }