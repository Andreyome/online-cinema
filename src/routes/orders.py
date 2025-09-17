from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.cart import Cart, CartItem, Purchase
from src.database.models.orders import OrderItem, Order, OrderStatusesEnum
from src.database.session import get_db
from src.deps import get_current_user, get_current_admin
from src.schemas.orders import OrderSchema

router = APIRouter(tags=["orders"])


@router.post("/orders/", response_model=OrderSchema)
async def create_order(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """
    **Create a new order from the user's cart.**

    This endpoint initiates a new order by converting all items in the authenticated user's cart into a pending order. It also performs checks to ensure the movies are not already purchased or part of another pending order.

    - **Raises:**
      - `HTTPException` 404: If the cart is empty or not found.
      - `HTTPException` 409: If a movie in the cart is already purchased or is in an existing pending order.

    - **Returns:**
      - `OrderSchema`: The newly created order object.
    """
    cart_stmt = (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    result = await db.execute(cart_stmt)
    cart = result.scalars().first()

    if not cart or not cart.items:
        raise HTTPException(status_code=404, detail="Cart not found or is empty")

    order_items_to_create = []
    to_pay = Decimal('0.00')

    for item in cart.items:
        purchase_stmt = select(Purchase).where(
            Purchase.movie_id == item.movie_id,
            Purchase.user_id == user.id
        )
        result = await db.execute(purchase_stmt)
        if result.scalars().first():
            raise HTTPException(status_code=409, detail=f"Movie with ID {item.movie_id} is already purchased.")

        pending_order_stmt = select(OrderItem).join(Order).where(
            OrderItem.movie_id == item.movie_id,
            Order.user_id == user.id,
            Order.status == OrderStatusesEnum.Pending
        )
        result = await db.execute(pending_order_stmt)
        if result.scalars().first():
            raise HTTPException(status_code=409,
                                detail=f"A pending order for movie with ID {item.movie_id} already exists.")

        order_items_to_create.append({
            "movie_id": item.movie.id,
            "price_at_order": item.movie.price
        })
        to_pay += item.movie.price

    new_order = Order(
        user_id=user.id,
        status=OrderStatusesEnum.Pending,
        total_amount=to_pay
    )
    db.add(new_order)
    await db.flush()

    for item_data in order_items_to_create:
        new_order_item = OrderItem(
            order_id=new_order.id,
            movie_id=item_data["movie_id"],
            price_at_order=item_data["price_at_order"]
        )
        db.add(new_order_item)

    await db.delete(cart)
    await db.commit()
    await db.refresh(new_order)

    return new_order


@router.patch("/orders/{order_id}/cancel/", response_model=OrderSchema)
async def cancel_order(
        order_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """
    **Cancel a pending order.**

    This endpoint allows a user to cancel one of their own orders if it is in a 'Pending' status.

    - **Parameters:**
      - `order_id`: The ID of the order to cancel.

    - **Raises:**
      - `HTTPException` 404: If the order is not found.
      - `HTTPException` 409: If the order is not in a 'Pending' status.

    - **Returns:**
      - `OrderSchema`: The updated order object with a 'Canceled' status.
    """
    stmt = select(Order).where(Order.id == order_id, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatusesEnum.Pending:
        raise HTTPException(status_code=409, detail=f"Order status is '{order.status.value}', cannot be canceled.")

    order.status = OrderStatusesEnum.Canceled
    await db.commit()
    await db.refresh(order)

    return order


@router.get("/orders/", response_model=List[OrderSchema])
async def get_orders(db: AsyncSession = Depends(get_db),
                     user=Depends(get_current_user)):
    """
    **Retrieve a list of all user's orders.**

    This endpoint returns all orders associated with the authenticated user, including the items within each order.

    - **Raises:**
      - `HTTPException` 404: If the user has no orders.

    - **Returns:**
      - `list[OrderSchema]`: A list of the user's orders.
    """
    stmt = select(Order).options(selectinload(Order.items)).where(Order.user_id == user.id)
    result = await db.execute(stmt)
    orders = result.scalars().all()
    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")

    return orders


@router.get("/admin/orders", response_model=list[OrderSchema])
async def get_all_orders(
        db: AsyncSession = Depends(get_db),
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        admin_user=Depends(get_current_admin)
):
    """
    **Admin-only: Retrieve all orders with filtering, pagination, and sorting.**

    This endpoint is for administrators only. It allows for advanced queries to retrieve orders based on various criteria, including user ID, date range, status, and sorting options.

    - **Raises:**
      - `HTTPException` 400: If invalid query parameters are provided for status, sort_by, or sort_order.
      - `HTTPException` 404: If no orders are found matching the criteria.

    - **Returns:**
      - `list[OrderSchema]`: A list of orders matching the specified criteria.
    """
    stmt = select(Order).options(selectinload(Order.items))

    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    if start_date and end_date:
        stmt = stmt.where(Order.created_at.between(start_date, end_date))
    elif start_date:
        stmt = stmt.where(Order.created_at >= start_date)
    elif end_date:
        stmt = stmt.where(Order.created_at <= end_date)

    if status is not None:
        try:
            order_status_enum = OrderStatusesEnum(status.capitalize())
            stmt = stmt.where(Order.status == order_status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: '{status}'")

    sortable_columns = {
        "created_at": Order.created_at,
        "total_amount": Order.total_amount,
        "user_id": Order.user_id,
        "status": Order.status,
    }

    if sort_by not in sortable_columns:
        raise HTTPException(status_code=400,
                            detail=f"Invalid sort_by parameter. Must be one of {list(sortable_columns.keys())}")

    order_column = sortable_columns[sort_by]

    if sort_order.lower() == "asc":
        stmt = stmt.order_by(asc(order_column))
    elif sort_order.lower() == "desc":
        stmt = stmt.order_by(desc(order_column))
    else:
        raise HTTPException(status_code=400, detail="Invalid sort_order parameter. Must be 'asc' or 'desc'.")

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    orders = result.scalars().unique().all()

    if not orders:
        raise HTTPException(
            status_code=404,
            detail="No orders found matching the criteria."
        )

    return orders
