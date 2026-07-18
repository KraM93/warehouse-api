from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Путь к БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./inventory.db"

# Общение с SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Сессии для отправки запросов в БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Класс для таблиц
Base = declarative_base()
