import os
import time
import json
import yaml
import logging.config
from datetime import datetime
import httpx
import connexion

# Load logging configuration from YAML
with open("./config/test/anomaly_detector/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

# Load application configuration from app_config.yml
with open("./config/test/anomaly_detector/app_config.yml", "r") as f:
    APP_CONFIG = yaml.safe_load(f.read())


# Configurable service endpoints and datastore file path
PROCESSING_URL = APP_CONFIG['processing']['url']
ANALYZER_URL = APP_CONFIG['analyzer']['url']
STORAGE_URL = APP_CONFIG['storage']['url']
JSON_DATASTORE = APP_CONFIG['datastore']['filename']

# Create a logger instance
logger = logging.getLogger('basicLogger')

def update_anomalies():
    """
    PUT /update
    reads from the Kafka queue (from the beginning, every time)
    finds events with anomalies
    updates the JSON datastore from scratch with anomaly data (= the JSON file is overwritten every time
    the endpoint is accessed)
    The endpoint returns an HTTP response that contains the number of anomalies detected in the queue. See
    the OpenAPI YAML specification for more details.
    My anomaly service will detect all flight schedule flight duration that are too low (for example, below 15). It will also detect passenger check luggage weights that are too high (for example, about 200).
    Logging
    At minimum, the following shall be logged:
    on startup of the service: log the threshold values for anomalies (
    When accessing the "update" endpoint (
    INFO)
    DEBUG)
    When an anomaly is detected and added to the JSON file, including the value detected and threshold
    exceeded (
    DEBUG)
    When the "update" endpoint has completed the anomaly detection. Make sure you include how long
    the service took to retrieve the anomalies (
    INFO).
    When a 
    GET /anomalies request is received and the response returned (
    Integration
    DEBUG)
    """
    start_time = time.time()
    logger.info("Starting anomaly update process")
    try:
        # Retrieve events from the analyzer service (queue)
        analyzer_events_resp = httpx.get(f"{ANALYZER_URL}/events")
        if analyzer_events_resp.status_code != 200:
            return {"message": "Failed to retrieve analyzer events"}, 500
        analyzer_events = analyzer_events_resp.json()
        
        anomalies = []
        for event in analyzer_events:
            if event.get("type") == "flight_schedule" and event.get("flight_duration") < 15:
                logger.debug(f"Anomaly detected: {event}")
                anomalies.append(event)
            elif event.get("type") == "passenger_checkin" and event.get("luggage_weight") > 200:
                logger.debug(f"Anomaly detected: {event}")  
                anomalies.append(event)
        
        # Write the anomalies to the JSON datastore
        with open(JSON_DATASTORE, "w") as f:
            json.dump(anomalies, f, indent=4)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Anomaly detection completed | processing_time_ms={processing_time_ms} | anomalies_detected={len(anomalies)}")
        return {"processing_time_ms": processing_time_ms, "anomalies_detected": len(anomalies)}, 200
    except Exception as e:
        logger.error(f"Error during anomaly update: {str(e)}")
        return {"message": str(e)}, 500


def get_anomalies():
    """
    The GET /anomalies endpoint defined in the OpenAPI spec returns a list of anomalies. The endpoint allows to filter by event type (i.e. show anomalies for "EVENT1" only, or "EVENT2" only) using a parameter in the query string (URL).
    If the event type provided is invalid, return 400.
    If the event type is not provided, show all anomalies.
    The event type is optional in the OpenAPI spec.
    Make sure you use a default value for the argument (use the following signature for your endpoint function: def get_anomalies(event_type=None)).
    If the event type is not provided in the URL, the function will use the default value provided in the signature.
    If there are no anomalies to return, return an empty response with code 204.
    If there are issues with the anomaly datastore (missing or invalid data), return 404.
    At minimum, the following shall be logged: on startup of the service: log the threshold values for anomalies (
    When accessing the "update" endpoint (INFO) DEBUG)
    When an anomaly is detected and added to the JSON file, including the value detected and threshold exceeded (DEBUG)
    When the "update" endpoint has completed the anomaly detection. Make sure you include how long
    the service took to retrieve the anomalies (
    INFO).
    When a GET /anomalies request is received and the response returned (DEBUG)    
    Make it easier to understand
    """
    # analyzer_events_resp = httpx.get(f"{ANALYZER_URL}/events")
    # if analyzer_events_resp.status_code != 200:
    #     return {"message": "Failed to retrieve analyzer events"}, 500
    # analyzer_events = analyzer_events_resp.json()

    # for event in analyzer_events:
    #     if event.get("type") == "flight_schedule" and event.get("flight_duration") < 15:
    #         logger.debug(f"Anomaly detected: {event}")
    #     elif event.get("type") == "passenger_checkin" and event.get("luggage_weight") > 200:
    #         logger.debug(f"Anomaly detected: {event}")



    logger.debug("Received GET request for anomalies")
    # Get the event type from the query parameters
    event_type = None
    if event_type not in ["flight_schedule", "passenger_checkin", None]:
        return {"message": "Invalid event type provided."}, 400
    try:
        with open(JSON_DATASTORE, "r") as f:
            anomalies = json.load(f)
        
        # Filter anomalies by event type if provided
        if event_type:
            filtered_anomalies = [anomaly for anomaly in anomalies if anomaly.get("type") == event_type]
            logger.debug(f"Filtered anomalies: {filtered_anomalies}")
        else:
            filtered_anomalies = anomalies
        
        if not filtered_anomalies:
            return {}, 204 
        
        return filtered_anomalies, 200
    except FileNotFoundError:
        return {"message": "Anomaly datastore not found."}, 404
    except json.JSONDecodeError:
        return {"message": "Invalid data in anomaly datastore."}, 404

# Set up the Connexion application using the provided OpenAPI spec
app = connexion.FlaskApp(__name__, specification_dir=".")
app.add_api("anomaly.yaml", base_path="/anomaly_detection", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8130)
