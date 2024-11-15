from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, Session, create_engine
from typing import  Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import stripe
import asyncio
import json
from dotenv import load_dotenv
import os
import logging
import ssl

# Load environment variables from .env file
load_dotenv()

# Payment Service Database Configuration
PAYMENT_DATABASE_URL = os.getenv("PAYMENT_DATABASE_URL", "sqlite:///./payments.db")
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

stripe.api_key = STRIPE_API_KEY

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up the database engine and session for Payment Service
payment_engine = create_engine(PAYMENT_DATABASE_URL)

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int
    stripe_payment_intent_id: str
    amount: float
    currency: str = "usd"
    status: str

# Configure Kafka connection settings based on environment
security_protocol = "PLAINTEXT" if ENVIRONMENT == "development" else "SASL_SSL"
sasl_mechanism = "PLAIN" if ENVIRONMENT != "development" else None
sasl_plain_username = os.getenv("KAFKA_SASL_USERNAME") if ENVIRONMENT != "development" else None
sasl_plain_password = os.getenv("KAFKA_SASL_PASSWORD") if ENVIRONMENT != "development" else None
ssl_context = None if ENVIRONMENT == "development" else ssl.create_default_context()

@app.on_event("startup")
async def on_startup():
    SQLModel.metadata.create_all(payment_engine)
    loop = asyncio.get_event_loop()

    app.state.consumer = AIOKafkaConsumer(
        'order_topic',
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
        security_protocol=security_protocol,
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=sasl_plain_username,
        sasl_plain_password=sasl_plain_password,
        ssl_context=ssl_context,
        group_id='payment-service-group'
    )
    app.state.producer = AIOKafkaProducer(
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
        security_protocol=security_protocol,
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=sasl_plain_username,
        sasl_plain_password=sasl_plain_password,
        ssl_context=ssl_context
    )

    logger.info("Starting Kafka consumer and producer...")
    retries = 5
    for _ in range(retries):    
        try:
            await app.state.consumer.start()
            await app.state.producer.start()
            logger.info("Kafka consumer and producer started successfully")
            asyncio.create_task(consume_order_events())
            break
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer/producer: {e}")
            raise HTTPException(status_code=500, detail="Failed to start Kafka consumer/producer")

@app.on_event("shutdown")
async def on_shutdown():
    if hasattr(app.state, 'producer'):
        logger.info("Stopping Kafka producer...")
        await app.state.producer.stop()
    if hasattr(app.state, 'consumer'):
        logger.info("Stopping Kafka consumer...")
        await app.state.consumer.stop()
    logger.info("Kafka consumer and producer stopped successfully")

async def consume_order_events():
    try:
        async for message in app.state.consumer:
            event_data = json.loads(message.value)
            logger.info(f"Received order event: {event_data}")

            if event_data['event'] == 'order_created':
                await process_payment(event_data['order'])

    except Exception as e:
        logger.error(f"Failed to consume order event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to consume order event: {str(e)}")

async def process_payment(order):
    try:
        # Create a Stripe PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(order['total_price'] * 100),  # Stripe expects the amount in cents
            currency='usd',
            payment_method_types=['card'],
            description=f"Payment for order {order['id']}",
            metadata={'order_id': order['id']}
        )

        # Save the payment record
        with Session(payment_engine) as session:
            payment = Payment(
                order_id=order['id'],
                stripe_payment_intent_id=intent['id'],
                amount=order['total_price'],
                currency='usd',
                status=intent['status']
            )
            session.add(payment)
            session.commit()

        if intent['status'] == 'succeeded':
            await emit_payment_event(order['id'], 'payment_succeeded', intent['id'])
        else:
            await emit_payment_event(order['id'], 'payment_failed', intent['id'])

    except stripe.error.StripeError as e:
        logger.error(f"Stripe payment failed: {e}")
        await emit_payment_event(order['id'], 'payment_failed')

async def emit_payment_event(order_id: int, status: str, stripe_payment_intent_id: str = None):
    event_data = {
        "event": status,
        "order_id": order_id,
        "stripe_payment_intent_id": stripe_payment_intent_id
    }
    logger.info(f"Producing payment event to Kafka: {event_data}")
    try:
        await app.state.producer.send_and_wait("payment_topic", json.dumps(event_data).encode('utf-8'))
        logger.info(f"Payment event {status} produced successfully")
    except Exception as e:
        logger.error(f"Failed to produce payment event to Kafka: {e}")
