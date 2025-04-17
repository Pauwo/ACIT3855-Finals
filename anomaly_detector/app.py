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
    """
    logger.debug("Received PUT request for anomaly update")

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
                logger.debug(f"Anomaly detected: {event} as it has a flight duration less than 15 minutes")
                anomalies.append(event)
            elif event.get("type") == "passenger_checkin" and event.get("luggage_weight") > 200:
                logger.debug(f"Anomaly detected: {event} as it exceeds the luggage weight limit of 200")  
                anomalies.append(event)
        
        with open(JSON_DATASTORE, "w") as f:
            json.dump(anomalies, f, indent=4)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Anomaly detection completed | processing_time_ms={processing_time_ms} | anomalies_detected={len(anomalies)}")
        return {"processing_time_ms": processing_time_ms, "anomalies_detected": len(anomalies)}, 200
    except Exception as e:
        logger.error(f"Error during anomaly update: {str(e)}")
        return {"message": str(e)}, 500


def get_anomalies(event_type=None):
    """
    The GET /anomalies endpoint defined in the OpenAPI spec returns a list of anomalies. The endpoint allows to filter by event type (i.e. show anomalies for "EVENT1" only, or "EVENT2" only) using a parameter in the query string (URL).
    """
    logger.debug("Received GET request for anomalies")
    if event_type not in ["flight_schedule", "passenger_checkin", None]:
        return {"message": "Invalid event type provided."}, 400
    try:
        with open(JSON_DATASTORE, "r") as f:
            anomalies = json.load(f)
        
        if event_type:
            filtered_anomalies = [anomaly for anomaly in anomalies if anomaly.get("type") == event_type]
            logger.debug(f"Filtered anomalies: {filtered_anomalies}")
        else:
            filtered_anomalies = anomalies
        
        if not filtered_anomalies:
            return {}, 204  # No content
        
        return filtered_anomalies, 200
    except FileNotFoundError:
        return {"message": "Anomaly datastore not found."}, 404
    

# Set up the Connexion application using the provided OpenAPI spec
app = connexion.FlaskApp(__name__, specification_dir=".")
app.add_api("anomaly.yaml", base_path="/anomaly_detection", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info(f"Threshold values for anomalies: luggage_weight=200, flight_duration=15")
    app.run(host="0.0.0.0", port=8130)
