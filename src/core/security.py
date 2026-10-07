"""
Security utilities for authentication and authorization.

Provides password hashing, JWT token creation and verification.
"""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import Config

# [Анализ] Вся аутентификация построена на stateless JWT: сервер не хранит
# сессии и не может отозвать конкретный токен до истечения его TTL —
# единственный способ "разлогинить" пользователя раньше времени — это
# выставить User.is_active=False (проверяется отдельно в dependencies.py).

# Security configuration
SECRET_KEY = Config.SECRET_KEY
ALGORITHM = "HS256"  # JWT algorithm - standard constant
ACCESS_TOKEN_EXPIRE_MINUTES = Config.ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing
# [Анализ] bcrypt с автоматическим маркированием устаревших схем
# (deprecated="auto") — если в будущем схему хеширования сменят,
# passlib сам подскажет, какие хэши пора перевычислить при следующем
# успешном логине.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        # [Анализ] Этот запасной вариант (15 минут) фактически "мёртвый
        # код" в текущем состоянии проекта: единственный вызывающий код
        # (routes/auth.py) всегда передаёт expires_delta, построенный из
        # ACCESS_TOKEN_EXPIRE_MINUTES (по умолчанию 30 минут).
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str | None:
    """Verify JWT token and return email."""
    # [Анализ] Функция возвращает email (claim "sub"), а НЕ user_id.
    # Из-за этого dependencies.get_current_user каждый раз делает
    # дополнительный SELECT users WHERE email=... — по токену нельзя
    # напрямую получить ID пользователя без похода в БД.
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        # [Анализ] Любая ошибка JWT (просроченный токен, неверная подпись,
        # некорректный формат) единообразно превращается в None — вызывающая
        # сторона (dependencies.py) трактует None как HTTP 401.
        return None
