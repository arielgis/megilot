import queue
import os
import logging
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import google_spreadsheet_access as gsa
import threading
from dji_utils import extract_drone_info
from caltopo_api import send_location_to_caltopo
from telegram_logger import TelegramMessageManager
from dotenv import load_dotenv
from mtqq_listener import start_mqtt_listener
from send_mail import send_email

# TODO: Add expired and valid columns, pin code, and an option to remove the drone from the list.



# Global state
WORKSHEET_NAME = 'Form Responses 1'
MQTT_CLIENT = None
ACCESS_URL_BY_DRONE = {}
MQTT_HOST = None
KEY_FILE = None
SPREADSHEET_ID = None
q = None
telegram  = None
last_row_count = 0
seen_registrations = set()
initial_load_done = False
PWD = None
FROM_MAIL = "dji.caltopo.sync@gmail.com"
MIN_INTERVAL_PER_TUPLE = 5.0  # seconds
last_sent_per_tuple = {}      # key: (sn, url_access) -> last send time (epoch seconds)
WORKER_POOL = None



# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")

def _extract_flighthub_timestamp_seconds(message, fallback_time: float) -> float:
    """
    Convert FlightHub timestamp (ms since epoch) to seconds.
    If missing or invalid, fall back to local receive time.
    """
    try:
        return message["timestamp"] / 1000.0
    except Exception:
        return fallback_time



def send_random_locations_to_all_drones():
    import random
    k_list = ACCESS_URL_BY_DRONE.keys()
    for k in k_list:
        latitude = round(31.8 + random.uniform(-0.5, 0.5),5)
        longitude = round(35.3 + random.uniform(-0.5, 0.5),5)
        for (url, name) in ACCESS_URL_BY_DRONE[k]:
            print(f"Sending random location to {name} at {url}")
            send_location_to_caltopo(url, name, latitude, longitude)

        
        

# --- MQTT Drone Subscription ---
def subscribe_to_drone(sn):
    topic = f"thing/product/{sn}/osd"
    if MQTT_CLIENT:
        MQTT_CLIENT.subscribe(topic)
        logger.info(f"✅ Subscribed to topic: {topic}")
    else:
        logger.warning("⚠️ MQTT client not initialized — can't subscribe.")


def init_global_variables():    
    global MQTT_HOST, MQTT_PORT, MQTT_CLIENT, DB_PATH, KEY_FILE, SPREADSHEET_ID
    global q, telegram, PWD, WORKER_POOL

    load_dotenv()
    KEY_FILE = os.getenv("SERVICE_ACCOUNT_KEY_FILE")
    SPREADSHEET_ID = os.getenv("SPREAD_SHEET_ID")
    MQTT_HOST = os.getenv("MQTT_BROKER_HOST")
    MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT"))
    q = queue.Queue()
    MQTT_CLIENT = start_mqtt_listener(q, MQTT_HOST, MQTT_PORT, [])
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_LOGGER_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    telegram = TelegramMessageManager(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    PWD = os.getenv("SMTP_PSWD")
    WORKER_POOL = ThreadPoolExecutor(max_workers=15)



def return_data_if_changed():
    global last_row_count
    worksheet = gsa.get_worksheet_data(KEY_FILE, SPREADSHEET_ID, WORKSHEET_NAME)
    registrations = gsa.worksheet_to_dataframe(worksheet)
    duplicated_rows = registrations.duplicated(['Drone Serial Number', 'CalTopo Access URL'])
    if duplicated_rows.any():
        dup_sn = registrations[duplicated_rows].iloc[0]['Drone Serial Number']
        logger.warning(f"⚠️ Duplicate registrations of {dup_sn} found in the spreadsheet. Please check the data.")
        registrations = registrations.drop_duplicates(['Drone Serial Number', 'CalTopo Access URL'], keep='last')
    #print(registrations.duplicated(['Drone Serial Number', 'CalTopo Access URL']).sum())
   
    current_row_count = len(registrations)
    assert current_row_count >= last_row_count, "Row count decreased, which is unexpected."
    if current_row_count == last_row_count:
        return None  # No new rows
    else:
        last_row_count = current_row_count
        return registrations

    
def handle_single_registration(sn, name, url_access, email, initial_load, new_access_map):

        registration_key = (sn, url_access)

        # Save access mapping
        assert isinstance(url_access, str), f"url_access is not a string: {url_access}"
        assert isinstance(name, str), f"name is not a string: {name}"
        new_access_map.setdefault(sn, []).append((url_access, name))

        # Handle new registration
        if registration_key not in seen_registrations:
            seen_registrations.add(registration_key)
            if not initial_load:
                logger.info(f"🆕 New registration detected: {sn} → {url_access}")
                telegram.send_registration(sn, url_access)
                subject="New Drone Registration"
                body_text=f"Your drone {sn} has been registered to token {url_access} successfully."
                send_email(email, subject, body_text, FROM_MAIL, PWD)
                # Here you'll add:
                # - generate_pin_for_sn(sn, url_access)
                
                # - send_registration_email(...)
    


def handle_registrations_from_spreadsheet(initial_load=False):
    global ACCESS_URL_BY_DRONE, seen_registrations
    registrations = return_data_if_changed()
    if registrations is None:
        return False

   
    new_access_map = {}
    for _, row in registrations.iterrows():
        handle_single_registration(row['Drone Serial Number'], row['Display name'], 
                                   row['CalTopo Access URL'], row["Email Address"], 
                                   initial_load, new_access_map)
    existing_sns = set(ACCESS_URL_BY_DRONE.keys())
    new_sns = set(new_access_map.keys())
    new_drones = new_sns - existing_sns  # SNs that are in new map but not already subscribed
    for sn in new_drones:
        subscribe_to_drone(sn)
    ACCESS_URL_BY_DRONE.clear()
    ACCESS_URL_BY_DRONE.update(new_access_map)

    return True

def _send_to_caltopo_worker(sn, name, url_access, latitude, longitude,
                            flighthub_ts, mqtt_received):
    """
    Runs in a worker thread:
    - calls CalTopo
    - measures delays
    - logs delay breakdown and warnings
    """
    try:
        worker_start = time.time()
        req_time = send_location_to_caltopo(url_access, name, latitude, longitude)
        worker_end = time.time()

        # If send_location_to_caltopo already measured HTTP time and returned it:
        if req_time is not None:
            http_delay = req_time
        else:
            http_delay = max(0.0, worker_end - worker_start)

        upstream_delay = max(0.0, mqtt_received - flighthub_ts)
        internal_delay = max(0.0, worker_start - mqtt_received)
        total_delay = max(0.0, worker_end - flighthub_ts)

        logger.info(
            f"[DELAY] {name}: upstream={upstream_delay:.3f}s, "
            f"internal={internal_delay:.3f}s, http={http_delay:.3f}s, "
            f"total={total_delay:.3f}s, SN={sn}, url_suffix=...{url_access[-4:]}"
        )

        if total_delay > 30.0:
            if upstream_delay > 25.0:
                cause = "UPSTREAM (DJI / FlightHub / MQTT)"
            elif internal_delay > 3.0:
                cause = "INTERNAL QUEUE / PROCESSING"
            elif http_delay > 3.0:
                cause = "CALTOPO HTTP / NETWORK"
            else:
                cause = "MIXED / UNKNOWN"

            logger.warning(
                f"⚠️ DELAY WARNING for {name}: total={total_delay:.2f}s "
                f"(upstream={upstream_delay:.2f}s, internal={internal_delay:.2f}s, "
                f"http={http_delay:.2f}s). Root cause (heuristic): {cause}."
            )

    except Exception as e:
        logger.error(
            f"Error in _send_to_caltopo_worker for {name} (SN={sn}): {e}",
            exc_info=True
        )


def handle_drone_message(message):
    """
    Process a single DJI MQTT message:
    - Extract drone info
    - Enforce 1 update / 5s per (drone, map) tuple
    - Submit CalTopo sends to worker pool (non-blocking)
    """
    try:
        # 1) Local receive time from MQTT (set in mtqq_listener.py)
        mqtt_received = message.get("_mqtt_received_time", time.time())

        # 2) FlightHub timestamp (ms → seconds) from top-level 'timestamp'
        flighthub_ts = _extract_flighthub_timestamp_seconds(
            message, fallback_time=mqtt_received
        )

        # 3) Extract drone mappings & coordinates (list of (url_access, name))
        result = extract_drone_info(message, ACCESS_URL_BY_DRONE, telegram)
        if result is None:
            return

        drone_mappings, longitude, latitude = result

        # 3a) Get SN from message for per-drone rate limiting
        sn = None
        data = message.get("data")
        if isinstance(data, dict):
            sn = data.get("sn")
        if sn is None:
            logger.warning(
                "No 'sn' in message['data']; rate limiting will be based on URL only."
            )

        sent_count = 0

        for url_access, name in drone_mappings:
            # Build key for rate limiting: (SN, URL) if SN known, otherwise ("NO_SN", URL)
            key = (sn, url_access) if sn is not None else ("NO_SN", url_access)

            now = time.time()
            last_time = last_sent_per_tuple.get(key)

            # --- Rate limit: max 1 update / MIN_INTERVAL_PER_TUPLE seconds per tuple ---
            if last_time is not None and (now - last_time) < MIN_INTERVAL_PER_TUPLE:
                logger.info(
                    f"[SKIP] Rate limit: {name} (SN={sn}) url_suffix=...{url_access[-4:]} "
                    f"last sent {now - last_time:.2f}s ago < {MIN_INTERVAL_PER_TUPLE:.1f}s"
                )
                continue

            # Update last sent time for this tuple
            last_sent_per_tuple[key] = now
            sent_count += 1

            # --- Submit to worker pool instead of sending directly ---
            if WORKER_POOL is not None:
                WORKER_POOL.submit(
                    _send_to_caltopo_worker,
                    sn,
                    name,
                    url_access,
                    latitude,
                    longitude,
                    flighthub_ts,
                    mqtt_received,
                )
            else:
                logger.error("WORKER_POOL is not initialized; cannot send to CalTopo.")

        # Small summary log per MQTT message
        primary_name = drone_mappings[0][1] if drone_mappings else "UNKNOWN"
        logger.info(
            f"[DISPATCH] {primary_name}: sent_tasks={sent_count}, "
            f"tuples={len(drone_mappings)}"
        )

    except Exception as e:
        logger.error(f"Error in handle_drone_message: {e}", exc_info=True)


def message_consumer(q):
    while True:
        message = q.get()
        handle_drone_message(message)
        q.task_done()


def poll_spreadsheet_loop():
    while True:
        try:
            handle_registrations_from_spreadsheet(False)
        except Exception as e:
            logger.error(f"⚠️ Error during spreadsheet polling: {e}")
        time.sleep(60)



# --- Main Entry Point ---
if __name__ == "__main__":
    #import telegram_command_bot
    init_global_variables()
    handle_registrations_from_spreadsheet(True)

    # Start message consumer thread
    consumer_thread = threading.Thread(target=message_consumer, args=(q,), daemon=True)
    consumer_thread.start()

    # Start spreadsheet polling thread
    polling_thread = threading.Thread(target=poll_spreadsheet_loop, daemon=True)
    polling_thread.start()

    # Send startup ping
    telegram.send_startup()

    #send_random_locations_to_all_drones()

    # Heartbeat loop    
    try:
        while True:
            time.sleep(60)
            telegram.send_heartbeat()
            
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user.")
