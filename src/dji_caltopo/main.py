import secrets
import queue
import os
from datetime import datetime, timedelta
import logging
import sqlite3
import time
import threading
from dotenv import load_dotenv

from mtqq_listener import start_mqtt_listener
from registration_db import init_db, insert_registration
from telegram_command_bot import start_bot, register_callback

# Global state
MQTT_CLIENT = None
ACTIVE_TOKENS_BY_DRONE = {}
MQTT_HOST = None
MQTT_PORT = None
DB_PATH = None

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("dji_caltopo")


# --- MQTT Drone Subscription ---
def subscribe_to_drone(sn):
    topic = f"thing/product/{sn}/osd"
    if MQTT_CLIENT:
        MQTT_CLIENT.subscribe(topic)
        logger.info(f"✅ Subscribed to topic: {topic}")
    else:
        logger.warning("⚠️ MQTT client not initialized — can't subscribe.")


# --- Database Operations ---
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


# --- One-time Initialization ---
def setup():
    global MQTT_HOST, MQTT_PORT, MQTT_CLIENT, DB_PATH
    load_dotenv()
    MQTT_HOST = os.getenv("MQTT_BROKER_HOST")
    MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT"))
    DB_PATH = os.getenv("REGISTRATION_DB_PATH")
    init_db(DB_PATH)

    q = queue.Queue()
    MQTT_CLIENT = start_mqtt_listener(q, MQTT_HOST, MQTT_PORT, [])
    load_active_registrations(DB_PATH, ACTIVE_TOKENS_BY_DRONE)


# --- Handle Telegram /register ---
def handle_register(sn, name, token, email):
    for existing_token, existing_name in ACTIVE_TOKENS_BY_DRONE.get(sn, []):
        if existing_token == token:
            return False, "This drone is already registered to that CalTopo token."

    for entries in ACTIVE_TOKENS_BY_DRONE.values():
        for t, n in entries:
            if t == token and n == name:
                return False, "This name is already used in that CalTopo token."

    removal_code = secrets.token_hex(3)
    DAYS_VALID = int(os.getenv("REGISTRATION_VALID_DAYS", "7"))
    print("DAYS_VALID:", DAYS_VALID, type(DAYS_VALID))
    expires_at = 0#datetime.utcnow() + timedelta(days=DAYS_VALID)

    success, error = insert_registration(DB_PATH, sn, name, token, email, expires_at, removal_code)
    if not success:
        return False, error

    ACTIVE_TOKENS_BY_DRONE.setdefault(sn, []).append((token, name))
    subscribe_to_drone(sn)

    logger.info(f"✅ Registered: SN={sn}, token={token}, name={name}, expires={expires_at.isoformat()}")
    return True, f"Drone '{name}' registered successfully."


# --- Main Entry Point ---
if __name__ == "__main__":
    import telegram_command_bot
    setup()
    #register_callback = handle_register
    # Explicitly set the callback in the telegram module
    
    telegram_command_bot.register_callback = handle_register

    threading.Thread(target=start_bot, daemon=True).start()

    while True:
        time.sleep(10)