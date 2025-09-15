from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.cart import Cart, CartItem, Purchase
from src.database.models.movies import Movie
from src.database.session import get_db
from src.deps import get_current_user
from src.schemas.cart import CartSchema, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("/", response_model=CartSchema)
async def get_cart(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """
    Retrieves the user's cart and its items. A cart is created if it does not exist.
    """
    stmt = (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie).selectinload(Movie.genres))
    )
    result = await db.execute(stmt)
    cart = result.scalar_one_or_none()

    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        return CartSchema(id=cart.id, items=[])

    return CartSchema(id=cart.id, items=cart.items)


@router.post("/add/{movie_id}", response_model=CartResponse)
async def add_movie_to_cart(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    # Check if the movie exists first
    movie_stmt = select(Movie).where(Movie.id == movie_id)
    movie = await db.scalar(movie_stmt)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
    # Check if the movie has already been purchased by the user
    purchased_stmt = select(Purchase).where(
        Purchase.user_id == user.id,
        Purchase.movie_id == movie_id
    )
    purchased_movie = await db.scalar(purchased_stmt)
    if purchased_movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already purchased this movie."
        )

    cart_stmt = select(Cart).where(Cart.user_id == user.id)
    cart = await db.scalar(cart_stmt)
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

    cart_item_stmt = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == movie_id
    )
    existing_item = await db.scalar(cart_item_stmt)
    if existing_item:
        return {"message": "Movie is already in the cart."}

    new_item = CartItem(cart_id=cart.id, movie_id=movie_id)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    return {"message": "Movie successfully added to cart."}


# In the same file as the other cart routes

@router.delete("/remove/{movie_id}", response_model=CartResponse)
async def remove_movie_from_cart(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    # Get the user's cart
    cart_stmt = select(Cart).where(Cart.user_id == user.id)
    cart = await db.scalar(cart_stmt)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found."
        )

    # Find the specific item in the cart
    cart_item_stmt = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == movie_id
    )
    cart_item = await db.scalar(cart_item_stmt)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found in cart."
        )

    # Delete the item
    await db.delete(cart_item)
    await db.commit()

    return {"message": "Movie successfully removed from cart."}


# In the same file as the other cart routes

@router.post("/pay", response_model=CartResponse)
async def pay_for_cart(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    # Get the user's cart and its items
    cart_stmt = (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    cart = await db.scalar(cart_stmt)
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty."
        )

    # pay logic

    # Move items from cart to purchases
    for item in cart.items:
        new_purchase = Purchase(user_id=user.id, movie_id=item.movie_id)
        db.add(new_purchase)

    # Clear the cart by deleting the items
    for item in cart.items:
        await db.delete(item)

    await db.commit()

    return {"message": "Payment successful! All movies have been purchased."}


# In the same file as the other cart routes

@router.delete("/clear", response_model=CartResponse)
async def clear_cart(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    # Find the user's cart and items
    cart_stmt = (
        select(Cart)
        .where(Cart.user_id == user.id)
        .options(selectinload(Cart.items))
    )
    cart = await db.scalar(cart_stmt)
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found."
        )

    # Delete all items in the cart
    if cart.items:
        for item in cart.items:
            await db.delete(item)
        await db.commit()

    return {"message": "Cart successfully cleared."}


