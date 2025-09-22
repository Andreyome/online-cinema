from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, aliased

from src.database.models.movies import Movie, Genre, Star, Director, movie_genres, movie_stars, movie_directors, \
    ReactionType, MovieReaction, Comment, CommentReaction
from src.database.models.user import User
from src.database.session import get_db
from src.deps import get_current_user
from src.schemas import movies as schemas
from src.schemas.movies import MovieSchema, MovieListSchema, CommentCreate, CommentSchema, CommentResponse

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/", response_model=MovieListSchema)
async def list_movies(
        page: int = Query(1, ge=1),
        limit: int = Query(10, ge=1, le=100),
        year: int | None = None,
        min_rating: float = Query(None, ge=0, le=10),
        max_rating: float = Query(None, ge=0, le=10),
        order: str = Query("asc", pattern="^(asc|desc)$"),
        db: AsyncSession = Depends(get_db),
        sort_by: Literal["name", "year", "imdb", "price", "votes"] = "name",
        q: str | None = None,

):
    """
    **List and filter movies.**

    This endpoint returns a paginated list of movies. It supports filtering, searching, and sorting.

    - **Filters:** `year`, `min_rating`, `max_rating`
    - **Sorting:** `sort_by` and `order` parameters
    - **Search:** `q` parameter for full-text search across movie details.

    - **Raises:**
      - `HTTPException` 404: If no movies match the search and filter criteria.

    - **Returns:**
      - `MovieListSchema`: A paginated list of movies.
    """
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
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    """
    **Retrieve a single movie by its ID.**

    This endpoint returns the detailed information for a single movie, including its genres, stars, and directors.

    - **Parameters:**
      - `movie_id`: The ID of the movie to retrieve.

    - **Raises:**
      - `HTTPException` 404: If a movie with the given ID does not exist.

    - **Returns:**
      - `MovieSchema`: The detailed movie information.
    """
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
    **Create a new movie.**

    This endpoint creates a new movie record in the database. It handles the creation of new genres, stars, and directors if they do not already exist.

    - **Raises:**
      - `HTTPException` 409: If a movie with the same name and year already exists.
      - `HTTPException` 400: For invalid input data.

    - **Returns:**
      - `MovieSchema`: The created movie object, including its relationships.
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
    """
    **Add or update a user's reaction (like/dislike) to a movie.**

    This endpoint allows an authenticated user to like or dislike a movie. If a user has already reacted, their previous reaction will be updated.

    - **Parameters:**
      - `movie_id`: The ID of the movie.
      - `reaction`: The type of reaction ('like' or 'dislike').

    - **Returns:**
      - `dict`: A confirmation message.
    """
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
    """
    **Get the total likes and dislikes for a movie.**

    This endpoint returns the total count of 'like' and 'dislike' reactions for a specific movie.

    - **Parameters:**
      - `movie_id`: The ID of the movie.

    - **Returns:**
      - `dict`: An object containing the counts for likes and dislikes.
    """
    stmt = select(MovieReaction.reaction, func.count(MovieReaction.id)).where(
        MovieReaction.movie_id == movie_id
    ).group_by(MovieReaction.reaction)

    result = await db.execute(stmt)
    counts = {r: c for r, c in result.all()}
    return {
        "likes": counts.get(ReactionType.like, 0),
        "dislikes": counts.get(ReactionType.dislike, 0),
    }


@router.post("/movies/{movie_id}/comments", response_model=CommentSchema)
async def add_comment(
        movie_id: int,
        comment: CommentCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    **Add a new comment to a movie.**

    Allows an authenticated user to post a new comment on a movie.

    - **Parameters:**
      - `movie_id`: The ID of the movie to comment on.
      - `comment`: The comment content in the request body.

    - **Returns:**
      - `CommentSchema`: The newly created comment object.
    """
    new_comment = Comment(
        user_id=current_user.id,
        movie_id=movie_id,
        content=comment.content
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    return CommentSchema(
        **new_comment.__dict__,
        likes=0,
        dislikes=0
    )


@router.delete("/comments/{comment_id}")
async def delete_comment(
        comment_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    **Delete a comment.**

    Allows a user to delete their own comment.

    - **Parameters:**
      - `comment_id`: The ID of the comment to delete.

    - **Raises:**
      - `HTTPException` 404: If the comment is not found.
      - `HTTPException` 403: If the user is not the owner of the comment.

    - **Returns:**
      - `dict`: A confirmation message.
    """
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    await db.delete(comment)
    await db.commit()
    return {"message": "Comment deleted"}


@router.post("/comments/{comment_id}/react/{reaction}")
async def react_to_comment(
        comment_id: int,
        reaction: ReactionType,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    **Add or update a user's reaction (like/dislike) to a comment.**

    Allows an authenticated user to like or dislike a specific comment. If a reaction already exists, it is updated.

    - **Parameters:**
      - `comment_id`: The ID of the comment.
      - `reaction`: The type of reaction ('like' or 'dislike').

    - **Returns:**
      - `dict`: A confirmation message.
    """
    stmt = select(CommentReaction).where(
        CommentReaction.comment_id == comment_id,
        CommentReaction.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.reaction = reaction
    else:
        new_reaction = CommentReaction(
            comment_id=comment_id,
            user_id=current_user.id,
            reaction=reaction
        )
        db.add(new_reaction)

    await db.commit()
    return {"message": f"{reaction.value} added"}


@router.get("/movies/{movie_id}/comments", response_model=CommentResponse)
async def list_comments(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),
):
    """
    **List all comments for a movie.**

    This endpoint returns a paginated list of comments for a specific movie, including the number of likes and dislikes for each comment.

    - **Parameters:**
      - `movie_id`: The ID of the movie.
      - `page`: The page number to retrieve.
      - `size`: The number of comments per page.

    - **Returns:**
      - `CommentResponse`: A paginated list of comments with reaction counts.
    """
    total_stmt = select(func.count(Comment.id)).where(Comment.movie_id == movie_id)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    stmt = (
        select(Comment)
        .where(Comment.movie_id == movie_id)
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    comments = result.scalars().all()

    if not comments:
        return CommentResponse(items=[], total=total, page=page, size=size)

    comment_ids = [c.id for c in comments]

    reaction_stmt = (
        select(
            CommentReaction.comment_id,
            CommentReaction.reaction,
            func.count(CommentReaction.id).label("count"),
        )
        .where(CommentReaction.comment_id.in_(comment_ids))
        .group_by(CommentReaction.comment_id, CommentReaction.reaction)
    )
    reaction_result = await db.execute(reaction_stmt)

    reaction_map: dict[int, dict[str, int]] = {}
    for comment_id, reaction, count in reaction_result.all():
        if comment_id not in reaction_map:
            reaction_map[comment_id] = {"like": 0, "dislike": 0}
        reaction_map[comment_id][reaction.value] = count

    items = [
        CommentSchema(
            **c.__dict__,
            likes=reaction_map.get(c.id, {}).get("like", 0),
            dislikes=reaction_map.get(c.id, {}).get("dislike", 0),
        )
        for c in comments
    ]

    total_pages = (total + size - 1) // size

    return CommentResponse(
        items=items,
        total_items=str(total),
        total_pages=str(total_pages),
        prev_page=f"/movies/{movie_id}/comments/?page={page - 1}&limit={size}" if page > 1 else None,
        next_page=f"/movies/{movie_id}/comments/?page={page + 1}&limit={size}" if page < total else None,
    )
