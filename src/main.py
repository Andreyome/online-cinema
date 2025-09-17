from fastapi import FastAPI

from src.database.models.base import Base
from src.database.session import engine
from src.routes.auth import router as auth_router
from src.routes.movies import router as movie_router
from src.routes.cart import router as cart_router
from src.routes.orders import router as orders_router
app = FastAPI()

app.include_router(auth_router)
app.include_router(movie_router)
app.include_router(cart_router)
app.include_router(orders_router)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
