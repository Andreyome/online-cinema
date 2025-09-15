from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel

from src.schemas.movies import GenreSchema


class MovieInCart(BaseModel):
    id: int
    name: str
    price: Decimal
    year: int
    genres: List[GenreSchema]

    class Config:
        from_attributes = True


class CartItemSchema(BaseModel):
    id: int
    movie: MovieInCart
    added_at: datetime

    class Config:
        from_attributes = True


class CartSchema(BaseModel):
    id: int
    items: List[CartItemSchema]

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    message: str