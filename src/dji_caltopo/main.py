import secrets
import queue
import os
from datetime import datetime, timedelta
import logging
import sqlite3
import time
import threading
#from offline_simulator import simulate_offline_messages
#from caltopo_api import send_location_to_caltopo
from dotenv import load_dotenv
from mtqq_listener import start_mqtt_listener
#from dji_utils import  extract_drone_info
#from telegram_logger import TelegramMessageManager
from registration_db import init_db, insert_registration
from telegram_command_bot import start_bot, register_callback

#global variables
MQTT_CLIENT = None
ACTIVE_TOKENS_BY_DRONE = {}
MQTT_HOST = None
MQTT_PORT = None
DB_PATH = None

# --- Logging Configuration ---
logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("dji_caltopo")


def subscribe_to_drone(sn):
    topic = f"thing/product/{sn}/osd"
    if MQTT_CLIENT:
        MQTT_CLIENT.subscribe(topic)
        logger.info(f"✅ Subscribed to topic: {topic}")
    else:
        logger.warning("⚠️ MQTT client not initialized — can't subscribe.")


def get_active_registrations(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()

    c.execute("""
        SELECT sn, name, caltopo_token
        FROM registrations
        WHERE (expires_at > ? OR permanent = 1)
    """, (now,))

    results = c.fetchall()
    conn.close()
    return results


def load_active_registrations(db_path, drones_map):
    drones_map.clear()
    records = get_active_registrations(db_path)
    for sn, name, token in records:
        drones_map.setdefault(sn, []).append((token, name))
        subscribe_to_drone(sn)
    logger.info(f"📦 Loaded {len(records)} active drone-token registrations.")

def setup():
    global MQTT_HOST, MQTT_PORT, MQTT_CLIENT, DB_PATH
    # --- Config & DB ---
    load_dotenv()
    MQTT_HOST = os.getenv("MQTT_BROKER_HOST")
    MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT"))
    DB_PATH = os.getenv("REGISTRATION_DB_PATH")
    init_db(DB_PATH)
    
    # --- MQTT ---
    q = queue.Queue()
    MQTT_CLIENT = start_mqtt_listener(q, MQTT_HOST, MQTT_PORT, [])
    load_active_registrations(DB_PATH, ACTIVE_TOKENS_BY_DRONE)



def handle_register(sn, name, token, email):
    # Check if already registered
    for existing_token, existing_name in ACTIVE_TOKENS_BY_DRONE.get(sn, []):
        if existing_token == token:
            return False, "This drone is already registered to that CalTopo token."

    # Check for duplicate name within the same token
    for entries in ACTIVE_TOKENS_BY_DRONE.values():
        for t, n in entries:
            if t == token and n == name:
                return False, "This name is already used in that CalTopo token."

    # Generate removal code and expiry
    removal_code = secrets.token_hex(3)  # short 6-char hex code
    expires_at = datetime.utcnow() + timedelta(days=7)

    # Try inserting to DB
    success, error = insert_registration(DB_PATH, sn, name, token, email, expires_at, removal_code)
    if not success:
        return False, error

    # Update internal map and subscribe
    ACTIVE_TOKENS_BY_DRONE.setdefault(sn, []).append((token, name))
    subscribe_to_drone(sn)

    # Optionally: log or email confirmation with removal code
    logger.info(f"✅ Registered: SN={sn}, token={token}, name={name}, expires={expires_at.isoformat()}")
    return True, None





#CALTOPO_CONNECT_KEY = os.getenv("CALTOPO_CONNECT_KEY")
#TELEGRAM_TOKEN= os.getenv("TELEGRAM_TOKEN")
#TELEGRAM_CHAT_ID= os.getenv("TELEGRAM_CHAT_ID")

#MQTT_TOPIC_TO_SUBSCRIBE = [f"thing/product/{sn.strip()}/osd" for sn in DRONES_SN_LIST]

#telegram = TelegramMessageManager(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)


# --- Dynamic MQTT topic control ---
"""

def subscribe_to_drone(sn):
    topic = f"thing/product/{sn}/osd"
    mqtt_client.subscribe(topic)
    logger.info(f"✅ Subscribed to topic: {topic}")

def unsubscribe_from_drone(sn):
    topic = f"thing/product/{sn}/osd"
    mqtt_client.unsubscribe(topic)
    logger.info(f"🛑 Unsubscribed from topic: {topic}")

def handle_register(sn, name, token):
    logger.info(f"📥 Register request from Telegram: SN={sn}, Name={name}, Token={token}")
    subscribe_to_drone(sn)
    # TODO: save to DB later


def handle_drone_message(message, sn_to_drone_name):
    try:
        result = extract_drone_info(message, sn_to_drone_name, telegram)
        if result is None:
            telegram.send_mqtt_queued("Invalid drone message format or missing data.")            
            return

        drone_name, longitude, latitude = result
        send_location_to_caltopo(CALTOPO_CONNECT_KEY, drone_name, latitude, longitude)
        telegram.send_validated_coord(drone_name, latitude, longitude)
        logger.info(f"{drone_name} → Longitude: {longitude}, Latitude: {latitude}")

    except Exception as e:
        logger.error(f"❌ Error in message processing: {e}")

# --- Message Consumer ---
def print_messages_from_queue(queue):
    while True:
        message = queue.get()
        try:
            handle_drone_message(message, sn_to_drone_name)
            #sn_to_drone_name[]
            #print(f"✅ Processed message: {message['data']['sn']}")
            #telegram.send_mqtt_queued(")
        except Exception as e:
            logger.error(f"❌ Error in message processing: {e}")
        queue.task_done()

# --- Main Entry Point ---
if __name__ == "__main__":
    q = queue.Queue()

    # Start consumer thread
    consumer_thread = threading.Thread(target=print_messages_from_queue, args=(q,), daemon=True)
    consumer_thread.start()

    
    logger.info("Running MQTT listener")
    mqtt_client = start_mqtt_listener(q, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_TO_SUBSCRIBE)

    register_callback = handle_register
    threading.Thread(target=start_bot, daemon=True).start()
    
    

    try:
        while True:
            time.sleep(10)   # Keep main thread alive
            telegram.send_heartbeat()
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
        
"""
if __name__ == "__main__":
   
    # 1. Run setup to load env, DB, MQTT, and drone map
    setup()

    # 2. Link Telegram bot to your register handler
    register_callback = handle_register

    # 3. Start Telegram bot in background
    threading.Thread(target=start_bot, daemon=True).start()

    # 4. Keep the main thread alive (e.g. for heartbeat or future tasks)
    while True:
        time.sleep(10)