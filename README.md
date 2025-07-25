# Drone Telemetry to CalTopo

This project ingests drone telemetry data either in **real-time** via an MQTT broker or from **offline simulation logs**, extracts GPS coordinates, and sends location updates to the [CalTopo API](https://caltopo.com/) for live tracking or analysis.


## 🛠️ Step-by-Step Guide

### Step 1:  Configure DJI FlightHub

⚠️ Note: You must have sufficient permissions to set the sync settings.
Open your browser and go to:
👉 https://fh.dji.com/user-center#/my-organization

Actions -> Organization Settings (gear icon) -> FlightHub Sync (Beta)

Click **Edit** next to **Telemetry Data** and enter the following:

MQTT Host: 129.159.135.253  
Port: 1883  
Username: (leave blank)  
Password: (leave blank)

Click Save.

⚠️ Note: Username and password are not supported yet—leave them blank.


![FlightHub Sync Screenshot](images/dji_sync_screenshot.png)




### Step 2: Get Access token from Caltopo

⚠️ Note: You must have sufficient permissions in the CalTopo group to view or create access tokens.

Navigate to your CalTopo group’s administration page.

Scroll down to the “Trackable Devices” section.

Click “Create New Access URL” (or use an existing one if already available).

Copy the **Access Token** — this will be used to send location data from the drone to CalTopo.

🔒 Keep this token secure — anyone with it can send location updates to your group.

![Caltopo Trackable Devices Screenshot](images/trackable_devices.png)
 








---




For **feature requests**, **bug reports**, or **technical assistance**, please contact:
👉 dji.caltopo.sync@gmail.com