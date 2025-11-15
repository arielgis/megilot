import time
import requests
import logging
import os
import random



class TelegramMessageManager:
    def __init__(self,  bot_token, chat_id_str):
        self.last_sent = {
            "startup": 0,
            "validated_coord": 0,
            "mqtt_queue": 0,
            "heartbeat": 0
        }
        self.enabled = False

        try:
            self.bot_token = bot_token
            self.chat_id = int(chat_id_str)
            self.enabled = True
            logging.info("✅ TelegramMessageManager initialized")
        except ValueError:
            logging.error(f"❌ TELEGRAM_CHAT_ID is not a valid integer: {chat_id_str}")

    def _send(self, text):
        if not self.enabled:
            logging.warning("TelegramMessageManager is not enabled. Message not sent.")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            r = requests.post(url, json=payload)
            if r.status_code != 200:
                logging.error(f"Telegram send failed: {r.status_code} - {r.text}")
        except Exception as e:
            logging.error(f"Telegram send exception: {e}")

    def send_startup(self):
        if time.time() - self.last_sent["startup"] > 5:
            self._send("🟢 Code restarted.")
            self.last_sent["startup"] = time.time()

    def send_validated_coord(self, drone_name, lat, lon, total_delay=None):
        if time.time() - self.last_sent["validated_coord"] > 180:  # 3 minutes
            # Optional extra line for delay
            delay_line = ""
            if total_delay is not None:
                delay_line = f"\nTotal processing time: {total_delay:.1f}s"

            self._send(
                f"📍 GPS Position of <b>{drone_name}</b>: sent to Caltopo\n"
                f"lat={lat:.5f}, lon={lon:.5f}\n"
                f"https://www.google.com/maps?q={lat:.5f},{lon:.5f}{delay_line}"
                
            )
           # print(f"DEBUG: {delay_line}")
            self.last_sent["validated_coord"] = time.time()

    def send_mqtt_queued(self, message):
        if time.time() - self.last_sent["mqtt_queue"] > 600:  # 10 minutes
            self._send(f"📦 Recieved new message : {message}")
            self.last_sent["mqtt_queue"] = time.time()

    def send_heartbeat(self):
        if time.time() - self.last_sent["heartbeat"] > 21600:  # 6 hours
            message = "✅ Live and running (heartbeat) \n" #+ random.choice(AI_MESSAGES_HE)
            self._send(message)
            self.last_sent["heartbeat"] = time.time()


    def send_registration(self, sn, url_access):
        # Send immediately without throttling
        sn_short = f"***{sn[-3:]}" if len(sn) > 3 else sn
        url_short = f"***{url_access[-3:]}" if len(url_access) > 3 else url_access

        message = (
            "🆕 New drone registration\n"
            f"SN: {sn_short}\n"
            f"Key: {url_short}"
        )
        self._send(message)
                