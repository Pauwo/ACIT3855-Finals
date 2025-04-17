import os
import time
import json
import yaml
import logging.config
from datetime import datetime
import httpx
import connexion

# Load logging configuration from YAML
with open("./config/test/consistency_check/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Load application configuration from app_config.yml
with open("./config/test/consistency_check/app_conf.yml", "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())


# Configurable service endpoints and datastore file path
PROCESSING_URL = APP_CONFIG['processing']['url']
ANALYZER_URL = APP_CONFIG['analyzer']['url']
STORAGE_URL = APP_CONFIG['storage']['url']
JSON_DATASTORE = APP_CONFIG['datastore']['filename']

# Create a logger instance
logger = logging.getLogger('basicLogger')

def to_int(value):
    """Attempt to convert a value to an integer, returning 0 if conversion fails."""
    try:
        return int(value)
    except Exception:
        return 0

def run_consistency_checks():
    """
    POST /update
    Runs the consistency checks by calling processing, analyzer, and storage endpoints,
    compares events based on trace_id, and writes the result to the JSON datastore.
    """
    start_time = time.time()
    logger.info("Starting consistency check update process")
    try:
        # Retrieve stats from the processing service
        processing_resp = httpx.get(f"{PROCESSING_URL}/stats")
        if processing_resp.status_code != 200:
            return {"message": "Failed to retrieve processing stats"}, 500
        processing_stats = processing_resp.json()
        
        # Retrieve stats and events from the analyzer service (queue)
        analyzer_stats_resp = httpx.get(f"{ANALYZER_URL}/stats")
        if analyzer_stats_resp.status_code != 200:
            return {"message": "Failed to retrieve analyzer stats"}, 500
        analyzer_stats = analyzer_stats_resp.json()
        
        analyzer_events_resp = httpx.get(f"{ANALYZER_URL}/events")
        if analyzer_events_resp.status_code != 200:
            return {"message": "Failed to retrieve analyzer events"}, 500
        analyzer_events = analyzer_events_resp.json()
        
        # Retrieve counts and events from the storage service (database)
        storage_count_resp = httpx.get(f"{STORAGE_URL}/count")
        if storage_count_resp.status_code != 200:
            return {"message": "Failed to retrieve storage counts"}, 500
        storage_counts = storage_count_resp.json()
        
        storage_events_resp = httpx.get(f"{STORAGE_URL}/events")
        if storage_events_resp.status_code != 200:
            return {"message": "Failed to retrieve storage events"}, 500
        storage_events = storage_events_resp.json()
        
        # Map counts to event1 (flight_schedule) and event2 (passenger_checkin)
        processing_converted = {
            "event1": processing_stats.get("num_flight_schedules", 0),
            "event2": processing_stats.get("num_passenger_checkins", 0)
        }
        analyzer_converted = {
            "event1": analyzer_stats.get("num_flight_schedules", 0),
            "event2": analyzer_stats.get("num_passenger_checkins", 0)
        }
        storage_converted = {
            "event1": storage_counts.get("flight_schedule_count", 0),
            "event2": storage_counts.get("passenger_checkin_count", 0)
        }
        
        # Compare events by trace_id (as strings for uniformity)
        analyzer_trace_ids = {str(event.get("trace_id")) for event in analyzer_events}
        storage_trace_ids = {str(event.get("trace_id")) for event in storage_events}
        
        not_in_db = []
        for event in analyzer_events:
            if str(event.get("trace_id")) not in storage_trace_ids:
                not_in_db.append({
                    "event_id": to_int(event.get("id")),
                    "trace_id": to_int(event.get("trace_id")),
                    "type": event.get("type", "unknown")
                })
        
        not_in_queue = []
        for event in storage_events:
            if str(event.get("trace_id")) not in analyzer_trace_ids:
                not_in_queue.append({
                    "event_id": to_int(event.get("event_id")),
                    "trace_id": to_int(event.get("trace_id")),
                    "type": event.get("type", "unknown")
                })
        
        result = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "counts": {
                "processing": processing_converted,
                "queue": analyzer_converted,
                "db": storage_converted
            },
            "not_in_db": not_in_db,
            "not_in_queue": not_in_queue
        }
        
        # Write the results to the JSON datastore
        with open(JSON_DATASTORE, "w") as f:
            json.dump(result, f, indent=4)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Consistency checks completed | processing_time_ms={processing_time_ms} | not_in_db={len(not_in_db)} | not_in_queue={len(not_in_queue)}")
        return {"processing_time_ms": processing_time_ms}, 200
    except Exception as e:
        logger.error(f"Error during consistency check update: {str(e)}")
        return {"message": str(e)}, 500

def get_checks():
    """
    GET /checks
    Retrieves the latest consistency check results from the JSON datastore.
    """
    try:
        with open(JSON_DATASTORE, "r") as f:
            data = json.load(f)
        return data, 200
    except FileNotFoundError:
        return {"message": "No consistency check results found."}, 404

# Set up the Connexion application using the provided OpenAPI spec
app = connexion.FlaskApp(__name__, specification_dir=".")
app.add_api("consistency_check.yaml", base_path="/consistency_check", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8120)
