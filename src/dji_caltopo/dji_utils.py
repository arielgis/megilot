import logging
import requests 
BUFFER_KM = 20  # max distance from Israel borders to consider valid GPS coordinates

def send_telegram_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("✅ Message sent successfully.")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

      


def validate_coordinates(lat, lon):
    """
    Validates GPS coordinates against Israel's boundaries with an optional buffer (in km).
    Logs specific warnings for no GPS, illegal coordinates, and out-of-bounds positions.
    """
    if lat == 0 and lon == 0:
        logging.warning("📡 No GPS fix – coordinates are (0, 0)")
        return False

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        logging.warning(f"❌ GPS Spoofing Alert: Invalid coordinates detected — lat={lat}, lon={lon}")
        return False

    # Convert buffer from km to degrees
    lat_buffer_deg = BUFFER_KM / 111.0  # 1° latitude ≈ 111 km
    lon_buffer_deg = BUFFER_KM / 95.0   # 1° longitude ≈ 95 km in Israel

    # Israel bounds
    israel_lat_min = 29.5 - lat_buffer_deg
    israel_lat_max = 33.3 + lat_buffer_deg
    israel_lon_min = 34.3 - lon_buffer_deg
    israel_lon_max = 35.9 + lon_buffer_deg

    if not (israel_lat_min <= lat <= israel_lat_max and israel_lon_min <= lon <= israel_lon_max):
        logging.warning(f"⚠️ Coordinates out of Israel + {BUFFER_KM} km buffer – possible spoofing: lat={lat}, lon={lon}")
        return False

    return True



def extract_drone_info(message, sn_to_drone_name, telegram):
    try:
        data = message['data']
    except KeyError:
        logging.error("Missing key 'data' in message")
        telegram.send_mqtt_queued("Missing key 'data' in message")
        return 
    

    try:
        #print(host_data)
        sn = data['sn']
    except KeyError:
        logging.error("Missing key 'sn' in message['data']", data)
        telegram.send_mqtt_queued("Missing key 'sn' in message['data']", data)
        return None

    if sn not in sn_to_drone_name:
        logging.error(f"Unknown serial number '{sn}' – not found in sn_to_drone_name mapping")
        telegram.send_mqtt_queued(f"Unknown drone SN: {sn}")
        raise ValueError(f"Unknown drone SN: {sn}")

    drone_url_name_list = sn_to_drone_name[sn]
    drone_name = drone_url_name_list[0][1]

    try:
        host_data = data['host']
    except KeyError:
        logging.error("Missing key 'host' in message['data']")
        return None

    try:
        longitude = host_data['longitude']
    except KeyError:
        logging.error("Missing key 'longitude' in message['data']['host']")
        return None

    try:
        latitude = host_data['latitude']
    except KeyError:
        logging.error("Missing key 'latitude' in message['data']['host']")
        return None
    if not validate_coordinates(latitude, longitude):
        return None
    else:
        telegram.send_validated_coord(drone_name, latitude, longitude)
        return drone_url_name_list, longitude, latitude


def extract_drone_name_mapping(DRONES_SN_LIST, DRONES_NAMES_LIST):
    sn_to_drone_name = {}
    for i in range(len(DRONES_SN_LIST)):
        sn = DRONES_SN_LIST[i].strip()
        name = DRONES_NAMES_LIST[i].strip()
        assert sn not in sn_to_drone_name, f"Duplicate SN found: {sn}"
        assert name, "Drone name cannot be empty."
        sn_to_drone_name[sn] = name
    return sn_to_drone_name
    

