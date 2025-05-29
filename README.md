# Drone Telemetry to CalTopo

This project ingests drone telemetry data either in **real-time** via an MQTT broker or from **offline simulation logs**, extracts GPS coordinates, and sends location updates to the [CalTopo API](https://caltopo.com/) for live tracking or analysis.

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