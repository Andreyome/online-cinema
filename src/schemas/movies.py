from typing import List, Optional
from pydantic import BaseModel


class GenreSchema(BaseModel):
    id: int
    name: str

    class Config: from_attributes = True


class StarSchema(BaseModel):
    id: int
    name: str

    class Config: from_attributes = True


class DirectorSchema(BaseModel):
    id: int
    name: str

    class Config: from_attributes = True


class CertificationSchema(BaseModel):
    id: int
    name: str

    class Config: from_attributes = True


class MovieBase(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    description: str
    price: float
    certification_id: int


class MovieSchema(MovieBase):
    id: int
    uuid: str
    certification: Optional[CertificationSchema] = None
    genres: List[GenreSchema]
    stars: List[StarSchema]
    directors: List[DirectorSchema]

    class Config: from_attributes = True


class MovieCreateSchema(MovieBase):
    uuid: str
    certification_id: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    genres: List[str]
    stars: List[str]
    directors: List[str]

    class Config: from_attributes = True


class MovieListSchema(BaseModel):
    movies: List[MovieSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: Optional[str] = None
    total_items: Optional[str] = None
