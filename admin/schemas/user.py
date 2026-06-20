"""User schemas"""
from datetime import datetime
from pydantic import BaseModel


class UserInfo(BaseModel):
    telegram_id: int
    sp_id: int | None = None
    username: str | None = None
    full_name: str | None = None
    balance: int = 0
    referrals: int = 0
    referred_by: int | None = None
    language: str = "uz"
    is_blocked: bool = False
    is_premium: bool = False
    premium_until: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: list[UserInfo]


class UserSearchRequest(BaseModel):
    query: str
    search_by: str = "telegram_id"  # telegram_id, username, sp_id


class OrderInfo(BaseModel):
    id: int
    telegram_id: int
    product_type: str
    target_username: str | None = None
    quantity: int | None = None
    amount: int | None = None
    status: str = "pending"
    external_id: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    orders: list[OrderInfo]


class OrderStatusUpdate(BaseModel):
    status: str  # pending, processing, completed, failed, cancelled
