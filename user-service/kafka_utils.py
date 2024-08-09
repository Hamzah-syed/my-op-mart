from kafka import KafkaProducer, KafkaConsumer
import json

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'user_topic',
    bootstrap_servers='kafka:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='user-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

def send_message(topic, message):
    producer.send(topic, message)
    producer.flush()
