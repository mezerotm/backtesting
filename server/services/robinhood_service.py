"""
Robinhood service for syncing Robinhood portfolio data into PocketBase.
Pulls stock/crypto positions, orders, and dividends via robin_stocks,
maps them to the PocketBase schema, and persists via the REST API.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

# robin_stocks — the Robinhood API wrapper
try:
    import robin_stocks.robinhood as r
    ROBIN_STOCKS_AVAILABLE = True
except ImportError:
    r = None
    ROBIN_STOCKS_AVAILABLE = False

from server.services.base_service import BaseService
from server.database.repositories.portfolio_repository import PortfolioRepository

# Suppress robin_stocks verbose logging
logging.getLogger('robin_stocks').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)


def _sanitize_symbol(symbol: str) -> Optional[str]:
    """Sanitize and validate a ticker symbol."""
    if not symbol or not isinstance(symbol, str):
        return None
    cleaned = symbol.strip().upper()
    if not cleaned or len(cleaned) > 10:
        return None
    if not cleaned.replace('.', '').isalnum():
        return None
    return cleaned


class RobinhoodService(BaseService):
    """Service for Robinhood API operations — pull, map, save."""

    def __init__(self):
        super().__init__()
        self.portfolio_repository = PortfolioRepository()

    # ── Public API ──

    async def pull_robinhood_data(self, user_id: str) -> Dict[str, Any]:
        """Pull all Robinhood data (positions, orders, dividends) and save to PocketBase."""
        try:
            self.log_operation("pull_robinhood_data", {"user_id": user_id})

            if not ROBIN_STOCKS_AVAILABLE:
                return self.handle_error(
                    Exception("robin_stocks library not available"),
                    "pull_robinhood_data"
                )

            # 1. Get Robinhood credentials from portfolio settings
            settings = await self.portfolio_repository.get_portfolio_settings(user_id)
            if not settings:
                return self.handle_error(
                    Exception("Portfolio settings not found for user"),
                    "pull_robinhood_data"
                )
            if not settings.robinhood_enabled:
                return self.handle_error(
                    Exception("Robinhood integration is not enabled"),
                    "pull_robinhood_data"
                )
            if not settings.robinhood_username or not settings.robinhood_password:
                return self.handle_error(
                    Exception("Robinhood credentials are missing"),
                    "pull_robinhood_data"
                )

            # 2. Login to Robinhood
            login_ok = await self._do_login(settings)
            if not login_ok:
                return self.handle_error(
                    Exception("Failed to authenticate with Robinhood"),
                    "pull_robinhood_data"
                )

            # 3. Pull stock positions
            self.logger.info("Pulling stock positions from Robinhood...")
            stock_positions = await _run_blocking(r.account.build_holdings, timeout=120)
            self.logger.info("Pulled %d stock positions", len(stock_positions))

            # 4. Pull crypto positions
            self.logger.info("Pulling crypto positions from Robinhood...")
            crypto_positions_raw = await _run_blocking(r.crypto.get_crypto_positions, timeout=120)
            self.logger.info("Pulled %d crypto positions", len(crypto_positions_raw))

            # 5. Pull stock orders
            self.logger.info("Pulling stock orders from Robinhood...")
            stock_orders_raw = await _run_blocking(r.orders.get_all_stock_orders, timeout=120)
            self.logger.info("Pulled %d stock orders", len(stock_orders_raw))

            # 6. Pull crypto orders
            self.logger.info("Pulling crypto orders from Robinhood...")
            crypto_orders_raw = []
            try:
                crypto_orders_raw = await _run_blocking(r.crypto.get_crypto_orders, timeout=60)
            except (AttributeError, asyncio.TimeoutError) as e:
                self.logger.warning("get_crypto_orders failed (%s), trying get_crypto_order_history...", e)
                try:
                    crypto_orders_raw = await _run_blocking(r.crypto.get_crypto_order_history, timeout=60)
                except (AttributeError, asyncio.TimeoutError) as e2:
                    self.logger.warning("get_crypto_order_history also failed (%s), skipping crypto orders", e2)
                    crypto_orders_raw = []
            self.logger.info("Pulled %d crypto orders", len(crypto_orders_raw))

            # 7. Pull dividends
            self.logger.info("Pulling dividends from Robinhood...")
            dividends_raw = await _run_blocking(r.account.get_dividends, timeout=120)
            self.logger.info("Pulled %d dividends", len(dividends_raw))

            # 8. Map and save to PocketBase
            mapped_stock = _map_stock_positions(stock_positions, user_id)
            mapped_crypto = _map_crypto_positions(crypto_positions_raw, user_id)
            all_positions = mapped_stock + mapped_crypto

            pos_result = await self._save_positions(user_id, all_positions)
            ord_result = await self._save_orders(user_id, stock_orders_raw, crypto_orders_raw)
            div_result = await self._save_dividends(user_id, dividends_raw)

            # 9. Update last_sync timestamp in portfolio settings
            await self._update_last_sync(user_id)

            self.logger.info(
                "Robinhood sync complete — positions: %d created, %d deleted; "
                "orders: %d created, %d updated; "
                "dividends: %d created",
                pos_result['created'], pos_result['deleted'],
                ord_result['created'], ord_result['updated'],
                div_result['created']
            )

            return {
                "success": True,
                "data": {
                    "positions_count": len(all_positions),
                    "orders_count": len(stock_orders_raw) + len(crypto_orders_raw),
                    "dividends_count": len(dividends_raw),
                    "message": "Robinhood data synced successfully",
                    "positions": {"stock": len(mapped_stock), "crypto": len(mapped_crypto)},
                    "orders": {"stock": len(stock_orders_raw), "crypto": len(crypto_orders_raw)},
                    "pull_timestamp": datetime.now().isoformat()
                }
            }

        except asyncio.TimeoutError:
            return self.handle_error(
                Exception("Robinhood pull timed out"),
                "pull_robinhood_data"
            )
        except Exception as e:
            self.logger.error("Unexpected error in pull_robinhood_data: %s", e)
            return self.handle_error(e, "pull_robinhood_data")

    async def get_robinhood_status(self, user_id: str) -> Dict[str, Any]:
        """Get Robinhood connection status for a user."""
        try:
            self.log_operation("get_robinhood_status", {"user_id": user_id})
            settings = await self.portfolio_repository.get_portfolio_settings(user_id)
            connected = bool(
                settings
                and settings.robinhood_enabled
                and settings.robinhood_username
                and settings.robinhood_password
            ) if settings else False
            return {
                "success": True,
                "data": {
                    "connected": connected,
                    "last_sync": settings.last_robinhood_pull if settings and hasattr(settings, 'last_robinhood_pull') else None
                }
            }
        except Exception as e:
            return self.handle_error(e, "get_robinhood_status")

    # ── Login ──

    async def _do_login(self, settings) -> bool:
        """Login to Robinhood with stored credentials."""
        try:
            if settings.robinhood_mfa:
                self.logger.info("Login with MFA...")
                try:
                    await _run_blocking(
                        lambda: r.login(settings.robinhood_username, settings.robinhood_password, mfa_code=settings.robinhood_mfa),
                        timeout=30
                    )
                except Exception:
                    # Fall back to positional MFA arg
                    await _run_blocking(
                        lambda: r.login(settings.robinhood_username, settings.robinhood_password, settings.robinhood_mfa),
                        timeout=30
                    )
            else:
                self.logger.info("Login without MFA...")
                await _run_blocking(
                    lambda: r.login(settings.robinhood_username, settings.robinhood_password),
                    timeout=30
                )
            self.logger.info("Robinhood login successful")
            return True
        except asyncio.TimeoutError:
            self.logger.error("Robinhood login timed out")
            return False
        except Exception as e:
            self.logger.error("Robinhood login failed: %s", e)
            return False

    # ── Save helpers ──

    async def _save_positions(self, user_id: str, positions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Replace all Robinhood-sourced positions for a user (delete-and-recreate)."""
        created = 0
        deleted = 0
        try:
            # Get existing Robinhood positions
            existing = self.pb_client.get_records("positions", "user='%s' && source='robinhood'" % user_id)
            for rec in existing:
                rec_id = rec.get("id") if isinstance(rec, dict) else getattr(rec, "id", None)
                if rec_id:
                    self.pb_client.delete_record("positions", rec_id)
                    deleted += 1

            # Create new positions
            for pos in positions:
                pos["source"] = "robinhood"
                pos["user"] = user_id
                pos["pulled_at"] = datetime.now().isoformat()
                for num_field in ["quantity", "buy_price", "market_value", "current_price"]:
                    if num_field in pos and pos[num_field] is not None:
                        pos[num_field] = str(pos[num_field])
                if self.pb_client.create_record("positions", pos):
                    created += 1
        except Exception as e:
            self.logger.error("Error saving positions: %s", e)
        return {"created": created, "deleted": deleted}

    async def _save_orders(self, user_id: str, stock_orders: List[Dict], crypto_orders: List[Dict]) -> Dict[str, int]:
        """Upsert orders into PocketBase by source_id."""
        created = 0
        updated = 0
        try:
            mapped_stock = _map_stock_orders(stock_orders, user_id)
            mapped_crypto = _map_crypto_orders(crypto_orders, user_id)
            all_orders = mapped_stock + mapped_crypto

            # Build a map of existing orders by source_id
            existing = self.pb_client.get_records("orders", "user='%s'" % user_id)
            existing_by_source = {}
            for rec in existing:
                rec_id = rec.get("id") if isinstance(rec, dict) else getattr(rec, "id", None)
                source_id = rec.get("source_id") if isinstance(rec, dict) else getattr(rec, "source_id", None)
                if source_id and rec_id:
                    existing_by_source[source_id] = (rec_id, rec)

            for order in all_orders:
                order["user"] = user_id
                source_id = order.get("source_id", "")
                for num_field in ["quantity", "price", "fees", "pl"]:
                    if num_field in order and order[num_field] is not None:
                        order[num_field] = str(order[num_field])

                if source_id and source_id in existing_by_source:
                    existing_id = existing_by_source[source_id][0]
                    if self.pb_client.update_record("orders", existing_id, order):
                        updated += 1
                else:
                    if self.pb_client.create_record("orders", order):
                        created += 1
        except Exception as e:
            self.logger.error("Error saving orders: %s", e)
        return {"created": created, "updated": updated}

    async def _save_dividends(self, user_id: str, raw_dividends: List[Dict]) -> Dict[str, int]:
        """Upsert dividends into PocketBase by symbol + date + amount."""
        created = 0
        updated = 0
        try:
            mapped = _map_dividends(raw_dividends, user_id)
            if not mapped:
                return {"created": 0, "updated": 0}

            # Build key map for existing dividends
            existing = self.pb_client.get_records("dividends", "user='%s'" % user_id)
            existing_by_key = {}
            for rec in existing:
                rec_id = rec.get("id") if isinstance(rec, dict) else getattr(rec, "id", None)
                sym = rec.get("symbol") if isinstance(rec, dict) else getattr(rec, "symbol", "")
                date = rec.get("date") if isinstance(rec, dict) else getattr(rec, "date", "")
                amt = rec.get("amount") if isinstance(rec, dict) else getattr(rec, "amount", "")
                key = "%s_%s_%s" % (sym, date, str(amt))
                if rec_id:
                    existing_by_key[key] = (rec_id, rec)

            for div in mapped:
                div["user"] = user_id
                div["source"] = "robinhood"
                key = "%s_%s_%s" % (div.get("symbol", ""), div.get("date", ""), str(div.get("amount", "")))
                if "amount" in div and div["amount"] is not None:
                    div["amount"] = str(div["amount"])

                if key in existing_by_key:
                    existing_id = existing_by_key[key][0]
                    if self.pb_client.update_record("dividends", existing_id, div):
                        updated += 1
                else:
                    if self.pb_client.create_record("dividends", div):
                        created += 1
        except Exception as e:
            self.logger.error("Error saving dividends: %s", e)
        return {"created": created, "updated": updated}

    async def _update_last_sync(self, user_id: str):
        """Update the last_robinhood_pull timestamp in portfolio settings."""
        try:
            existing = self.pb_client.get_records("portfolio", "user='%s'" % user_id)
            if existing:
                rec = existing[0]
                rec_id = rec.get("id") if isinstance(rec, dict) else getattr(rec, "id", None)
                if rec_id:
                    self.pb_client.update_record("portfolio", rec_id, {
                        "last_robinhood_pull": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    })
        except Exception as e:
            self.logger.warning("Failed to update last_sync: %s", e)


# ── Mapping functions ──

def _map_stock_positions(raw: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
    """Map robin_stocks build_holdings output to PocketBase positions schema."""
    mapped = []
    for symbol, data in raw.items():
        clean = _sanitize_symbol(symbol)
        if not clean:
            continue
        try:
            qty = float(data.get("quantity", 0))
            if qty <= 0:
                continue
            is_crypto = data.get("is_crypto", False)
            mapped.append({
                "symbol": clean,
                "quantity": qty,
                "buy_price": float(data.get("average_buy_price", 0)),
                "market_value": float(data.get("market_value", 0)),
                "current_price": float(data.get("price", 0)),
                "is_crypto": is_crypto,
                "source": "robinhood",
                "notes": data.get("name", ""),
            })
        except (ValueError, TypeError):
            continue
    return mapped


def _map_crypto_positions(raw: List[Dict], user_id: str) -> List[Dict[str, Any]]:
    """Map robin_stocks crypto positions to PocketBase positions schema."""
    mapped = []
    for pos in raw:
        try:
            currency = pos.get("currency", {})
            code = currency.get("code", "")
            clean = _sanitize_symbol(code)
            if not clean:
                continue
            qty = float(pos.get("quantity_available", 0))
            if qty <= 0:
                continue
            cost_bases = pos.get("cost_bases", [])
            avg_price = 0.0
            if cost_bases:
                total_cost = sum(float(cb.get("cost", 0)) for cb in cost_bases)
                total_qty = sum(float(cb.get("direct_quantity", 0)) for cb in cost_bases)
                avg_price = total_cost / total_qty if total_qty > 0 else 0.0

            mapped.append({
                "symbol": clean,
                "quantity": qty,
                "buy_price": avg_price,
                "is_crypto": True,
                "source": "robinhood",
                "notes": currency.get("name", clean),
            })
        except (ValueError, TypeError, KeyError):
            continue
    return mapped


def _map_stock_orders(raw: List[Dict], user_id: str) -> List[Dict[str, Any]]:
    """Map stock orders to PocketBase orders schema."""
    mapped = []
    for order in raw:
        try:
            instrument = order.get("instrument", "")
            symbol = order.get("symbol", "")

            side = order.get("side", "buy")
            order_id = order.get("id", "")
            executions = order.get("executions", [])
            if not executions:
                continue

            for exec_ in executions:
                qty = float(exec_.get("quantity", 0))
                price = float(exec_.get("price", 0))
                timestamp = exec_.get("timestamp", order.get("created_at", ""))

                mapped.append({
                    "symbol": symbol or "UNKNOWN",
                    "type": side,
                    "quantity": qty,
                    "price": price,
                    "date": timestamp,
                    "fees": float(exec_.get("fees", 0)),
                    "pl": float(exec_.get("settlement", 0)),
                    "source_id": order_id,
                    "notes": symbol or "",
                    "source": "robinhood",
                })
        except (ValueError, TypeError):
            continue
    return mapped


def _map_crypto_orders(raw: List[Dict], user_id: str) -> List[Dict[str, Any]]:
    """Map crypto orders to PocketBase orders schema."""
    mapped = []
    for order in raw:
        try:
            crypto_symbol = order.get("currency_pair", order.get("symbol", ""))
            if "_" in crypto_symbol:
                base = crypto_symbol.split("_")[0]
            else:
                parts = order.get("currency_code", order.get("currency_pair", "")).split("-")
                base = parts[0] if len(parts) > 0 else crypto_symbol
            clean = _sanitize_symbol(base)
            if not clean:
                continue

            side = order.get("side", "buy")
            order_id = order.get("id", "")
            executions = order.get("executions", [])
            if not executions:
                continue

            for exec_ in executions:
                qty = float(exec_.get("quantity", 0)) or float(order.get("cumulative_quantity", 0))
                price = float(exec_.get("price", 0)) or float(order.get("price", 0))
                timestamp = exec_.get("timestamp", order.get("created_at", ""))
                mapped.append({
                    "symbol": clean,
                    "type": side,
                    "quantity": qty,
                    "price": price,
                    "date": timestamp,
                    "fees": float(exec_.get("fees", 0)),
                    "pl": 0.0,
                    "source_id": order_id,
                    "notes": "crypto:" + clean,
                    "source": "robinhood_crypto",
                })
        except (ValueError, TypeError):
            continue
    return mapped


def _map_dividends(raw: List[Dict], user_id: str) -> List[Dict[str, Any]]:
    """Map dividends to PocketBase dividends schema."""
    mapped = []
    for div in raw:
        try:
            symbol = div.get("symbol", "")
            if not symbol:
                symbol = "UNKNOWN"
            clean = _sanitize_symbol(symbol)
            if not clean:
                clean = "UNKNOWN"

            mapped.append({
                "symbol": clean,
                "amount": float(div.get("amount", 0)),
                "date": div.get("payable_date", div.get("record_date", div.get("paid_at", datetime.now().isoformat()))),
                "record_date": div.get("record_date", ""),
                "payable_date": div.get("payable_date", ""),
                "source": "robinhood",
            })
        except (ValueError, TypeError):
            continue
    return mapped


async def _run_blocking(fn, timeout: int = 30):
    """Run a sync blocking function in a thread pool with timeout."""
    return await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout)