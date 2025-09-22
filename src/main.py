from fastapi import FastAPI

from src.config.settings import settings
from src.database.models.base import Base
from src.database.session import engine
from src.routes.auth import router as auth_router
from src.routes.movies import router as movie_router
from src.routes.cart import router as cart_router
from src.routes.orders import router as orders_router

if settings.ENVIRONMENT == "production":
    app = FastAPI(docs_url=None, redoc_url=None)
else:
    app = FastAPI(
        title="Online Cinema API",
        description="An API for managing an online cinema platform, including user authentication, movie listings, shopping carts and orders",
        openapi_tags=[
            {"name": "orders", "description": "Endpoints for managing user orders and their status."},
            {"name": "auth", "description": "User creation, authentication, and profile management."},
            {"name": "movies", "description": "Endpoints for retrieving and managing movie data."},
            {"name": "cart", "description": "Endpoints for retrieving and managing cart data."},
        ]
    )

app.include_router(auth_router)
app.include_router(movie_router)
app.include_router(cart_router)

app.include_router(orders_router)
