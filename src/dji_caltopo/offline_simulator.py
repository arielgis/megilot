import os
import time
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def simulate_offline_messages(
    folder_path: str,
    queue,
    use_real_timestamps: bool = False,
    default_delay: float = 1.0,
    time_multiplier: float = 1.0
):
    """
    Simulate MQTT message flow by reading messages from log.csv and injecting them into the queue.

    Args:
        folder_path (str): Folder containing the message JSON files and log.csv.
        queue: The queue to push messages into.
        use_real_timestamps (bool): Use actual message intervals from log.csv.
        default_delay (float): Delay (in seconds) between messages if not using real timestamps.
        time_multiplier (float): Adjust real delay (e.g. 0.5 = 2× speed, 2 = half speed).
    """
    log_path = os.path.join(folder_path, "log.csv")

    if not os.path.isfile(log_path):
        logger.error(f"Missing log.csv in folder: {folder_path}")
        return

    logger.info(f"Starting offline message simulation from: {log_path}")
    previous_time = None

    with open(log_path, 'r', encoding='utf-8') as log_file:
        for line in log_file:
            try:
                timestamp_str, filename = line.strip().split(",")
                current_time = datetime.fromisoformat(timestamp_str)

                # Delay calculation
                if use_real_timestamps and previous_time:
                    delay = (current_time - previous_time).total_seconds() * time_multiplier
                    time.sleep(max(delay, 0))
                elif not use_real_timestamps:
                    time.sleep(default_delay)

                previous_time = current_time

                # Load the message from file
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    payload_str = f.read()
                    data = json.loads(payload_str)
                    queue.put(data)
                    logger.info(f"Simulated message: {filename}")

            except Exception as e:
                logger.error(f"Error processing line: {line.strip()}\n{e}")

    logger.info("Finished simulating all offline messages.")