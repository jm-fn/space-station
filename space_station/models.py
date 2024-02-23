from typing import Optional
from sqlmodel import Field, SQLModel


class Kosmonaut(SQLModel, table=True):
    __tablename__ = "kosmonauti"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    age: Optional[int]
