"""
Database configuration and session management.

Provides SQLAlchemy engine, session factory, and Base class for ORM models.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# [Анализ] Двухуровневая конфигурация подключения: если задана готовая
# строка DATABASE_URL (так и происходит в docker-compose.yml), она
# используется как есть; иначе строка собирается из отдельных
# переменных POSTGRES_* с разумными значениями по умолчанию для
# локальной разработки без Docker.
# Prefer single DATABASE_URL, fall back to individual pieces if absent
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER", "dev")
    pw = os.getenv("POSTGRES_PASSWORD", "dev")
    name = os.getenv("POSTGRES_DB", "devtrackr")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    DATABASE_URL = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{name}"

# Manage connections/pool to psql
# [Анализ] pool_pre_ping=True — перед выдачей соединения из пула
# SQLAlchemy посылает лёгкий проверочный запрос; спасает от ошибок
# "MySQL/Postgres server has gone away" при долго простаивающих
# соединениях (актуально для контейнеров, которые могут перезапускаться).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create short-lived sessions per req
# [Анализ] autocommit=False + autoflush=False: транзакция и запись в БД
# происходят только тогда, когда прикладной код явно вызывает
# db.commit() — что уже гарантирует контроль над границами транзакции
# в каждом роуте (важно для команд с несколькими шагами, например,
# "остановить таймер и обновить task.actual_minutes").
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# All ORM models inherit from this so Alembic can find metadata
Base = declarative_base()
