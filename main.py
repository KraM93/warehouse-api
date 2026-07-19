from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
import os
from dotenv import load_dotenv

# Импорт файлов
import models
from database import engine, SessionLocal

# Настройка шифровальщика
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()

SECRET_KEY = os.getenv(
    "SECRET_KEY", "ea3307e3d0f9241ae050439db99e6b1cc11247bdf7aeffa9e0dd1a86ca26f7de"
)
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Кнопка Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# Создание таблиц в БД
models.Base.metadata.create_all(bind=engine)
# Экземпляр приложения
app = FastAPI(title="Inventory API", description="Система управления складом")


# Валидация товара
class ItemCreate(BaseModel):
    name: str
    price: float


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "worker"


class UserLogin(BaseModel):
    username: str
    password: str


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    quantity: int


class LogResponse(BaseModel):
    id: int
    item_id: int
    user_id: int
    change_amount: int


class Config:
    from_attributes = True


# Подключение / Закрытие к БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET: проверка токена
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Расшифровка токена
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Токен не содержит ID пользователя"
            )
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Время действия токена истекло")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Поддельный или поврежденный токен")


# GET: проверка админа
def require_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")

        if role != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        return int(payload.get("sub"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Время действия токена истекло")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Поддельный токен")


# GET: получение по ID
@app.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    # запрос к БД: найти первую запись
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    # если ничего не найдено
    if item is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return {"status": "ok", "item": item}


# GET: Получить список товаров (с поиском и страницами)
@app.get("/items", response_model=List[ItemResponse])
def get_items(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Item)

    if search:
        query = query.filter(models.Item.name.ilike(f"%{search}%"))
    items = query.offset(skip).limit(limit).all()
    return items


# GET: Получить историю операций
@app.get("/logs", response_model=List[LogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    logs = db.query(
        models.ItemLog.order_by(models.ItemLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return logs


# POST: добавление товаров
@app.post("/items")
def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    admin_id: int = Depends(require_admin),
):
    # Создание объекта таблицы
    db_item = models.Item(name=item.name, price=item.price, quantity=0)

    # Добавление в сессию и сохранение
    db.add(db_item)
    db.commit()

    # Обновление объекта
    db.refresh(db_item)

    return {
        "status": "success",
        "message": f"Товар '{db_item.name}'" f"добавлен админом ID '{admin_id}'",
    }


# POST: регистрация
@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    print(
        "Запрос на регистрацию:" f"логин='{user.username}'," f"пароль='{user.password}'"
    )
    # Проверка на дубль логина
    existing_user = (
        db.query(models.User).filter(models.User.username == user.username).first()
    )
    print(f"Поиск: {existing_user}")

    if existing_user:
        print("Ошибка: Пользователь найден")
        raise HTTPException(
            status_code=400, detail="Пользователь с таким именем уже существует"
        )

    # Хэширование пароля
    hashed_pass = pwd_context.hash(user.password)

    # Создание пользователя
    db_user = models.User(
        username=user.username, hashed_password=hashed_pass, role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"Успех! ID пользователя: {db_user.id}")
    return {
        "status": "success",
        "message": "Пользователь успешно зарегистрирован",
        "user_id": db_user.id,
    }


# POST: вход в систему и генерация токена
@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # Ищем по логину
    db_user = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )

    # Защита: проверка на совпадение логина и пароля
    if not db_user or not pwd_context.verify(
        form_data.password, db_user.hashed_password
    ):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    # Время жизни токена
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    # Формирование токена
    token_data = {"sub": str(db_user.id), "exp": expire_time, "role": db_user.role}

    # Создание зашифрованной строки
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Отдаем токен клиенту
    return {"access_token": token, "token_type": "bearer"}


# PUT: обновление количества товара
@app.put("/items/{item_id}/quantity")
def update_quantity(
    item_id: int,
    amount_change: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    # Поиск товара
    if item is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    # Защита на минус
    if item.quantity + amount_change < 0:
        raise HTTPException(
            status_code=400,
            detail="На складе не хватает товара." f"В наличии: {item.quantity}",
        )
    # Транзакция
    try:
        item.quantity += amount_change

        new_log = models.ItemLog(
            item_id=item.id, change_amount=amount_change, user_id=current_user_id
        )
        db.add(new_log)
        db.commit()
        db.refresh(item)
        return {
            "status": "success",
            "message": "Количество обновлено и записано в историю",
            "item": item,
        }
    except Exception as e:
        db.rollback()
        print(f"Error: {repr(e)}")
        raise HTTPException(status_code=500, detail="Ошибка БД при обновлении")


# DELETE: удаление данных
@app.delete("/items/{item_id}")
def delete_item(
    item_id: int, db: Session = Depends(get_db), admin_id: int = Depends(require_admin)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")
    db.delete(item)
    db.commit()
    return {"message": f"Товар успешно удален админом ID {admin_id}"}
