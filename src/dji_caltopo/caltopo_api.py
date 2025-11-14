import time
import requests
import logging

CALTOPO_API_BASE_URL = "https://caltopo.com/api/v1/position/report"
logger = logging.getLogger("caltopo_api")

def send_location_to_caltopo(connect_key, device_id, latitude, longitude):
    """
    Constructs and sends an HTTP GET request to the CalTopo position report API.
    Returns the HTTP request duration in seconds (float), or None on error.
    """
    url = (
        f"{CALTOPO_API_BASE_URL}/{connect_key}"
        f"?id={device_id}&lat={latitude}&lng={longitude}"
    )
    print(f"DEBUG Sending url CalTopo API: {url} - should remove this line")

    try:
        t0 = time.time()
        # Add a timeout so a single slow request doesn't block forever
        response = requests.get(url, timeout=3)
        t1 = time.time()
        req_time = t1 - t0

        if response.status_code == 200:
            logger.info(
                f"✅ Location sent for '{device_id}' in {req_time:.3f}s. "
                f"Response: {response.text}"
            )
        else:
            logger.warning(
                f"❌ Could not send location for '{device_id}' "
                f"(HTTP {response.status_code}, {req_time:.3f}s). "
                f"Response: {response.text}"
            )

        return req_time

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Error sending location for '{device_id}': {e}")
        logger.error(
            "Please ensure you have an active internet connection and the CalTopo API is reachable."
        )
        return None

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