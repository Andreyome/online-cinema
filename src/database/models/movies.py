import enum
import uuid as uuid_pkg

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DECIMAL, UniqueConstraint, Table, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database.models.base import Base

movie_genres = Table(
    "movie_genres", Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)

movie_directors = Table(
    "movie_directors", Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("director_id", ForeignKey("directors.id"), primary_key=True),
)

movie_stars = Table(
    "movie_stars", Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("star_id", ForeignKey("stars.id"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uix_movie_name_year_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(String, default=lambda: str(uuid_pkg.uuid4()), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float] = mapped_column(nullable=True)
    gross: Mapped[float] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)

    reactions = relationship("MovieReaction", back_populates="movie")
    certification = relationship("Certification", backref="movies")
    genres = relationship("Genre", secondary="movie_genres", backref="movies")
    directors = relationship("Director", secondary="movie_directors", backref="movies")
    stars = relationship("Star", secondary="movie_stars", backref="movies")



class ReactionType(enum.Enum):
    like = "like"
    dislike = "dislike"

class MovieReaction(Base):
    __tablename__ = "movie_reactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    reaction = Column(Enum(ReactionType), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uix_user_movie"),)

    # Relationships
    user = relationship("User", back_populates="reactions")
    movie = relationship("Movie", back_populates="reactions")


