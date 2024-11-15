from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import SQLModel, Session, create_engine, select, Field, Relationship
from pydantic import BaseModel
from typing import List, Optional
from aiokafka import AIOKafkaProducer
import httpx 
import asyncio
import json
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
DATABASE_URL = os.getenv("DATABASE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")  # URL of the Product service API

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up the database engine and session
engine = create_engine(DATABASE_URL)

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[int] = Field(foreign_key="order.id")
    product_id: int
    quantity: int
    price: float

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    total_price: float = 0.0
    status: str = "pending"
    payment_status: str = "pending"
    stripe_payment_intent_id: Optional[str] = None
    items: List[OrderItem] = Relationship(back_populates="order")

class OrderCreate(BaseModel):
    user_id: int
    items: List[dict]  # Contains product_id and quantity

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    items: Optional[List[OrderItem]] = None

@app.on_event("startup")
async def on_startup():
    SQLModel.metadata.create_all(engine)
    loop = asyncio.get_event_loop()

    app.state.producer = AIOKafkaProducer(
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
    )
    
    logger.info("Starting Kafka producer...")
    retries = 5
    for _ in range(retries):
        try:
            await app.state.producer.start()
            logger.info("Kafka producer started successfully")
            break
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            if _ < retries - 1:
                logger.info("Retrying...")
                await asyncio.sleep(5)  # Wait before retrying
            else:
                raise HTTPException(status_code=500, detail="Failed to start Kafka producer")

@app.on_event("shutdown")
async def on_shutdown():
    if hasattr(app.state, 'producer'):
        logger.info("Stopping Kafka producer...")
        await app.state.producer.stop()
        logger.info("Kafka producer stopped successfully")

async def fetch_product_details(product_id: int) -> dict:
    """Fetch product details including price from Product Service."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Product with id {product_id} not found")
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch product details")


@app.post("/orders/", response_model=Order)
async def create_order(order_create: OrderCreate):
    try:
        with Session(engine) as session:
            total_price = 0.0
            order_items = []

            for item_data in order_create.items:
                product_id = item_data["product_id"]
                quantity = item_data["quantity"]

                # Fetch product details from the Product Service
                product_details = await fetch_product_details(product_id)
                price = product_details["price"]
                
                total_price += quantity * price

                order_item = OrderItem(
                    product_id=product_id,
                    quantity=quantity,
                    price=price
                )
                order_items.append(order_item)

            # Create the order with the calculated total price
            order = Order(
                user_id=order_create.user_id,
                total_price=total_price,
                status="pending",
                payment_status="pending"
            )
            session.add(order)
            session.commit()
            session.refresh(order)

            for order_item in order_items:
                order_item.order_id = order.id  # Link the order items to the order
                session.add(order_item)
            session.commit()

            # Produce event to Kafka with Stripe payment data and total price
            event_data = {
                "event": "order_created",
                "order": {
                    "id": order.id,
                    "user_id": order.user_id,
                    "total_price": order.total_price,
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "stripe_payment_intent_id": order.stripe_payment_intent_id
                }
            }
            logger.info(f"Producing order created event to Kafka: {event_data}")
            try:
                await app.state.producer.send_and_wait("order_topic", json.dumps(event_data).encode('utf-8'))
                logger.info("Order created event produced successfully")
            except Exception as e:
                logger.error(f"Failed to produce order created event to Kafka: {e}")
                raise HTTPException(status_code=500, detail="Failed to produce order created event to Kafka")

            return order
    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(status_code=500, detail=str(e))
