from fastapi import FastAPI, HTTPException, Depends, status, Response
from sqlmodel import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
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

# Environment and Kafka configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

async def create_kafka_topic(topic_name: str):
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_SERVER,
        security_protocol="SASL_SSL" if ENVIRONMENT != "development" else "PLAINTEXT",
        sasl_mechanism="PLAIN" if ENVIRONMENT != "development" else None,
        sasl_plain_username=KAFKA_SASL_USERNAME if ENVIRONMENT != "development" else None,
        sasl_plain_password=KAFKA_SASL_PASSWORD if ENVIRONMENT != "development" else None,
        ssl_context=ssl.create_default_context() if ENVIRONMENT != "development" else None,
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

    if ENVIRONMENT != "development":
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
    else:
        app.state.producer = AIOKafkaProducer(
            loop=loop,
            bootstrap_servers=KAFKA_SERVER,
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

@app.post("/login/", response_model=Token)
async def login_user(user: UserLogin, response: Response):
    try:
        with Session(engine) as session:
            db_user = session.query(User).filter(User.email == user.email).first()
            if not db_user or not verify_password(user.password, db_user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Create JWT access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(data={"sub": db_user.email}, expires_delta=access_token_expires)

            # Set the access token in an HTTP-only cookie
            response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, secure=True, samesite="Lax")

            # Produce login event to Kafka
            event_data = {
                "event": "user_login",
                "username": db_user.username,
                "email": db_user.email
            }
            logger.info(f"Producing login event to Kafka: {event_data}")
            try:
                await app.state.producer.send_and_wait("user_topic", json.dumps(event_data).encode('utf-8'))
                logger.info("Login event produced successfully")
            except Exception as e:
                logger.error(f"Failed to produce login event to Kafka: {e}")
                raise HTTPException(status_code=500, detail="Failed to produce login event to Kafka")

            return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Failed to login user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile/")
async def get_profile(user_id: int):
    try:
        with Session(engine) as session:
            db_user = session.query(User).filter(User.id == user_id).first()
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return UserProfile(username=db_user.username, email=db_user.email)
    except Exception as e:
        logger.error(f"Failed to fetch user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/profile/")
async def update_profile(user_id: int, user_update: UserProfile):
    try:
        with Session(engine) as session:
            db_user = session.query(User).filter(User.id == user_id).first()
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")

            db_user.username = user_update.username
            db_user.email = user_update.email
            session.commit()
            session.refresh(db_user)

            # Produce profile update event to Kafka
            event_data = {
                "user_id": db_user.id,
                "username": db_user.username,
                "email": db_user.email
            }
            logger.info(f"Producing profile update event to Kafka: {event_data}")
            try:
                await app.state.producer.send_and_wait("user_topic", json.dumps(event_data).encode('utf-8'))
                logger.info("Event produced successfully")
            except Exception as e:
                logger.error(f"Failed to produce profile update event to Kafka: {e}")
                raise HTTPException(status_code=500, detail="Failed to produce profile update event to Kafka")

            return db_user
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# JWT creation and verification functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + expires_delta if expires_delta else datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
