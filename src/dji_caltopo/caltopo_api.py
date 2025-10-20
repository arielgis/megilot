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
    """
    try:
        response = requests.get(url)

        if response.status_code == 200:
            logger.info(f"✅ Location sent for '{device_id}'. Response: {response.text}")
        else:
            logger.warning(
                f"❌ Could not send location for '{device_id}'. "
                f"Status Code: {response.status_code}, Response: {response.text}"
            )

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Error sending location for '{device_id}': {e}")
        logger.error("Please ensure you have an active internet connection and the CalTopo API is reachable.")