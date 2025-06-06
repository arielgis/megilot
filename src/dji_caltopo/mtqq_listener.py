import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

def start_mqtt_listener(queue, host, port, topic_list):
    """
    Connects to MQTT broker and listens for messages.
    Every valid JSON message is pushed into the queue.
    """

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker: {host}:{port}")
            for topic in topic_list:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT Broker, rc={rc}")

    def on_message(client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
            data = json.loads(payload_str)
            #print(data["sn"])
            queue.put(data)
            logger.info(f"Queued message from topic '{msg.topic}'")
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Unexpected error while handling message: {e}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, port, 60)
        logger.info("Starting MQTT listener loop...")
        client.loop_forever()  # Blocking call, should be run in a thread
    except Exception as e:
        logger.error(f"MQTT connection or loop failed: {e}")