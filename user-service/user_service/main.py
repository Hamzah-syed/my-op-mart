from fastapi import FastAPI, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from .model import create_db_and_tables, User, engine
import hashlib
from aiokafka import AIOKafkaProducer
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

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

async def create_kafka_topic(topic_name: str):
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_SERVER,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username=KAFKA_SASL_USERNAME,
        sasl_plain_password=KAFKA_SASL_PASSWORD,
        ssl_context=ssl.create_default_context(),
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
    create_db_and_tables()
    loop = asyncio.get_event_loop()

    # Create Kafka topic if it doesn't exist
    await create_kafka_topic("user_topic")

    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    app.state.producer = AIOKafkaProducer(
        loop=loop,
        bootstrap_servers=KAFKA_SERVER,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username=KAFKA_SASL_USERNAME,
        sasl_plain_password=KAFKA_SASL_PASSWORD,
        ssl_context=ssl_context,
    )
    
    logger.info("Starting Kafka producer...")
    try:
        await app.state.producer.start()
        logger.info("Kafka producer started successfully")
    except Exception as e:
        logger.error(f"Failed to start Kafka producer: {e}")
        raise HTTPException(status_code=500, detail="Failed to start Kafka producer")

@app.on_event("shutdown")
async def on_shutdown():
    if hasattr(app.state, 'producer'):
        logger.info("Stopping Kafka producer...")
        await app.state.producer.stop()
        logger.info("Kafka producer stopped successfully")

@app.post("/users/")
async def create_user(user: UserCreate):
    user_dict = user.dict()
    user_dict['password_hash'] = hash_password(user_dict.pop('password'))
    try:
        with Session(engine) as session:
            db_user = User(**user_dict)
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            # Produce event to Kafka
            event_data = {
                "username": db_user.username,
                "email": db_user.email
            }
            logger.info(f"Producing event to Kafka: {event_data}")
            try:
                await app.state.producer.send_and_wait("user_topic", json.dumps(event_data).encode('utf-8'))
                logger.info("Event produced successfully")
            except Exception as e:
                logger.error(f"Failed to produce event to Kafka: {e}")
                raise HTTPException(status_code=500, detail="Failed to produce event to Kafka")
        return db_user
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def hash_password(password: str) -> str:
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return hashed_password
