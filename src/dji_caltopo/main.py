import queue
import os
import logging
import time
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



# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("main")


# --- MQTT Drone Subscription ---
def subscribe_to_drone(sn):
    topic = f"thing/product/{sn}/osd"
    if MQTT_CLIENT:
        MQTT_CLIENT.subscribe(topic)
        logger.info(f"✅ Subscribed to topic: {topic}")
    else:
        logger.warning("⚠️ MQTT client not initialized — can't subscribe.")


def init_global_variables():    
    global MQTT_HOST, MQTT_PORT, MQTT_CLIENT, DB_PATH, KEY_FILE, SPREADSHEET_ID, q, telegram, PWD
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

def handle_drone_message(message):
    try:
        result = extract_drone_info(message, ACCESS_URL_BY_DRONE, telegram)
        if result is None:
            telegram.send_mqtt_queued("Invalid drone message format or missing data.")
            return

        drone_mappings, longitude, latitude = result  # Expecting a list of (url, name) tuples
        for url, name in drone_mappings:
            send_location_to_caltopo(url, name, latitude, longitude)

        # Use the display name of the first mapping for the Telegram message (or modify as needed)
        if drone_mappings:
            telegram.send_validated_coord(drone_mappings[0][1], latitude, longitude)

        logger.info(f"{drone_mappings[0][1]} → Longitude: {longitude}, Latitude: {latitude}")

    except Exception as e:
        logger.error(f"❌ Error in message processing: {e}")

    except Exception as e:
        logger.error(f"❌ Error in message processing: {e}")


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

    # Heartbeat loop    
    try:
        while True:
            time.sleep(60)
            telegram.send_heartbeat()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user.")
