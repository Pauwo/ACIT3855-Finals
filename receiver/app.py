import connexion
from connexion import NoContent
import httpx 
import time
import yaml
import logging
import logging.config
import json
import datetime
from pykafka import KafkaClient
from pykafka.exceptions import KafkaException
import random

# Load the configuration file
with open('./config/test/receiver/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Load logging configuration from YAML
with open("./config/test/receiver/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Create a logger instance
logger = logging.getLogger('basicLogger')

kafka_config = app_config['events']
# client = KafkaClient(hosts=f"{kafka_config['hostname']}:{kafka_config['port']}")
# topic = client.topics[str.encode(kafka_config['topic'])]
# producer = topic.get_sync_producer()

class KafkaProducerWrapper:
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic = topic
        self.client = None
        self.producer = None
        self.connect()

    def connect(self):
        while True:
            logger.debug("Trying to connect to Kafka producer...")
            if self.make_client():
                if self.make_producer():
                    break
            time.sleep(random.randint(500, 1500) / 1000)

    def make_client(self):
        if self.client is not None:
            return True
        try:
            self.client = KafkaClient(hosts=self.hostname)
            logger.info("Kafka producer client created!")
            return True
        except KafkaException as e:
            logger.warning(f"Kafka error creating client: {e}")
            self.client = None
            self.producer = None
            return False

    def make_producer(self):
        if self.producer is not None:
            return True
        if self.client is None:
            return False
        try:
            topic = self.client.topics[self.topic]
            self.producer = topic.get_sync_producer()
            return True
        except KafkaException as e:
            logger.warning(f"Kafka error creating producer: {e}")
            self.client = None
            self.producer = None
            return False

    def send(self, message):
        if self.producer is None:
            self.connect()
        while True:
            try:
                self.producer.produce(message.encode('utf-8'))
                break
            except KafkaException as e:
                logger.warning(f"Kafka send error: {e}, reconnecting...")
                self.connect()

# Global producer wrapper instance
producer_wrapper = KafkaProducerWrapper(
    f"{kafka_config['hostname']}:{kafka_config['port']}",
    kafka_config['topic'].encode()
)


# Function for the flight schedule event
def report_flight_schedules(body):
    trace_id = time.time_ns()
    body["trace_id"] = trace_id
    logger.info(f"Received flight schedule event (trace_id: {trace_id})")

    # Create Kafka message
    msg = {
        "type": "flight_schedule",  # Custom event type
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body  # Includes trace_id
    }
    msg_str = json.dumps(msg)
    
    # Send to Kafka
    producer_wrapper.send(msg_str)
    logger.info(f"Produced flight_schedule event (trace_id: {trace_id})")

    return NoContent, 201 

# Function for the passenger check-in event
def record_passenger_checkin(body):
    trace_id = time.time_ns()
    body["trace_id"] = trace_id
    logger.info(f"Received passenger check-in event (trace_id: {trace_id})")

    # Create Kafka message
    msg = {
        "type": "passenger_checkin",  # Custom event type
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body  # Includes trace_id
    }
    msg_str = json.dumps(msg)
    
    # Send to Kafka
    producer_wrapper.send(msg_str)
    logger.info(f"Produced passenger_checkin event (trace_id: {trace_id})")

    return NoContent, 201

# Connexion app setup
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/receiver", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")  # Receiver service runs on port 8080