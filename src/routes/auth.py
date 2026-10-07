"""Authentication routes.

[Анализ] Реализует классическую схему JWT bearer-аутентификации:
регистрация -> хеширование пароля -> логин -> выдача токена ->
последующие запросы несут токен в заголовке Authorization.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_user, get_db
from ..core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)
from ..models import User
from ..schemas import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    # [Анализ] Эта проверка на уровне приложения — не единственная защита
    # от дублей: она подвержена состоянию гонки (два одновременных запроса
    # регистрации с одним email могут оба пройти этот SELECT до того, как
    # любой из них закоммитится). Настоящая защита — UNIQUE-ограничения
    # на email/username в БД (см. models/user.py); поэтому ниже код
    # дополнительно перехватывает IntegrityError как страховочный план
    # на случай именно такой гонки.
    existing_user = (
        db.query(User)
        .filter((User.email == user_data.email) | (User.username == user_data.username))
        .first()
    )

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        # [Анализ] Страховка от гонки, описанной выше: если UNIQUE-
        # ограничение в БД всё же нарушено (несмотря на предварительную
        # проверку), транзакция откатывается и пользователю возвращается
        # понятная ошибка вместо необработанного 500.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed"
        )


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    # Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()

    # [Анализ] "not user or not verify_password(...)" — благодаря
    # короткому замыканию (short-circuit) оператора "or", bcrypt-сравнение
    # пароля вызывается только если пользователь найден. Значит, ответ на
    # запрос с несуществующим email формируется чуть быстрее, чем с
    # существующим email и неверным паролем — небольшой временной канал
    # (timing side-channel), теоретически позволяющий отличить
    # "email не зарегистрирован" от "email есть, пароль неверный".
    # На практике для учебного проекта это не критично.
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information.

    [Анализ] Обратите внимание: здесь используется get_current_user,
    а НЕ get_current_active_user, как в большинстве других защищённых
    роутов — то есть деактивированный (is_active=False) пользователь
    всё ещё может посмотреть /auth/me, хотя не сможет работать с
    задачами/таймерами. Скорее всего, это не осознанное архитектурное
    решение, а недосмотр при написании кода (несогласованность выбора
    зависимости), но эффект стоит явно отметить при анализе.
    """
    return current_user
