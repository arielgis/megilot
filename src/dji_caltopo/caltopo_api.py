import requests
import logging

CALTOPO_API_BASE_URL = "https://caltopo.com/api/v1/position/report"
logger = logging.getLogger("caltopo_api")

def send_location_to_caltopo(connect_key, device_id, latitude, longitude):
    
    """
    Constructs and sends an HTTP GET request to the CalTopo position report API.
    """
    url = (
        f"{CALTOPO_API_BASE_URL}/{connect_key}"
        f"?id={device_id}&lat={latitude}&lng={longitude}"
    )
    print(f"DEBUG Sending url CalTopo API: {url} - should remove this line")

    logger.debug(f"Attempting to send location for Device ID '{device_id}' to CalTopo...")
    logger.debug(f"URL: {url}")

    send_request_to_caltopo(url, device_id)

def send_request_to_caltopo(url, device_id):
    """
    Sends a GET request to the specified CalTopo API URL and handles the response.
    Returns: request_duration (float, seconds)
    """
    try:
        t0 = time.time()
        response = requests.get(url)
        t1 = time.time()
        req_time = t1 - t0

        if response.status_code == 200:
            logger.info(f"✓ Sent for '{device_id}' ({req_time:.3f}s). Response: {response.text}")
        else:
            logger.warning(f"✗ Error sending for '{device_id}' ({req_time:.3f}s): HTTP {response.status_code}")

        return req_time

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending location for '{device_id}': {e}")
        return None