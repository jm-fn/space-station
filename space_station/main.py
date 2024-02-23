from contextlib import asynccontextmanager
import asyncio

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from space_station import db, rabbit
from space_station.models import Kosmonaut

import logging

logging.basicConfig(format="%(levelname)s:  %(message)s", level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.db_init()
    # Perform connection
    loop = asyncio.get_running_loop()
    task = loop.create_task(rabbit.PikaConsumer.create(loop))
    await task
    yield


app = FastAPI(lifespan=lifespan)


async def get_db():
    session = db.ASession()
    try:
        yield session
    finally:
        await session.close()


@app.post("/kosmonauts/", response_model=Kosmonaut)
async def create_kosmonaut(kosmo: Kosmonaut, session: AsyncSession = Depends(get_db)):
    created, db_kosmo = await db.create_kosmonaut(session, kosmo)
    if not created:
        raise HTTPException(
            status_code=400,
            detail=f"Kosmonaut already registered with id {db_kosmo.id}",
        )
    else:
        return db_kosmo


@app.get("/kosmonauts/", response_model=list[Kosmonaut])
async def read_kosmonauts(
    start: int = 0, limit: int = 20, session: AsyncSession = Depends(get_db)
):
    kosmonauts = await db.get_kosmonaut_list(session, start, limit)
    return kosmonauts


@app.get("/kosmonauts/{kosmo_id}", response_model=Kosmonaut)
async def read_kosmonaut(kosmo_id: int, session: AsyncSession = Depends(get_db)):
    kosmo = await db.get_kosmonaut(session, kosmo_id)
    if kosmo is None:
        raise HTTPException(
            status_code=400, detail=f"Kosmonaut with id {kosmo_id} does not exist."
        )
    else:
        return kosmo


@app.post("/kosmonauts/{kosmo_id}/{age}", response_model=Kosmonaut)
async def update_kosmonaut_age(
    kosmo_id: int, age: int, session: AsyncSession = Depends(get_db)
):
    kosmonaut = await db.update_kosmonaut_age(session, kosmo_id, age)
    return kosmonaut


@app.post("/delete/{kosmo_id}", response_model=Kosmonaut)
async def delete_kosmonaut(kosmo_id: int, session: AsyncSession = Depends(get_db)):
    kosmo = await db.delete_kosmonaut(session, kosmo_id)
    if kosmo is None:
        raise HTTPException(
            status_code=400, detail=f"Kosmonaut with id {kosmo_id} does not exist."
        )
    else:
        return kosmo
