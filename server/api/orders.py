from fastapi import APIRouter, Request, HTTPException, Body
from server.models import get_model_manager, Order, validate_order_data, transform_pocketbase_record, transform_to_pocketbase_data
from server.api.auth import get_current_user_id
from utils.logger import get_server_logger
from typing import Dict, List

logger = get_server_logger("orders")

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/")
async def get_orders(request: Request) -> Dict:
    """Get all orders for the current user."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Orders API called without authentication - expected for fresh starts")
            return {"orders": []}

        # Get raw orders from PocketBase
        raw_orders = get_model_manager().get_orders(user_id)

        # Transform to Pydantic models for validation
        orders = []
        for raw_order in raw_orders:
            try:
                order = transform_pocketbase_record(raw_order, Order)
                orders.append(order)
            except Exception as e:
                logger.warning(
                    f"Invalid order data: {e}, skipping order {
                        raw_order.get(
                            'id', 'unknown')}")
                continue

        # Convert back to dictionaries for API response
        order_dicts = [transform_to_pocketbase_data(order) for order in orders]

        return {"orders": order_dicts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to get orders")


@router.post("/")
async def create_order(request: Request, order_data: Dict = Body(...)):
    """Create a new order."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Orders API called without authentication - expected for fresh starts")
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        # Add user_id to order data
        order_data['user'] = user_id

        # Validate order data using Pydantic model
        try:
            validated_order = validate_order_data(order_data)
        except Exception as e:
            logger.error(f"Order validation failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order data: {e}")

        # Create order in database
        result = get_model_manager().create_order(validated_order)
        return {"success": True, "order": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")


@router.put("/{order_id}")
async def edit_order(
        order_id: str,
        order: dict = Body(...),
        request: Request = None):
    """Update an existing order in PocketBase."""
    try:
        logger.info(f"Updating order {order_id}...")

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Orders API called without authentication - expected for fresh starts")
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        # Note: ModelManager doesn't have update_order method yet, so we'll need to implement it
        # For now, we'll return an error
        raise HTTPException(status_code=501,
                            detail="Update order not implemented yet")
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update order")


@router.delete("/{order_id}")
async def delete_order(order_id: str, request: Request = None):
    """Delete an order from PocketBase."""
    try:
        logger.info(f"Deleting order {order_id}...")

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Orders API called without authentication - expected for fresh starts")
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        # Note: ModelManager doesn't have delete_order method yet, so we'll need to implement it
        # For now, we'll return an error
        raise HTTPException(status_code=501,
                            detail="Delete order not implemented yet")
    except Exception as e:
        logger.error(f"Error deleting order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete order")
