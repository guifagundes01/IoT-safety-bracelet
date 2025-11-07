import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# --- ThingSpeak Configuration (Replace with YOUR values!) ---
CHANNEL_ID = "3134375"  # Enter your Channel ID here
READ_API_KEY = "O729N63F5UVJ6IOZ" # Enter your Read API Key here
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
NUM_RESULTS = 100 # Number of recent entries to fetch
REFRESH_INTERVAL_SECONDS = 20 # Auto-refresh interval (>= 15s for free ThingSpeak plan)

# --- Field Mapping (Adjust as needed!) ---
# IMPORTANT: Make sure these fields match your ThingSpeak channel setup!
FIELD_MAP = {
    'field1': 'Gyro X',
    'field2': 'Gyro Y',
    'field3': 'Gyro Z',
    'field4': 'Accel X (mg)',
    'field5': 'Accel Y (mg)',
    'field6': 'Accel Z (mg)',
    'field7': 'Fall Detected (0/1)',
    'field8': 'Accel Magnitude',
    'field9': 'Latitude', # Assuming Latitude is in field 8
    'field10': 'Longitude' # Assuming Longitude is in field 9
    # Add more fields if needed (e.g., Heart Rate)
}

# --- Fixed Location for Map (Replace with dynamic data later) ---
FIXED_LATITUDE = 48.7111  # Example: Near CentraleSupélec
FIXED_LONGITUDE = 2.2034 # Example: Near CentraleSupélec

# --- Function to fetch and process ThingSpeak data ---
def fetch_thingspeak_data(api_key, results=NUM_RESULTS):
    """Fetches data from ThingSpeak and returns a Pandas DataFrame."""
    params = {
        'api_key': api_key,
        'results': results
    }
    try:
        response = requests.get(THINGSPEAK_URL, params=params, timeout=10)
        response.raise_for_status() # Raise exception for HTTP errors
        data = response.json()

        if 'feeds' not in data or not data['feeds']:
            st.warning("No data received from ThingSpeak or channel is empty.")
            return pd.DataFrame() # Return empty DataFrame

        df = pd.DataFrame(data['feeds'])

        # Rename columns using FIELD_MAP
        df.rename(columns=FIELD_MAP, inplace=True)

        # Convert field columns to numeric (ignore errors for missing columns)
        for field_name in FIELD_MAP.values():
            if field_name in df.columns:
                # Convert all mapped fields to numeric, coercing errors
                df[field_name] = pd.to_numeric(df[field_name], errors='coerce')

        # Convert 'created_at' to datetime and adjust timezone (if needed)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Europe/Paris') # Adjust to your timezone!

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from ThingSpeak: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Dashboard - Safety Bracelet",
    page_icon="👵",
    layout="wide"
)

st.title("❤️‍🩹 Safety Bracelet Dashboard")
st.caption(f"Real-time monitoring from ThingSpeak Channel ID: {CHANNEL_ID}")

# --- Layout Definition ---
col1, col2 = st.columns([2, 1]) # Make first column wider

# Placeholders within columns
with col1:
    placeholder_status = st.empty()
    placeholder_map = st.empty()
    placeholder_accel = st.empty()
    placeholder_accel_mag = st.empty() # <<< ADDED Placeholder for Magnitude Chart
    placeholder_gyro = st.empty()
with col2:
    placeholder_latest = st.empty()
    placeholder_fall_history = st.empty()
    placeholder_df = st.empty()

counter = 0
# --- Auto-Refresh Loop ---
while True:
    counter += 1
    df_data = fetch_thingspeak_data(READ_API_KEY, results=NUM_RESULTS)

    if not df_data.empty:
        latest_entry = df_data.iloc[-1] # Get the most recent data entry

        # --- Fall Detection Status (Prominent Display in Col1) ---
        with placeholder_status.container():
            st.subheader("🚨 Fall Alert Status")
            fall_field_name = FIELD_MAP.get('field7') # Get the mapped name
            if fall_field_name and fall_field_name in df_data.columns and not df_data[fall_field_name].isnull().all():
                fall_detected_in_history = (df_data[fall_field_name] == 1).any()
                if fall_detected_in_history:
                    most_recent_fall_entry = df_data[df_data[fall_field_name] == 1].iloc[-1]
                    fall_time = most_recent_fall_entry['created_at'].strftime('%H:%M:%S (%d/%m/%Y)')
                    st.error(f"🔴 **FALL DETECTED within the last {NUM_RESULTS} readings!**", icon="🚨")
                    st.warning(f"🕒 Most Recent Fall Time: {fall_time}")
                    st.info("ℹ️ *Simulated: Notification SMS Sent to Emergency Contacts*", icon="✉️")
                else:
                    latest_time = df_data['created_at'].iloc[-1].strftime('%H:%M:%S (%d/%m/%Y)')
                    st.success(f"✅ **Status Normal.** No falls detected in the last {NUM_RESULTS} readings.", icon="👍")
                    st.info(f"🕒 Last check: {latest_time}")
            else:
                st.warning("Fall detection data (field 7) is currently unavailable or has no valid entries.")
            st.divider()

        # --- Real-Time Location Map (Col1) ---
        with placeholder_map.container():
            st.subheader("📍 Last Known Location")
            # Using fixed location - Adjust FIELD_MAP if Lat/Lon fields changed
            lat_field = FIELD_MAP.get('field9') # Check if this is still correct
            lon_field = FIELD_MAP.get('field10')# Check if this is still correct
            current_lat = FIXED_LATITUDE
            current_lon = FIXED_LONGITUDE
            st.info(f"Showing fixed location: ({current_lat:.4f}, {current_lon:.4f}). Integrate GPS data later.")
            map_data = pd.DataFrame({'lat': [current_lat], 'lon': [current_lon]})
            st.map(map_data, zoom=14)
            st.divider()

        # --- Accelerometer Chart (Col1) ---
        with placeholder_accel.container():
            st.subheader("📊 Accelerometer Axes")
            # Adjust fields if you are sending deltas
            accel_fields = [f for f in [FIELD_MAP.get('field4'), FIELD_MAP.get('field5'), FIELD_MAP.get('field6')] if f and f in df_data.columns]
            if accel_fields:
                fig_accel = px.line(df_data, x='created_at', y=accel_fields, title="Accelerometer Readings per Axis")
                fig_accel.update_layout(xaxis_title="Timestamp", yaxis_title="Acceleration (Raw/Delta?)", legend_title="Axis")
                st.plotly_chart(fig_accel, use_container_width=True, key=f"accel_chart_{counter}")
            else:
                st.warning("Accelerometer axis data (fields 4-6) not found.")

        # --- Accelerometer Magnitude Chart (Col1) <<< NEW CHART ---
        with placeholder_accel_mag.container():
            st.subheader("📈 Acceleration Magnitude")
            mag_field_name = FIELD_MAP.get('field8')
            if mag_field_name and mag_field_name in df_data.columns and not df_data[mag_field_name].isnull().all():
                 fig_mag = px.line(df_data, x='created_at', y=mag_field_name, title="Total Acceleration Magnitude Over Time")
                 fig_mag.update_layout(xaxis_title="Timestamp", yaxis_title="Magnitude (Raw Unit)") # Adjust unit label if known
                 st.plotly_chart(fig_mag, use_container_width=True, key=f"accel_mag_chart_{counter}")
            else:
                 st.warning("Acceleration magnitude data (field 8) not found or is empty.")
            st.divider() # Add divider after magnitude chart

        # --- Gyroscope Chart (Col1) ---
        with placeholder_gyro.container():
            st.subheader("🌀 Gyroscope")
            gyro_fields = [f for f in [FIELD_MAP.get('field1'), FIELD_MAP.get('field2'), FIELD_MAP.get('field3')] if f and f in df_data.columns]
            if gyro_fields:
                fig_gyro = px.line(df_data, x='created_at', y=gyro_fields, title="Gyroscope Readings")
                fig_gyro.update_layout(xaxis_title="Timestamp", yaxis_title="Angular Velocity", legend_title="Axis") # Adjust unit if known
                st.plotly_chart(fig_gyro, use_container_width=True, key=f"gyro_chart_{counter}")
            else:
                 st.warning("Gyroscope data (fields 1-3) not found.")

        # --- Latest Values Summary (Col2) ---
        with placeholder_latest.container():
             st.subheader("⏱️ Latest Values")
             for field_orig, field_name in FIELD_MAP.items():
                  if field_name in latest_entry and pd.notna(latest_entry[field_name]):
                       if field_name not in ['Latitude', 'Longitude']:
                            # Handle potential float magnitude value
                            if field_name == FIELD_MAP.get('field8'): # Check if it's the magnitude field
                                formatted_value = f"{latest_entry[field_name]:.2f}"
                            else: # Treat others as integer for display
                                formatted_value = int(latest_entry[field_name])
                            st.metric(label=field_name, value=formatted_value)
             st.divider()

        # --- Fall Detection History Chart (Col2) ---
        with placeholder_fall_history.container():
            st.subheader("📉 Fall History")
            fall_field_name = FIELD_MAP.get('field7')
            if fall_field_name and fall_field_name in df_data.columns:
                 fig_fall = px.line(df_data, x='created_at', y=fall_field_name, markers=True,
                                    title="Detection Events (0=Normal, 1=Fall)")
                 fig_fall.update_layout(yaxis=dict(range=[-0.1, 1.1]), xaxis_title="Timestamp", yaxis_title="Status")
                 st.plotly_chart(fig_fall, use_container_width=True, key=f"fall_history_chart_{counter}")
            else:
                 st.warning("Fall detection data (field 7) not found for history chart.")
            st.divider()

        # --- Raw Data Table (Col2) ---
        with placeholder_df.container():
            st.subheader("📄 Raw Data (Recent)")
            display_columns = ['created_at'] + [f for f in FIELD_MAP.values() if f in df_data.columns]
            st.dataframe(df_data[display_columns].iloc[::-1].head(5), use_container_width=True) # Show latest 5

    else:
        # Clear placeholders if no data
        placeholder_status.info("Waiting for data from ThingSpeak...")
        placeholder_map.empty()
        placeholder_accel.empty()
        placeholder_accel_mag.empty() # <<< Clear magnitude placeholder
        placeholder_gyro.empty()
        placeholder_latest.empty()
        placeholder_fall_history.empty()
        placeholder_df.empty()

    # --- Wait before the next refresh ---
    time.sleep(REFRESH_INTERVAL_SECONDS)