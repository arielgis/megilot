import threading
import queue
import os
import logging
from offline_simulator import simulate_offline_messages
from caltopo_api import send_location_to_caltopo
from dotenv import load_dotenv
from mtqq_listener import start_mqtt_listener

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
load_dotenv()
USE_REALTIME=True
DEFAULT_DELAY = 1.0        # Used if USE_REAL_TIMING is False
TIME_MULTIPLIER = 0.1     # e.g. 0.5 = 2x faster, 2.0 = 2x slower
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_TOPIC_TO_SUBSCRIBE = os.getenv("MQTT_TOPIC_TO_SUBSCRIBE")
CALTOPO_CONNECT_KEY = os.getenv("CALTOPO_CONNECT_KEY")
DRONES_SN_NAME = os.getenv("DRONES_SN_NAME")

sn_to_drone_name = {}
for item in DRONES_SN_NAME.split(","):
    sn, name = item.split(":")
    sn_to_drone_name[sn.strip()] = name.strip()
print(sn_to_drone_name)


def handle_drone_message(message):
    if message["data"]["sn"] in DRONES_SN_NAME:
        drone_name = DRONES_SN_NAME[message["data"]["sn"]]
        host = message["data"].get("host", {})
        longitude = host.get("longitude")
        latitude = host.get("latitude")
        print(drone_name, " Longitude:", longitude, "Latitude:", latitude)
        send_location_to_caltopo(CALTOPO_CONNECT_KEY, drone_name, latitude, longitude)


# --- Message Consumer ---
def print_messages_from_queue(queue):
    while True:
        message = queue.get()
        #print("\n📥 New Message from Queue:")
        if "sn" in message.get("data", {}):
            handle_drone_message(message)
        queue.task_done()

# --- Main Entry Point ---
if __name__ == "__main__":
    q = queue.Queue()

    # Start consumer thread to print messages
    consumer_thread = threading.Thread(target=print_messages_from_queue, args=(q,), daemon=True)
    consumer_thread.start()

    if USE_REALTIME:
        logger.info("Running in REAL-TIME mode (MQTT listener)")
        mqtt_thread = threading.Thread(
            target=start_mqtt_listener,
            args=(q, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_TO_SUBSCRIBE),
            daemon=True
        )
        mqtt_thread.start()
        try:
            while True:
                pass  # Keep main thread alive
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
    else:
        logger.info("Running in OFFLINE mode (reading from folder)")
        simulate_offline_messages(
            folder_path=OFFLINE_FOLDER,
            queue=q,
            use_real_timestamps=USE_REAL_TIMING,
            default_delay=DEFAULT_DELAY,
            time_multiplier=TIME_MULTIPLIER
        )
        logger.info("Simulation complete. Waiting for queue to finish...")
        q.join()
        logger.info("All messages processed. Exiting.")