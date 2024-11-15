from fastapi import FastAPI, HTTPException, Query
from sqlmodel import Session, select, SQLModel, create_engine, Field
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(".env.dev")

# Database URL and engine setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Database models
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float = Field(gt=0, description="Price must be greater than zero")
    in_stock: int = Field(ge=0, description="Stock must be non-negative")

# Function to create tables in the database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# FastAPI app instance
app = FastAPI()

# Pydantic models for request validation
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    in_stock: int

# Event handler to create tables at startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Route to create a new product
@app.post("/products/", response_model=Product)
async def create_product(product: ProductCreate):
    product_dict = product.dict()
    product_dict['id'] = None  # Let the database auto-generate the ID
    try:
        with Session(engine) as session:
            db_product = Product(**product_dict)
            session.add(db_product)
            session.commit()
            session.refresh(db_product)
        return db_product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to get all products
@app.get("/products/", response_model=List[Product])
async def get_products():
    try:
        with Session(engine) as session:
            products = session.exec(select(Product)).all()
            return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to get a specific product by ID
@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    try:
        with Session(engine) as session:
            product = session.get(Product, product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to update a product by ID
@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: ProductCreate):
    try:
        with Session(engine) as session:
            db_product = session.get(Product, product_id)
            if not db_product:
                raise HTTPException(status_code=404, detail="Product not found")
            db_product.name = product.name
            db_product.description = product.description
            db_product.price = product.price
            db_product.in_stock = product.in_stock
            session.add(db_product)
            session.commit()
            session.refresh(db_product)
            return db_product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to delete a product by ID
@app.delete("/products/{product_id}", response_model=Product)
async def delete_product(product_id: int):
    try:
        with Session(engine) as session:
            product = session.get(Product, product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            session.delete(product)
            session.commit()
            return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Route to get multiple products by IDs and calculate total price
# @app.get("/products/total_price", response_model=float)
# async def get_total_price(product_ids: List[int] = Query(...)):
#     try:
#         with Session(engine) as session:
#             products = session.exec(select(Product).where(Product.id.in_(product_ids))).all()

#             # Check if all requested products were found
#             found_product_ids = {product.id for product in products}
#             invalid_product_ids = set(product_ids) - found_product_ids
#             if invalid_product_ids:
#                 raise HTTPException(
#                     status_code=404,
#                     detail=f"Products with IDs {invalid_product_ids} not found"
#                 )

#             # Calculate the total price of the valid products
#             total_price: int = sum(product.price for product in products)
#             return total_price

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))