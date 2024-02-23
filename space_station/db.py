import os
from typing import Sequence
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.expression import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

from space_station.models import (
    Kosmonaut,
)  # Has to be imported for SQLModel.metadata.create_all to work


logger = logging.getLogger(__name__)

db_password_file = os.environ.get("DB_PASSWORD_FILE", None)
db_user = os.environ.get("DB_USER", "station")
db_port = os.environ.get("DB_PORT", 5432)

# get host - if there is a k8s defined env var, use it.
db_env_host = os.environ.get("DB_HOST", "localhost")
db_host_k8s = os.environ.get("SPACE_STATION_POSTGRES_SERVICE_HOST", None)
db_host = db_host_k8s or db_env_host

if db_password_file:
    with open(db_password_file, "r") as f:
        db_password = f.readline().rstrip()
        print(f"FROM FILE: {db_password}...")
else:
    db_password = os.environ.get("DB_PASSWORD", "test_password")

database_url = (
    f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/station"
)

engine = create_async_engine(database_url, echo=False, max_overflow=0, pool_size=100)

ASession = async_sessionmaker(engine)


async def db_init():
    # Heh, this is reeeally bad security...
    logger.info("Connecting to database at %s", database_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_kosmonaut(db: AsyncSession, kosmo_id: int) -> Kosmonaut | None:
    """
    Returns the db instance of kosmonaut or None if there is no kosmonaut by
    the ID in the database
    """
    # mypy has problems with the bool expression in the where clause
    # TODO: fix the mypy errors in this module...
    result = await db.scalars(select(Kosmonaut).where(Kosmonaut.id == kosmo_id))  # type: ignore
    return result.first()


async def get_kosmonaut_by_name(db: AsyncSession, kosmo_name: str) -> Kosmonaut | None:
    """
    Returns the db instance of kosmonaut or None if there is no kosmonaut by
    the name in the database
    """
    result = await db.scalars(select(Kosmonaut).where(Kosmonaut.name == kosmo_name))  # type: ignore
    return result.first()


async def get_kosmonaut_list(
    db: AsyncSession, start: int = 0, limit: int = 20
) -> Sequence[Kosmonaut]:
    """
    Returns list of kosmonauts in database
    """
    result = await db.scalars(select(Kosmonaut).offset(start).limit(limit))
    return result.all()


async def create_kosmonaut(
    db: AsyncSession, kosmo: Kosmonaut
) -> tuple[bool, Kosmonaut]:
    """
    Returns a tuple (created: bool, kosmonaut: Kosmonaut)
    - *created*:  false if there is already kosmonaut by the same name in the database
              and no new kosmonaut is added
    - *kosmonaut*: the instance of kosmonaut in database

    """
    # if kosmonaut by same name is in db already, we don't create new one
    db_kosmonaut = await get_kosmonaut_by_name(db, kosmo.name)
    if db_kosmonaut:
        return (False, db_kosmonaut)

    db.add(kosmo)
    await db.commit()
    await db.refresh(kosmo)
    return (True, kosmo)


async def update_kosmonaut_age(
    db: AsyncSession, kosmo_id: int, new_age: int
) -> Kosmonaut | None:
    """
    Returns the db instance of kosmonaut or None if there is no kosmonaut by
    the ID in the database
    """
    kosmo_select = await db.scalars(select(Kosmonaut).where(Kosmonaut.id == kosmo_id))  # type: ignore
    kosmo = kosmo_select.first()
    if kosmo is not None:
        kosmo.age = new_age
        await db.commit()
        await db.refresh(kosmo)
    return kosmo


async def delete_kosmonaut(db: AsyncSession, kosmo_id: int) -> Kosmonaut | None:
    """
    Returns the db instance of kosmonaut or None if there is no kosmonaut by
    the ID in the database
    """
    kosmo_select = await db.scalars(select(Kosmonaut).where(Kosmonaut.id == kosmo_id))  # type: ignore
    kosmo = kosmo_select.first()
    if kosmo is not None:
        await db.delete(kosmo)
        await db.commit()
    return kosmo
