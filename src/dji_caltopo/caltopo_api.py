import requests

CALTOPO_API_BASE_URL = "https://caltopo.com/api/v1/position/report"

def send_location_to_caltopo(connect_key, device_id, latitude, longitude):
    """
    Constructs and sends an HTTP GET request to the Caltopo position report API.

    Args:
        connect_key (str): Your unique Caltopo Connect Key.
        device_id (str): The specific device ID for this report (e.g., M3T, M200).
        latitude (float): The latitude coordinate.
        longitude (float): The longitude coordinate.
    """

    # Construct the full URL with parameters
    # Caltopo's API expects the Connect Key in the path and other details as query parameters.
    url = (
        f"{CALTOPO_API_BASE_URL}/{connect_key}"
        f"?id={device_id}&lat={latitude}&lng={longitude}"
    )

    print(f"Attempting to send location for Device ID '{device_id}' to Caltopo...")
    print(f"URL: {url}")

    send_request_to_caltopo(url, device_id)

def send_request_to_caltopo(url, device_id):
    """
    Sends a GET request to the specified Caltopo API URL and handles the response.

    Args:
        url (str): The full API URL to send the request to.
        device_id (str): The device ID for logging purposes.
    """
    try:
        # Make the HTTP GET request
        response = requests.get(url)

        # Check the response status code
        if response.status_code == 200:
            print(f"SUCCESS: Location sent for '{device_id}'. Response: {response.text}")
        else:
            print(f"FAILED: Could not send location for '{device_id}'.")
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"AN ERROR OCCURRED: {e}")
        print("Please ensure you have an active internet connection and the Caltopo API is reachable.")

