import os
import time
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from datetime import datetime

# Track time of last saved message
last_saved_time = 0  # seconds since epoch
MSG_INTERVAL_SECONDS = 5  # Minimum interval between saves

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Successfully connected to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        client.subscribe(MQTT_TOPIC_TO_SUBSCRIBE)
        print(f"Subscribed to topic: '{MQTT_TOPIC_TO_SUBSCRIBE}'")
    else:
        print(f"Failed to connect, return code {rc}")
        print("Please check your internet connection or broker address.")

def on_message(client, userdata, msg):
    """
    Save raw payload_str to a uniquely named file every 5 seconds.
    Record the filename and timestamp in log.csv.
    """
    global last_saved_time
    try:
        current_time = time.time()
        if current_time - last_saved_time < MSG_INTERVAL_SECONDS:
            return  # Skip this message if it's too soon

        payload_str = msg.payload.decode('utf-8')

        # Create timestamp-based filename
        timestamp_obj = datetime.fromtimestamp(current_time)
        timestamp_str = timestamp_obj.strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{timestamp_str}.json"

        # Save the payload string to a file
        folder_path = userdata
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(payload_str)

        # Append an entry to the log file
        log_path = os.path.join(folder_path, "log.csv")
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"{timestamp_obj.isoformat(timespec='milliseconds')},{filename}\n")

        last_saved_time = current_time  # Update last saved time
        print(f"[{timestamp_obj.strftime('%H:%M:%S')}] Saved message to: {filename}")

    except Exception as e:
        print(f"Error saving message: {e}")

def create_unique_folder():
    BASE_PATH = os.getenv("OUT_FOLDER_BASE")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_folder_name = f"MyUniqueFolder_{timestamp_str}"
    new_folder_path = os.path.join(BASE_PATH, unique_folder_name)
    os.makedirs(new_folder_path)
    print(f"New unique folder created at: {new_folder_path}")
    return new_folder_path

def create_mqtt_client():
    global MQTT_TOPIC_TO_SUBSCRIBE, MQTT_BROKER_HOST, MQTT_BROKER_PORT
    MQTT_TOPIC_TO_SUBSCRIBE = os.getenv("MQTT_TOPIC_TO_SUBSCRIBE")
    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))

    print("Starting MQTT Raw Message Archiver...")
    print(f"Listening on topic: '{MQTT_TOPIC_TO_SUBSCRIBE}'")
    print("Press Ctrl+C to stop.")
    print("-" * 40)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        exit(1)

    return client

def run_loop(client):
    client.loop_start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping MQTT Archiver (KeyboardInterrupt)...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT broker.")
        print("MQTT Archiver stopped.")

if __name__ == "__main__":
    load_dotenv()
    new_folder_path = create_unique_folder()
    client = create_mqtt_client()
    client.user_data_set(new_folder_path)
    run_loop(client)