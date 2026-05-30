from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import BigInteger
from sqlmodel import Field, Relationship, SQLModel


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    stars_price: int
    max_products: int
    check_interval_minutes: int

    users: List["User"] = Relationship(back_populates="plan")


class User(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger)  # Telegram ID
    username: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan_id: int = Field(foreign_key="plan.id")
    subscription_expires_at: Optional[datetime] = None

    plan: Plan = Relationship(back_populates="users")
    products: List["Product"] = Relationship(back_populates="user")
    payments: List["Payment"] = Relationship(back_populates="user")


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    url: str
    title: str
    current_price: Decimal = Field(
        default=Decimal("0.00"), max_digits=10, decimal_places=2
    )
    target_price: Decimal = Field(max_digits=10, decimal_places=2)
    is_favorite: bool = Field(default=False)
    threshold: Decimal = Field(default=Decimal("0.00"), max_digits=10, decimal_places=2)
    last_notified_price: Optional[Decimal] = Field(
        default=None, max_digits=10, decimal_places=2
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked_at: Optional[datetime] = None

    user: User = Relationship(back_populates="products")


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", sa_type=BigInteger)
    telegram_payment_charge_id: str
    stars_amount: int
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="payments")
