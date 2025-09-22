import pytest

from src.database.models.movies import ReactionType
from src.database.models.user import User
from src.schemas.movies import MovieCreateSchema
from src.utils.hash import hash_password


async def create_test_movie(db_session, name="Test Movie"):
    movie_data = MovieCreateSchema(
        name=name,
        year=2020,
        time=120,
        imdb=8.5,
        votes=1000,
        meta_score=75,
        gross=1000000,
        description="A test movie",
        price=9.99,
        certification_id=1,
        genres=["Action"],
        stars=["Actor 1"],
        directors=["Director 1"]
    )
    from src.routes.movies import create_movie
    return await create_movie(movie_data, db_session)


@pytest.mark.asyncio
async def test_list_movies(client, db_session, prepare_test_db):
    await create_test_movie(db_session, "List Movie")

    response = client.get("/movies/?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "movies" in data
    assert len(data["movies"]) >= 1


@pytest.mark.asyncio
async def test_get_movie(client, db_session):
    movie = await create_test_movie(db_session, "Single Movie")

    response = client.get(f"/movies/{movie.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Movie"


@pytest.mark.asyncio
async def test_create_movie_conflict(client, db_session):
    movie = await create_test_movie(db_session, "Conflict Movie")
    payload = {
        "name": "Conflict Movie",
        "year": 2020,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "meta_score": 75,
        "gross": 1000000,
        "description": "A test movie",
        "price": 9.99,
        "certification_id": 1,
        "genres": ["Action"],
        "stars": ["Actor 1"],
        "directors": ["Director 1"]
    }
    response = client.post("/movies/", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_react_to_movie(client, db_session):
    user = User(email="react@test.com", hashed_password=hash_password("StrongPa$$worD"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movie = await create_test_movie(db_session, "React Movie")

    from src.main import app
    from src.routes.movies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(f"/movies/movies/{movie.id}/react/{ReactionType.like.value}")
    assert response.status_code == 200
    assert "like added" in response.json()["message"]

    response = client.get(f"/movies/movies/{movie.id}/reactions")
    assert response.status_code == 200
    data = response.json()
    assert data["likes"] == 1

    response = client.post(f"/movies/movies/{movie.id}/react/{ReactionType.dislike.value}")
    assert response.status_code == 200
    assert "dislike added" in response.json()["message"]

    response = client.get(f"/movies/movies/{movie.id}/reactions")
    assert response.status_code == 200
    data = response.json()
    assert data["dislikes"] == 1


@pytest.mark.asyncio
async def test_react_to_movie_multiple_times(client, db_session):
    user = User(email="react1@test.com", hashed_password=hash_password("StrongPa$$worD"), is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movie = await create_test_movie(db_session, "React Movie2")

    from src.main import app
    from src.routes.movies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(f"/movies/movies/{movie.id}/react/{ReactionType.like.value}")
    assert response.status_code == 200
    assert "like added" in response.json()["message"]

    response = client.post(f"/movies/movies/{movie.id}/react/{ReactionType.like.value}")
    assert response.status_code == 200
    assert "like added" in response.json()["message"]
    client.post(f"/movies/movies/{movie.id}/react/{ReactionType.like.value}")

    response = client.get(f"/movies/movies/{movie.id}/reactions")
    assert response.status_code == 200
    data = response.json()
    assert data["likes"] == 1


@pytest.mark.asyncio
async def test_add_and_list_comments_comment_reaction(client, db_session):
    user = User(email="comment@test.com", hashed_password="pass", is_active=True, group_id=1)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movie = await create_test_movie(db_session, "Comment Movie")

    from src.main import app
    from src.routes.movies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    payload = {"content": "Great movie!"}
    response = client.post(f"/movies/movies/{movie.id}/comments", json=payload)
    assert response.status_code == 200
    comment_data = response.json()
    assert comment_data["content"] == "Great movie!"

    response = client.post(f"/movies/comments/1/react/{ReactionType.like.value}")
    assert response.status_code == 200
    assert "like added" in response.json()["message"]

    response = client.get(f"/movies/movies/{movie.id}/comments")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["content"] == "Great movie!"
    print(data)
    assert data["items"][0]["likes"] == 1
