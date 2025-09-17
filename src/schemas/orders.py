from pydantic import BaseModel, Field


class OrderSchema(BaseModel):
    """
    Schema for an order.
    """
    user_id: int | None = Field(..., description="The ID of the user who placed the order.")
    total_amount: float | None = Field(..., description="The total amount of the order.")
    status: str | None = Field(..., description="The current status of the order ('Pending', 'Canceled', 'Paid').")


class MessageSchema(BaseModel):
    """
    A generic message schema for API responses.
    """
    message: str | None = Field(..., description="A message describing the result of an operation.")