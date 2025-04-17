import connexion
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from models import FlightSchedule, PassengerCheckin, Base
from datetime import datetime
import yaml
import logging
import logging.config
import json
import time
from threading import Thread
from pykafka import KafkaClient
from pykafka.common import OffsetType
from pykafka.exceptions import KafkaException
import random

# Load logging configuration from log_conf.yml
with open("./config/test/storage/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Create a logger
logger = logging.getLogger('basicLogger')

# Load database configuration from app_conf.yml
with open("./config/test/storage/app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

db_user = app_config['datastore']['user']
db_password = app_config['datastore']['password']
db_hostname = app_config['datastore']['hostname']
db_port = app_config['datastore']['port']
db_name = app_config['datastore']['db']

# Create the database URL
# DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_hostname}:{db_port}/{db_name}"
DATABASE_URL = f"mysql://{db_user}:{db_password}@{db_hostname}:{db_port}/{db_name}"

# Database setup
engine = create_engine(DATABASE_URL, pool_size=100, pool_pre_ping=True, pool_recycle=3600)
Base.metadata.create_all(engine)  # Ensure tables exist


def make_session():
    return sessionmaker(bind=engine)()


class KafkaWrapper:
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic = topic
        self.client = None
        self.consumer = None
        self.connect()

    def connect(self):
        while True:
            logger.debug("Trying to connect to Kafka...")
            if self.make_client():
                if self.make_consumer():
                    break
            time.sleep(random.randint(500, 1500) / 1000)

    def make_client(self):
        if self.client is not None:
            return True
        try:
            self.client = KafkaClient(hosts=self.hostname)
            logger.info("Kafka client created!")
            return True
        except KafkaException as e:
            msg = f"Kafka error when making client: {e}"
            logger.warning(msg)
            self.client = None
            self.consumer = None
            return False

    def make_consumer(self):
        if self.consumer is not None:
            return True
        if self.client is None:
            return False
        try:
            topic = self.client.topics[self.topic]
            self.consumer = topic.get_simple_consumer(
                consumer_group=b'event_group',
                reset_offset_on_start=False,
                auto_offset_reset=OffsetType.LATEST
            )
            return True
        except KafkaException as e:
            msg = f"Make error when making consumer: {e}"
            logger.warning(msg)
            self.client = None
            self.consumer = None
            return False

    def messages(self):
        if self.consumer is None:
            self.connect()
        while True:
            try:
                for msg in self.consumer:
                    yield msg
            except KafkaException as e:
                msg = f"Kafka issue in consumer: {e}"
                logger.warning(msg)
                self.client = None
                self.consumer = None
                self.connect()


def process_messages():
    """Process event messages from Kafka"""
    # Load Kafka config
    kafka_config = app_config['events']
    hostname = f"{kafka_config['hostname']}:{kafka_config['port']}"
    topic_name = kafka_config['topic']
    kafka_wrapper = KafkaWrapper(hostname, topic_name)
    
    # # Initialize Kafka client
    # client = KafkaClient(hosts=hostname)
    # topic = client.topics[str.encode(topic_name)]
    
    # # Create a consume on a consumer group, that only reads new messages
    # # (uncommitted messages) when the service re-starts (i.e., it doesn't
    # # read all the old messages from the history in the message queue).
    # # Configure consumer
    # consumer = topic.get_simple_consumer(
    #     consumer_group=b'event_group',
    #     reset_offset_on_start=False,
    #     auto_offset_reset=OffsetType.LATEST
    # )

    
    for msg in kafka_wrapper.messages():
        try:
            # Decode message
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.info(f"Message: {msg}")
            
            payload = msg["payload"]
            
            # Handle different event types
            if msg["type"] == "flight_schedule":
                # Store flight schedule
                session = make_session()
                try:
                    flight_departure = datetime.fromisoformat(payload["flight_departure"])
                    event = FlightSchedule(
                        flight_id=payload["flight_id"],
                        flight_status=payload["flight_status"],
                        flight_duration=payload["flight_duration"],
                        flight_departure=flight_departure,
                        trace_id=payload["trace_id"]
                    )
                    session.add(event)
                    session.commit()
                    logger.debug(f"Stored flight_schedule: {payload['trace_id']}")
                except Exception as e:
                    session.rollback()
                    logger.error(f"DB error: {str(e)}")
                finally:
                    session.close()
                    
            elif msg["type"] == "passenger_checkin":
                # Store passenger checkin
                session = make_session()
                try:
                    checkin_timestamp = datetime.fromisoformat(payload["checkin_timestamp"])
                    event = PassengerCheckin(
                        checkin_id=payload["checkin_id"],
                        flight_id=payload["flight_id"],
                        luggage_weight=payload["luggage_weight"],
                        checkin_timestamp=checkin_timestamp,
                        trace_id=payload["trace_id"]
                    )
                    session.add(event)
                    session.commit()
                    logger.debug(f"Stored passenger_checkin: {payload['trace_id']}")
                except Exception as e:
                    session.rollback()
                    logger.error(f"DB error: {str(e)}")
                finally:
                    session.close()
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")


def setup_kafka_thread():
    """Start Kafka consumer thread"""
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()



# Decorator for session management
def use_db_session(func):
    def wrapper(*args, **kwargs):
        session = make_session()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    return wrapper
    

# Function to retrieve flight schedules within a time range
def get_flight_schedules(start_timestamp, end_timestamp):
    try:
        session = make_session()

        # Convert timestamps to datetime
        start_time = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")

        # Query database
        stmt = select(FlightSchedule).where(
            FlightSchedule.date_created >= start_time,
            FlightSchedule.date_created < end_time
        )
        results = session.execute(stmt).scalars().all()

        session.close()

        # Convert results to JSON
        data = [r.to_dict() for r in results]

        logger.info(f"Returning {len(data)} flight schedules between {start_timestamp} and {end_timestamp}")
        return data, 200
    except ValueError as e:
        return {"error": f"Invalid timestamp format: {str(e)}"}, 400
    except Exception as e:
        logger.error(f"Error retrieving flight schedules: {str(e)}")
        return {"error": str(e)}, 500
    

# Function to retrieve passenger check-ins within a time range
def get_passenger_checkins(start_timestamp, end_timestamp):
    try:
        session = make_session()

        # Convert timestamps to datetime
        start_time = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")

        # Query database
        stmt = select(PassengerCheckin).where(
            PassengerCheckin.date_created >= start_time,
            PassengerCheckin.date_created < end_time
        )
        results = session.execute(stmt).scalars().all()

        session.close()

        # Convert results to JSON
        data = [r.to_dict() for r in results]

        logger.info(f"Returning {len(data)} passenger check-ins between {start_timestamp} and {end_timestamp}")
        return data, 200
    except ValueError as e:
        return {"error": f"Invalid timestamp format: {str(e)}"}, 400
    except Exception as e:
        logger.error(f"Error retrieving passenger check-ins: {str(e)}")
        return {"error": str(e)}, 500

def get_count():
    """
    GET /count
    Retrieves the count of flight schedules and passenger check-ins in the database.
    """
    try:
        session = make_session()
        flight_schedule_count = session.query(FlightSchedule).count()
        passenger_checkin_count = session.query(PassengerCheckin).count()
        session.close()

        result = {
            "flight_schedule_count": flight_schedule_count,
            "passenger_checkin_count": passenger_checkin_count
        }
        logger.info(f"Returning counts: {result}")
        return result, 200
    except Exception as e:
        logger.error(f"Error retrieving counts: {str(e)}")
        return {"error": str(e)}, 500
    
def get_events():
    """
    GET /events
    Retrieves all events from the database.
    """
    try:
        session = make_session()
        flight_events = session.query(FlightSchedule).all()
        checkin_events = session.query(PassengerCheckin).all()
        session.close()

        events = []
        for flight in flight_events:
            events.append({
                "event_id": str(flight.id),
                "trace_id": flight.trace_id,
                "type": "flight_schedule"
            })
        for checkin in checkin_events:
            events.append({
                "event_id": str(checkin.id),
                "trace_id": checkin.trace_id,
                "type": "passenger_checkin"
            })
        logger.info(f"Returning {len(events)} events from database")
        return events, 200

        # # Convert results to JSON
        # flight_schedule_data = [r.to_dict() for r in flight_schedules //flight_events]
        # passenger_checkin_data = [r.to_dict() for r in passenger_checkins //checkin_events]

        # result = {
        #     "flight_schedules": flight_schedule_data,
        #     "passenger_checkins": passenger_checkin_data
        # }
        # return result, 200

    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        return {"error": str(e)}, 500

# Connexion app setup
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0") 