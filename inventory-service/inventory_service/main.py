from fastapi import FastAPI, HTTPException
from sqlmodel import Session,select
from pydantic import BaseModel
from typing import List
from .model import create_db_and_tables, Item, engine

app = FastAPI()

class ItemCreate(BaseModel):
    name: str
    description: str = None

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/items/")
async def add_item(item: ItemCreate):
    item_dict = item.dict()
    item_dict['id'] = None  # Let the database auto-generate the ID
    try:
        with Session(engine) as session:
            db_item = Item(**item_dict)
            session.add(db_item)
            session.commit()
            session.refresh(db_item)
        return session.get(Item, db_item.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/items/", response_model=List[Item])
async def get_items():
    try:
        with Session(engine) as session:
            items = session.exec(select(Item)).all()
            return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: ItemCreate):
    with Session(engine) as session:
        item = session.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = item.name
        item.description = item.description
        session.add(item)
        session.commit()
        session.refresh(item)
        
    return item

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    with Session(engine) as session:
        item = session.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
    return item

