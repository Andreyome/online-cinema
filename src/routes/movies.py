from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.movies import Movie, Genre, Star, Director
from src.database.session import get_db
from src.schemas import movies as schemas
from src.schemas.movies import MovieSchema, MovieListSchema

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/", response_model=MovieListSchema)
async def list_movies(page: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    skip = (page - 1) * limit
    count = await db.execute(select(func.count(Movie.id)))
    total = count.scalar() or 0
    if not total:
        raise HTTPException(status_code=404, detail="No movies found.")

    result = await db.execute(
        select(Movie)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        ).offset(skip).limit(limit)
    )
    movies = result.scalars().unique().all()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = (total + limit - 1) // limit
    movie_list = [MovieSchema.model_validate(movie) for movie in movies]

    response = MovieListSchema(
        movies=movie_list,
        prev_page=f"/movies/?skip={skip - 1}&limit={limit}" if skip > 1 else None,
        next_page=f"/movies/?skip={skip + 1}&limit={limit}" if skip < total_pages else None,
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
