import pytest
from sqlalchemy import select

from src.database.models.user import User


def test_register_user(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "strongpassword123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "email" in data
    assert data["email"] == "test@example.com"


def test_login_user_not_activated(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "password": "mypassword123"
    })

    response = client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "mypassword123"
    })
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Account not activated"


@pytest.mark.asyncio
async def test_login_user_activated_then_logout(client, db_session):
    client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "password": "mypassword123"
    })

    result = await db_session.execute(select(User).where(User.email == "login@test.com"))
    user = result.scalar_one()
    user.is_active = 1
    db_session.add(user)
    await db_session.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "mypassword123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    access_token = data["refresh_token"]

    response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": access_token})
    assert response.status_code == 200
    assert response.json()["detail"] == "Logged out"
