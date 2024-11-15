from fastapi import FastAPI, HTTPException
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
import asyncio
import json
from dotenv import load_dotenv
import os
import ssl
import logging

# Load environment variables from .env file
load_dotenv()

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Determine the Kafka security protocol
security_protocol = "PLAINTEXT" if ENVIRONMENT == "development" else "SASL_SSL"
sasl_mechanism = "PLAIN" if ENVIRONMENT != "development" else None
sasl_plain_username = KAFKA_SASL_USERNAME if ENVIRONMENT != "development" else None
sasl_plain_password = KAFKA_SASL_PASSWORD if ENVIRONMENT != "development" else None
ssl_context = ssl_context if ENVIRONMENT != "development" else None

async def create_kafka_topic(topic_name: str):
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_SERVER,
        security_protocol=security_protocol,
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=sasl_plain_username,
        sasl_plain_password=sasl_plain_password,
        ssl_context=ssl_context,
    )

    try:
        existing_topics = admin_client.list_topics()
        if topic_name not in existing_topics:
            topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
            admin_client.create_topics([topic])
            logger.info(f"Created Kafka topic: {topic_name}")
        else:
            logger.info(f"Kafka topic {topic_name} already exists")
    except Exception as e:
        logger.error(f"Failed to create Kafka topic {topic_name}: {e}")
    finally:
        admin_client.close()

@app.on_event("startup")
async def on_startup():
    loop = asyncio.get_event_loop()

    # Create Kafka topics if they don't exist
    await create_kafka_topic("user_topic")
    await create_kafka_topic("notification_topic")

    app.state.consumer = AIOKafkaConsumer(
        'user_topic',
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
        security_protocol=security_protocol,
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=sasl_plain_username,
        sasl_plain_password=sasl_plain_password,
        ssl_context=ssl_context,
        group_id='notification-group'
    )
    app.state.producer = AIOKafkaProducer(
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
        security_protocol=security_protocol,
        sasl_mechanism=sasl_mechanism,
        sasl_plain_username=sasl_plain_username,
        sasl_plain_password=sasl_plain_password,
        ssl_context=ssl_context,
    )

    logger.info("Starting Kafka consumer and producer...")
    try:
        await app.state.consumer.start()
        await app.state.producer.start()
        logger.info("Kafka consumer and producer started successfully")
        asyncio.create_task(consume())
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer/producer: {e}")
        raise HTTPException(status_code=500, detail="Failed to start Kafka consumer/producer")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Stopping Kafka consumer and producer...")
    try:
        await app.state.consumer.stop()
        await app.state.producer.stop()
        logger.info("Kafka consumer and producer stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop Kafka consumer/producer: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop Kafka consumer/producer")

async def consume():
    try:
        async for message in app.state.consumer:
            event_data = json.loads(message.value)
            logger.info(f"Received user data: {event_data}")
            new_event_data = {"message": f"Notification for user {event_data['username']} sent."}
            await app.state.producer.send_and_wait("notification_topic", json.dumps(new_event_data).encode('utf-8'))
            logger.info("Notification event produced successfully")
    except Exception as e:
        logger.error(f"Failed to consume/produce Kafka message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to consume/produce Kafka message: {str(e)}")

@app.post("/print")
async def print_message(message: dict):
    try:
        logger.info(f"Received message to print: {message}")
        return {"status": "Message received", "message": message}
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
