import pytest

from src.database.models.user import User
from src.database.models.cart import Cart, CartItem
from src.database.models.orders import Order, OrderStatusesEnum
from src.utils.hash import hash_password
from src.main import app
from src.routes.orders import get_current_user, get_current_admin

from src.test.test_movie import create_test_movie


@pytest.mark.asyncio
async def test_create_order_from_cart(client, db_session):
    user = User(email="order_create@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Order Movie 1")

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
    await db_session.commit()

    response = client.post("/orders/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == OrderStatusesEnum.Pending.value
    assert float(data["total_amount"]) == float(movie.price)


@pytest.mark.asyncio
async def test_create_order_empty_cart(client, db_session):
    user = User(email="order_empty@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post("/orders/")
    assert response.status_code == 404
    assert "Cart not found or is empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cancel_order(client, db_session):
    user = User(email="order_cancel@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Order Movie 2")

    order = Order(user_id=user.id, status=OrderStatusesEnum.Pending, total_amount=movie.price)
    db_session.add(order)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(order)

    response = client.patch(f"/orders/{order.id}/cancel/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == OrderStatusesEnum.Canceled.value


@pytest.mark.asyncio
async def test_cancel_nonexistent_order(client, db_session):
    user = User(email="order_notfound@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.patch("/orders/999/cancel/")
    assert response.status_code == 404
    assert "Order not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_orders(client, db_session):
    user = User(email="order_list@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Order Movie 3")

    order = Order(user_id=user.id, status=OrderStatusesEnum.Pending, total_amount=movie.price)
    db_session.add(order)
    await db_session.commit()

    response = client.get("/orders/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["status"] == OrderStatusesEnum.Pending.value


@pytest.mark.asyncio
async def test_get_orders_not_found(client, db_session):
    user = User(email="order_list_empty@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/orders/")
    assert response.status_code == 404
    assert "No orders found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_get_all_orders(client, db_session):
    admin = User(email="admin@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=2)
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    app.dependency_overrides[get_current_admin] = lambda: admin

    user = User(email="order_user@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movie = await create_test_movie(db_session, "Admin Order Movie")
    order = Order(user_id=user.id, status=OrderStatusesEnum.Pending, total_amount=movie.price)
    db_session.add(order)
    await db_session.commit()

    response = client.get("/admin/orders?sort_by=created_at&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == OrderStatusesEnum.Pending.value


@pytest.mark.asyncio
async def test_admin_get_all_orders_invalid_status(client, db_session):
    admin = User(email="admin_invalid@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=2)
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    app.dependency_overrides[get_current_admin] = lambda: admin

    response = client.get("/admin/orders?status=wrongstatus")
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


