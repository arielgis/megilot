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
USE_REALTIME = True
DEFAULT_DELAY = 1.0        # Used if USE_REAL_TIMING is False
TIME_MULTIPLIER = 0.1      # e.g. 0.5 = 2x faster, 2.0 = 2x slower
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
CALTOPO_CONNECT_KEY = os.getenv("CALTOPO_CONNECT_KEY")

DRONES_SN_LIST = os.getenv("DRONES_SN_LIST", "").split(",")
DRONES_NAMES_LIST = os.getenv("DRONES_NAMES_LIST", "").split(",")
assert len(DRONES_SN_LIST) == len(DRONES_NAMES_LIST), "Drones SN and Names lists must have the same length."
assert len(DRONES_SN_LIST) > 0, "Drones SN list cannot be empty."

MQTT_TOPIC_TO_SUBSCRIBE = [f"thing/product/{sn.strip()}/osd" for sn in DRONES_SN_LIST]

sn_to_drone_name = {}
for i in range(len(DRONES_SN_LIST)):
    sn = DRONES_SN_LIST[i].strip()
    name = DRONES_NAMES_LIST[i].strip()
    assert sn not in sn_to_drone_name, f"Duplicate SN found: {sn}"
    assert name, "Drone name cannot be empty."
    sn_to_drone_name[sn] = name

print(sn_to_drone_name)

# --- Utilities ---
def extract_sn(message):
    return message.get("sn") or message.get("data", {}).get("sn")

# --- Drone Message Handler ---
def handle_drone_message(message):
    sn = extract_sn(message)
    if not sn or sn not in sn_to_drone_name:
        logger.warning(f"⚠️ Skipped: missing or unknown SN: {sn}")
        return

    drone_name = sn_to_drone_name[sn]
    host_data = message.get("data", {})
    latitude = host_data.get("latitude")
    longitude = host_data.get("longitude")
    logger.info(f"{drone_name} → Longitude: {longitude}, Latitude: {latitude}")
    send_location_to_caltopo(CALTOPO_CONNECT_KEY, drone_name, latitude, longitude)

# --- Message Consumer ---
def print_messages_from_queue(queue):
    while True:
        message = queue.get()
        try:
            handle_drone_message(message)
        except Exception as e:
            logger.error(f"❌ Error in message processing: {e}")
        queue.task_done()

# --- Main Entry Point ---
if __name__ == "__main__":
    q = queue.Queue()

    # Start consumer thread
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