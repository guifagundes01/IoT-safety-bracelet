# ❤️‍🩹 IoT Safety Bracelet Dashboard

This project is a real-time monitoring dashboard built with **Streamlit**. It connects to a ThingSpeak channel to visualize sensor data from an IoT safety bracelet, designed for monitoring elderly individuals or at-risk persons.

The dashboard provides a "caregiver" view, prioritizing critical alerts (like fall detection) and location, while keeping detailed sensor data accessible in a collapsible section for technical debugging.

## Features

* **Persistent Fall Alerts:** Displays a prominent, persistent alert if a fall is detected. The alert must be manually acknowledged to be reset.
* **Simulated Notifications:** Shows a simulated "SMS Sent" message when a fall is detected.
* **GPS Location Map:** Shows the user's last known location. It's ready for dynamic GPS data but currently uses a fixed fallback location.
* **Vital Signs (Placeholder):** Includes a dedicated chart for Heart Rate (BPM), ready to display data once it's sent from the device.
* **Sensor Debug View:** A collapsible "expander" shows detailed, real-time charts for:
    * Gyroscope (X, Y, Z)
    * Accelerometer (X, Y, Z Deltas)
    * Total Acceleration Magnitude
* **Data Summary:** A sidebar displays the latest raw values and a history of fall events.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
    ```

3.  **Install the required libraries:**
    (It's best to create a `requirements.txt` file with the content below and run `pip install -r requirements.txt`)
    ```text
    streamlit
    requests
    pandas
    plotly
    ```
    Or install them manually:
    ```bash
    pip install streamlit requests pandas plotly
    ```

## Configuration

Before running the application, you **must** edit the main Python script (`dash_iot_v3.py` or your file name):

1.  **ThingSpeak Credentials:** Update these constants with your own channel information:
    ```python
    CHANNEL_ID = "3134375"  # <-- REPLACE with your Channel ID
    READ_API_KEY = "O729N63F5UVJ6IOZ" # <-- REPLACE with your Read API Key
    ```

2.  **Field Mapping:** This is the most important step. Ensure the `FIELD_MAP` dictionary correctly matches the data fields in your ThingSpeak channel.
    ```python
    FIELD_MAP = {
        'field1': 'Gyro X',
        'field2': 'Gyro Y',
        'field3': 'Gyro Z',
        'field4': 'Delta Accel X',
        'field5': 'Delta Accel Y',
        'field6': 'Delta Accel Z',
        'field7': 'Fall Detected (0/1)',
        'field8': 'Accel Magnitude',
        # 'field9': 'Heart Rate (BPM)',  # Uncomment when you send this
        # 'field10': 'Latitude',         # Uncomment when you send this
        # 'field11': 'Longitude'        # Uncomment when you send this
    }
    ```

3.  **(Optional) Fixed Location:** Change the `FIXED_LATITUDE` and `FIXED_LONGITUDE` constants to your desired fallback location.

## How to Run

Once configured, run the Streamlit app from your terminal:

```bash
streamlit run dash_iot_v3.py