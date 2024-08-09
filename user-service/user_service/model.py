from sqlmodel import SQLModel, create_engine, Field, Column,String
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str
    email: str = Field(sa_column=Column(String, unique=True), default=None)
    password_hash: str

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
