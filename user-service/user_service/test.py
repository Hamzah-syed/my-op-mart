import os
import ssl
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_kafka_topic(topic_name: str):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    logger.info(f"Connecting to Kafka server: {KAFKA_SERVER}")
    logger.info(f"Using SASL username: {KAFKA_SASL_USERNAME}")
    logger.info(f"Using SASL password: {KAFKA_SASL_PASSWORD}")

    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_SERVER,
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_plain_username=KAFKA_SASL_USERNAME,
        sasl_plain_password=KAFKA_SASL_PASSWORD,
        ssl_context=ssl_context,
    )

    try:
        existing_topics = admin_client.list_topics()
        logger.info(f"Existing topics: {existing_topics}")
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

if __name__ == "__main__":
    create_kafka_topic("user_topic")
