import pytest

from src.database.models.user import User
from src.utils.hash import hash_password
from src.main import app

from src.test.test_movie import create_test_movie


@pytest.mark.asyncio
async def test_get_empty_cart(client, db_session):
    user = User(email="cart_empty@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    from src.routes.cart import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/cart/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["items"] == []


@pytest.mark.asyncio
async def test_add_movie_to_cart(client, db_session):
    user = User(email="cart_add@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    app.dependency_overrides[lambda: None] = lambda: user
    from src.routes.cart import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Cart Movie 1")

    response = client.post(f"/cart/add/{movie.id}")
    assert response.status_code == 200
    assert "successfully added" in response.json()["message"]

    response2 = client.post(f"/cart/add/{movie.id}")
    assert response2.status_code == 200
    assert "already in the cart" in response2.json()["message"]


@pytest.mark.asyncio
async def test_remove_movie_from_cart(client, db_session):
    user = User(email="cart_remove@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    from src.routes.cart import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Cart Movie 2")
    client.post(f"/cart/add/{movie.id}")

    response = client.delete(f"/cart/remove/{movie.id}")
    assert response.status_code == 200
    assert "successfully removed" in response.json()["message"]

    response2 = client.delete(f"/cart/remove/{movie.id}")
    assert response2.status_code == 404
    assert "Movie not found in cart" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_pay_for_cart(client, db_session):
    user = User(email="cart_pay@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    from src.routes.cart import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    movie = await create_test_movie(db_session, "Cart Movie 3")
    client.post(f"/cart/add/{movie.id}")

    response = client.post("/cart/pay")
    assert response.status_code == 200
    assert "Payment successful" in response.json()["message"]

    response2 = client.post("/cart/pay")
    assert response2.status_code == 400
    assert "Cart is empty" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_clear_cart(client, db_session):
    user = User(email="cart_clear@test.com", hashed_password=hash_password("pass"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    from src.routes.cart import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    movie1 = await create_test_movie(db_session, "Cart Movie 4")
    movie2 = await create_test_movie(db_session, "Cart Movie 5")
    client.post(f"/cart/add/{movie1.id}")
    client.post(f"/cart/add/{movie2.id}")

    response = client.delete("/cart/clear")
    assert response.status_code == 200
    assert "successfully cleared" in response.json()["message"]
