# app/kafka/consumer.py
import asyncio
import json
import ssl
import logging
from fastapi import FastAPI, HTTPException
from aiokafka import AIOKafkaConsumer
from ..config import KAFKA_BOOTSTRAP_SERVERS, EVENTHUB_SAS_POLICY, EVENTHUB_SAS_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

async def consume():
    consumer = AIOKafkaConsumer(
        'user_topic',
        loop=asyncio.get_event_loop(),
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username=EVENTHUB_SAS_POLICY,
        sasl_plain_password=EVENTHUB_SAS_KEY,
        ssl_context=ssl.create_default_context(),
        group_id='notification-group'
    )
    await consumer.start()
    try:
        async for message in consumer:
            event_data = json.loads(message.value)
            logger.info(f"Received user data: {event_data}")
            await process_message(event_data)
    finally:
        await consumer.stop()

async def process_message(event_data):
    # Logic to process message and call /print endpoint
    async with app.state.http_client.post("http://localhost:8002/print", json=event_data) as response:
        if response.status != 200:
            logger.error(f"Failed to call /print endpoint with data: {event_data}")
        else:
            logger.info(f"Successfully called /print endpoint with data: {event_data}")

@app.on_event("startup")
async def startup_event():
    # Start Kafka consumer in background
    asyncio.create_task(consume())

@app.post("/print")
async def print_message(message: dict):
    try:
        logger.info(f"Received message to print: {message}")
        return {"status": "Message received", "message": message}
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")
