from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class GenreSchema(BaseModel):
    id: int = Field(..., description="The unique ID of the genre.")
    name: str = Field(..., description="The name of the genre (e.g., 'Action', 'Drama').")

    class Config:
        from_attributes = True


class StarSchema(BaseModel):
    id: int = Field(..., description="The unique ID of the star.")
    name: str = Field(..., description="The name of the star.")

    class Config:
        from_attributes = True


class DirectorSchema(BaseModel):
    id: int = Field(..., description="The unique ID of the director.")
    name: str = Field(..., description="The name of the director.")

    class Config:
        from_attributes = True


class CertificationSchema(BaseModel):
    id: int = Field(..., description="The unique ID of the movie certification.")
    name: str = Field(..., description="The name of the certification (e.g., 'PG-13', 'R').")

    class Config:
        from_attributes = True


class MovieBase(BaseModel):
    name: str = Field(..., description="The title of the movie.")
    year: int = Field(..., description="The release year of the movie.")
    time: int = Field(..., description="The runtime of the movie in minutes.")
    imdb: float = Field(..., description="The IMDb rating of the movie.")
    votes: int = Field(..., description="The number of votes the movie has received on IMDb.")
    description: str = Field(..., description="A brief summary of the movie's plot.")
    price: float = Field(..., description="The price of the movie.")
    certification_id: int = Field(..., description="The ID of the movie's certification.")


class MovieSchema(MovieBase):
    id: int = Field(..., description="The unique ID of the movie.")
    uuid: str = Field(..., description="The unique identifier for the movie.")
    certification: Optional[CertificationSchema] = Field(None, description="The movie's certification details.")
    genres: List[GenreSchema] = Field(..., description="A list of genres associated with the movie.")
    stars: List[StarSchema] = Field(..., description="A list of the main stars in the movie.")
    directors: List[DirectorSchema] = Field(..., description="A list of directors of the movie.")

    class Config:
        from_attributes = True


class MovieCreateSchema(BaseModel):
    """
    Schema for creating a new movie.
    """
    name: str = Field(..., example="Inception", description="The title of the movie.")
    year: int = Field(..., example=2010, description="The release year of the movie.")
    time: int = Field(..., example=148, description="The runtime of the movie in minutes.")
    imdb: float = Field(..., example=8.8, description="The IMDb rating.")
    votes: int = Field(..., example=2400000, description="The number of votes.")
    meta_score: Optional[float] = Field(None, example=74, description="The Metascore.")
    gross: Optional[float] = Field(None, example=292.58, description="The gross revenue in millions USD.")
    description: str = Field(..., example="A thief who enters the dreams of others...",
                             description="A brief summary of the movie's plot.")
    price: float = Field(..., example=19.99, description="The price of the movie.")
    certification_id: int = Field(..., example=1, description="The ID of the movie's certification.")
    genres: List[str] = Field(..., example=["Action", "Sci-Fi"], description="A list of genre names.")
    stars: List[str] = Field(..., example=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
                             description="A list of star names.")
    directors: List[str] = Field(..., example=["Christopher Nolan"], description="A list of director names.")

    class Config:
        from_attributes = True


class MovieListSchema(BaseModel):
    """
    Schema for a paginated list of movies.
    """
    movies: List[MovieSchema]
    prev_page: Optional[str] = Field(None, description="URL for the previous page of results.")
    next_page: Optional[str] = Field(None, description="URL for the next page of results.")
    total_pages: Optional[str] = Field(None, description="Total number of pages available.")
    total_items: Optional[str] = Field(None, description="Total number of movies matching the query.")


class CommentCreate(BaseModel):
    """
    Schema for creating a new comment.
    """
    content: str = Field(..., description="The content of the comment.")


class CommentSchema(BaseModel):
    """
    Schema for a comment with reaction counts.
    """
    id: int = Field(..., description="The ID of the comment.")
    content: str = Field(..., description="The content of the comment.")
    created_at: datetime = Field(..., description="The timestamp when the comment was created.")
    updated_at: datetime | None = Field(None, description="The timestamp when the comment was last updated.")
    user_id: int = Field(..., description="The ID of the user who posted the comment.")
    likes: int = Field(..., description="The number of 'like' reactions on the comment.")
    dislikes: int = Field(..., description="The number of 'dislike' reactions on the comment.")

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """
    Schema for a paginated list of comments.
    """
    items: List[CommentSchema]
    prev_page: Optional[str] = Field(None, description="URL for the previous page of comments.")
    next_page: Optional[str] = Field(None, description="URL for the next page of comments.")
    total_pages: Optional[str] = Field(None, description="Total number of comment pages available.")
    total_items: Optional[str] = Field(None, description="Total number of comments for the movie.")
