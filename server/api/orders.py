import os, json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import get_widget_logger

# Initialize logger for orders widget
logger = get_widget_logger('orders')

router = APIRouter(prefix="/api/orders", tags=["orders"])
ORDERS_PATH = os.path.join("public", "data", "orders.json")

# Helper: load/save orders
def load_orders():
    if not os.path.exists(ORDERS_PATH):
        return []
    with open(ORDERS_PATH, "r") as f:
        return json.load(f)

def save_orders(orders):
    with open(ORDERS_PATH, "w") as f:
        json.dump(orders, f, indent=2)

@router.get("")
def get_orders() -> List[Dict]:
    logger.debug("Fetching all orders")
    return load_orders()

@router.post("")
def add_order(order: dict = Body(...)):
    orders = load_orders()
    order["id"] = order.get("id") or (max([o["id"] for o in orders], default=0) + 1)
    orders.append(order)
    save_orders(orders)
    return {"status": "ok", "id": order["id"]}

@router.put("/{order_id}")
def edit_order(order_id: int, order: dict = Body(...)):
    orders = load_orders()
    for i, o in enumerate(orders):
        if o["id"] == order_id:
            order["id"] = order_id
            orders[i] = order
            save_orders(orders)
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Order not found")

@router.delete("/{order_id}")
def delete_order(order_id: int):
    orders = load_orders()
    new_orders = [o for o in orders if o["id"] != order_id]
    if len(new_orders) == len(orders):
        raise HTTPException(status_code=404, detail="Order not found")
    save_orders(new_orders)
    return {"status": "ok"} 