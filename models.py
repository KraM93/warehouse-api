from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    role = Column(String, default="worker")


class Item(Base):
    # Название таблицы в БД
    __tablename__ = "items"

    # Описание колонок
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Integer, default=0)
    price = Column(Float)

    def __repr__(self):
        return f"<Item '{self.name}', qty: {self.quantity}>"

    # Таблица: история операций
class ItemLog(Base):
    __tablename__ = "item_logs"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    change_amount = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
