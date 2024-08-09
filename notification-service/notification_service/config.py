# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

EVENTHUB_NAMESPACE = os.getenv("EVENTHUB_NAMESPACE")
EVENTHUB_NAME = os.getenv("EVENTHUB_NAME")
EVENTHUB_SAS_POLICY = os.getenv("EVENTHUB_SAS_POLICY")
EVENTHUB_SAS_KEY = os.getenv("EVENTHUB_SAS_KEY")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
