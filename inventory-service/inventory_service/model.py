from sqlmodel import SQLModel, create_engine, Field
from dotenv import load_dotenv
import os

# Determine which environment file to load
env = os.getenv("ENV", "development")  # Default to "development" if ENV is not set
print(env)
if env == "development":
    load_dotenv(".env.dev")
elif env == "production":
    load_dotenv(".env.prod")
else:
    raise ValueError(f"Unknown environment: {env}")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

class Item(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str = None

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
