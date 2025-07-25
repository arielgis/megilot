# Drone Telemetry to CalTopo

This project ingests drone telemetry data either in **real-time** via an MQTT broker or from **offline simulation logs**, extracts GPS coordinates, and sends location updates to the [CalTopo API](https://caltopo.com/) for live tracking or analysis.


## 🛠️ Step-by-Step Setup

### Step 1:  Configure DJI FlightHub

⚠️ Note: You must have sufficient permissions to set the sync settings.
Open your browser and go to:
👉 https://fh.dji.com/user-center#/my-organization

Actions -> Organization Settings (gear icon) -> FlightHub Sync (Beta)

Click "Edit" next to Telemetry Data and fill in the following MQTT details:

MQTT Host: 129.159.135.253, 

Port: 1883

Username: leave blank

Password: leave blank

Click Save.

⚠️ Note: Username and password are not supported yet—leave them blank.


![FlightHub Sync Screenshot](images/dji_sync_screenshot.png)




### Step 2: Access DJI Organization Page










## Features

- ✅ Connects to DJI FlightHub MQTT telemetry stream
- ✅ Reads offline JSON logs and replays them with accurate timing
- ✅ Extracts drone GPS coordinates (latitude, longitude)
- ✅ Supports multiple drones using serial number (SN) mapping
- ✅ Sends data to CalTopo using API
- ✅ Modular design with interchangeable backends
- ✅ Built-in logging and clean threading

---

## Project Structure

```bash
.
├── main.py                  # Main orchestrator for real-time or offline mode
├── mqtt_listener.py         # Connects to MQTT broker and pushes messages into a queue
├── offline_simulator.py     # Replays messages from folder using log.csv
├── caltopo_api.py           # Sends location data to CalTopo via HTTP API
├── .env                     # Local environment config (MQTT host, API key, etc.)
├── requirements.txt         # Python dependencies
└── README.md
