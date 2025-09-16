from pydantic import BaseModel



class OrderSchema(BaseModel):
    user_id: int | None
    total_amount: float | None
    status: str | None

class MessageSchema(BaseModel):
    message: str | None

