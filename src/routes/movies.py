from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from src.database.models.movies import Movie, Genre, Star, Director, movie_genres, movie_stars, movie_directors, \
    ReactionType, MovieReaction
from src.database.models.user import User
from src.database.session import get_db
from src.deps import get_current_user
from src.schemas import movies as schemas
from src.schemas.movies import MovieSchema, MovieListSchema

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/", response_model=MovieListSchema)
async def list_movies(
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        year: int | None = None,
        min_rating: float = Query(None, ge=0, le=10),
        max_rating: float = Query(None, ge=0, le=10),
        order: str = Query("asc", regex="^(asc|desc)$"),
        db: AsyncSession = Depends(get_db),
        sort_by: Literal["name", "year", "imdb", "price", "votes"] = "name",
        q: str | None = None,

):
    skip = (page - 1) * limit
    stmt = select(Movie).options(
        selectinload(Movie.genres),
        selectinload(Movie.stars),
        selectinload(Movie.directors),
        selectinload(Movie.certification),
    )

    if year:
        stmt = stmt.where(Movie.year == year)
    if min_rating is not None:
        stmt = stmt.where(Movie.imdb >= min_rating)
    if max_rating is not None:
        stmt = stmt.where(Movie.imdb <= max_rating)

    if q:
        stmt = stmt.where(
            or_(
                Movie.name.ilike(f"%{q}%"),
                Movie.description.ilike(f"%{q}%"),
                exists().where(movie_genres.c.movie_id == Movie.id)
                .where(Genre.id == movie_genres.c.genre_id)
                .where(Genre.name.ilike(f"%{q}%")),
                exists().where(movie_stars.c.movie_id == Movie.id)
                .where(Star.id == movie_stars.c.star_id)
                .where(Star.name.ilike(f"%{q}%")),
                exists().where(movie_directors.c.movie_id == Movie.id)
                .where(Director.id == movie_directors.c.director_id)
                .where(Director.name.ilike(f"%{q}%")),
            )
        )

    sort_attr = getattr(Movie, sort_by)

    if order == "desc":
        stmt = stmt.order_by(func.lower(sort_attr).desc())
    else:
        stmt = stmt.order_by(func.lower(sort_attr).asc())

    total_result = await db.execute(select(func.count(Movie.id)))
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    movies = result.scalars().unique().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    movie_list = [MovieSchema.model_validate(movie) for movie in movies]

    response = MovieListSchema(
        movies=movie_list,
        prev_page=f"/movies/?page={page - 1}&limit={limit}" if page > 1 else None,
        next_page=f"/movies/?page={page + 1}&limit={limit}" if page < total_pages else None,
        total_pages=str(total_pages),
        total_items=str(total),
    )
    return response


@router.get("/{movie_id}", response_model=schemas.MovieSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> MovieSchema:
    result = await db.execute(
        select(Movie)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
        .where(Movie.id == movie_id)
    )
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return MovieSchema.model_validate(movie)


@router.post("/", response_model=schemas.MovieSchema)
async def create_movie(
        movie_data: schemas.MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    """
    Add a new movie to the database.

    This endpoint allows the creation of a new movie with details such as
    name, year, description, genres, stars, and directors. It automatically
    handles linking or creating related entities.

    :param movie_data: The data required to create a new movie.
    :type movie_data: MovieCreate
    :param db: The SQLAlchemy async database session (provided via dependency injection).
    :type db: AsyncSession

    :return: The created movie with all details.
    :rtype: MovieSchema

    :raises HTTPException:
        - 409 if a movie with the same name and year already exists.
        - 400 if input data is invalid (e.g., violating a constraint).
    """
    # Conflict check
    existing_stmt = (select(Movie)
    .where(
        (Movie.name == movie_data.name),
        (Movie.year == movie_data.year)
    ))
    existing_result = await db.execute(existing_stmt)
    existing_movie = existing_result.scalars().first()

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{movie_data.name}' "
                f"and year '{movie_data.year}' already exists."
            )
        )

    try:
        # Genres
        genres = []
        for genre_name in movie_data.genres:
            stmt = select(Genre).where(Genre.name == genre_name)
            result = await db.execute(stmt)
            genre = result.scalars().first()
            if not genre:
                genre = Genre(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        # Stars
        stars = []
        for star_name in movie_data.stars:
            stmt = select(Star).where(Star.name == star_name)
            result = await db.execute(stmt)
            star = result.scalars().first()
            if not star:
                star = Star(name=star_name)
                db.add(star)
                await db.flush()
            stars.append(star)

        # Directors
        directors = []
        for director_name in movie_data.directors:
            stmt = select(Director).where(Director.name == director_name)
            result = await db.execute(stmt)
            director = result.scalars().first()
            if not director:
                director = Director(name=director_name)
                db.add(director)
                await db.flush()
            directors.append(director)

        # Create movie
        movie = Movie(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification_id=movie_data.certification_id,
            genres=genres,
            stars=stars,
            directors=directors,
        )

        db.add(movie)
        await db.commit()
        await db.refresh(movie)

        stmt = (
            select(Movie)
            .options(
                selectinload(Movie.genres),
                selectinload(Movie.stars),
                selectinload(Movie.directors),
                selectinload(Movie.certification),
            )
            .filter_by(id=movie.id)
        )
        result = await db.execute(stmt)
        movie_with_relations = result.scalar_one()

        return schemas.MovieSchema.model_validate(movie_with_relations, from_attributes=True)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.post("/movies/{movie_id}/react/{reaction}")
async def react_to_movie(
        movie_id: int,
        reaction: ReactionType,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Check if user already reacted
    stmt = select(MovieReaction).where(
        MovieReaction.movie_id == movie_id,
        MovieReaction.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.reaction = reaction  # Update like→dislike or vice versa
    else:
        new_reaction = MovieReaction(
            movie_id=movie_id,
            user_id=current_user.id,
            reaction=reaction
        )
        db.add(new_reaction)

    await db.commit()
    return {"message": f"{reaction.value} added"}


@router.get("/movies/{movie_id}/reactions")
async def get_movie_reactions(movie_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MovieReaction.reaction, func.count(MovieReaction.id)).where(
        MovieReaction.movie_id == movie_id
    ).group_by(MovieReaction.reaction)

    result = await db.execute(stmt)
    counts = {r: c for r, c in result.all()}
    return {
        "likes": counts.get(ReactionType.like, 0),
        "dislikes": counts.get(ReactionType.dislike, 0),
    }
