import json
import logging
import connexion
from pykafka import KafkaClient
import yaml
import logging.config
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path
from connexion import FlaskApp
import random
from datetime import datetime
import pytz 
import os


app = connexion.FlaskApp(__name__, specification_dir="./")

if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Load logging configuration from YAML
with open("./config/test/analyzer/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Load application configuration from app_config.yml
with open("./config/test/analyzer/app_config.yml", "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())

# Create a logger instance
logger = logging.getLogger('basicLogger')

def get_flight_schedule(index):
    """
    GET /flights/schedule?index=<NUMBER>
    """
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    
    counter = 0
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        # Look for flight_schedule events only
        if data.get("type") == "flight_schedule":
            if counter == index:
                payload = data.get("payload")
                logger.info(f"Returning flight schedule data: {payload}")
                return payload, 200
            counter += 1

    return {"message": f"No flight schedule at index {index}!"}, 404


def get_passenger_checkin(index):
    """
    GET /passenger/checkin?index=<NUMBER>
    """
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    
    counter = 0
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        # Look for passenger_checkin events only
        if data.get("type") == "passenger_checkin":
            if counter == index:
                payload = data.get("payload")
                logger.info(f"Returning passenger check-in data: {payload}")
                return payload, 200
            counter += 1

    return {"message": f"No passenger check-in at index {index}!"}, 404


def get_event_stats():
    """
    GET /stats
    """
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    print(f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    
    count_flight_schedule = 0
    count_passenger_checkin = 0
    
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data.get("type") == "flight_schedule":
            count_flight_schedule += 1
        elif data.get("type") == "passenger_checkin":
            count_passenger_checkin += 1

    now = datetime.now(pytz.utc)
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

    stats = {
        "num_flight_schedules": count_flight_schedule,
        "num_passenger_checkins": count_passenger_checkin,
        "last_updated": formatted_time
    }
    return stats, 200


def get_random_flight_schedule():
    """GET /flights/schedule/random"""
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    
    events = []
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data.get("type") == "flight_schedule":
            events.append(data["payload"])
    
    if not events:
        return {"message": "No flight schedules found!"}, 404
    return random.choice(events), 200

def get_random_passenger_checkin():
    """GET /passenger/checkin/random"""
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    
    events = []
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data.get("type") == "passenger_checkin":
            events.append(data["payload"])
    
    if not events:
        return {"message": "No passenger check-ins found!"}, 404
    return random.choice(events), 200


def get_events():
    """
    GET /events
    """
    client = KafkaClient(hosts=f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}")
    topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True,
        consumer_timeout_ms=1000
    )
    
    events = []
    event_id = 1 

    # for msg in consumer:
    #     message = msg.value.decode("utf-8")
    #     data = json.loads(message)
    #     if data.get("type") == "flight_schedule":
    #         event_id = data.get("payload", {}).get("flight_id")
    #         events.append({
    #             "event_id": event_id,
    #             "trace_id": data.get("trace_id"),
    #             "type": "flight_schedule"
    #         })
    #     elif data.get("type") == "passenger_checkin":
    #         event_id = data.get("payload", {}).get("checkin_id")
    #         events.append({
    #             "event_id": event_id,
    #             "trace_id": data.get("trace_id"),
    #             "type": "passenger_checkin"
    #         })


    # this was the original code
    # for msg in consumer:
    #     message = msg.value.decode("utf-8")
    #     data = json.loads(message)
    #     events.append(data["payload"])

    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        payload = data.get("payload", {})
        
        payload['id'] = event_id
        event_id += 1

        events.append(payload)
    
    return events, 200

# Set up the Connexion application and link the OpenAPI specification
# app = connexion.FlaskApp(__name__, specification_dir="./")
app.add_api("openapi.yaml", base_path="/analyzer", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8110, host="0.0.0.0")
