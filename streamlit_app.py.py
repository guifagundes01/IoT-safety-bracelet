import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
from datetime import datetime

# --- ThingSpeak Configuration (Replace with YOUR values!) ---
CHANNEL_ID = "3134375"  # Your Channel ID
READ_API_KEY = "O729N63F5UVJ6IOZ" # Your Read API Key
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
NUM_RESULTS = 100 # Number of recent entries to fetch
REFRESH_INTERVAL_SECONDS = 20 # Refresh interval (>= 15s for free ThingSpeak plan)

# --- Field Mapping (Adjust as needed!) ---
# ADJUSTED to reflect main.c (8 fields) + placeholders for future fields
FIELD_MAP = {
    'field1': 'Gyro X',
    'field2': 'Gyro Y',
    'field3': 'Gyro Z',
    'field4': 'Delta Accel X',  # Renamed
    'field5': 'Delta Accel Y',  # Renamed
    'field6': 'Delta Accel Z',  # Renamed
    'field7': 'Fall Detected (0/1)',
    'field8': 'Accel Magnitude',
    # --- Placeholders for future data (add to your main.c) ---
    # 'field9': 'Heart Rate (BPM)', 
    # 'field10': 'Latitude',
    # 'field11': 'Longitude'
}

# --- Fixed Location for Map (Fallback) ---
FIXED_LATITUDE = 48.7111  # Near CentraleSupélec
FIXED_LONGITUDE = 2.2034 # Near CentraleSupélec

# --- Function to fetch and process ThingSpeak data ---
def fetch_thingspeak_data(api_key, results=NUM_RESULTS):
    """Fetches data from ThingSpeak and returns a Pandas DataFrame."""
    params = {
        'api_key': api_key,
        'results': results
    }
    try:
        response = requests.get(THINGSPEAK_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'feeds' not in data or not data['feeds']:
            st.warning("No data received from ThingSpeak or channel is empty.")
            return pd.DataFrame()

        df = pd.DataFrame(data['feeds'])
        df.rename(columns=FIELD_MAP, inplace=True)

        for field_name in FIELD_MAP.values():
            if field_name in df.columns:
                df[field_name] = pd.to_numeric(df[field_name], errors='coerce')

        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Europe/Paris') # Adjust your timezone!

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from ThingSpeak: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

# --- Initialize Session State (for Improvement 3) ---
if 'alert_active' not in st.session_state:
    st.session_state.alert_active = False
    st.session_state.alert_info = None

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Dashboard - Safety Bracelet",
    page_icon="👵",
    layout="wide"
)

st.title("❤️‍🩹 Safety Bracelet Dashboard")
st.caption(f"Real-time monitoring from ThingSpeak Channel: {CHANNEL_ID}")

# --- Layout Definition ---
col1, col2 = st.columns([2, 1]) # Main column (2/3) and sidebar (1/3)

# --- Placeholders ---
# Column 1 (Main)
placeholder_status = col1.empty()
placeholder_map = col1.empty()
placeholder_vitals = col1.empty() # Placeholder for Vital Signs
placeholder_debug_charts = col1.empty() # Placeholder for debug charts

# Column 2 (Sidebar)
placeholder_latest = col2.empty()
placeholder_fall_history = col2.empty()
placeholder_df = col2.empty()

counter = 0
# --- Auto-Refresh Loop ---
while True:
    counter += 1
    df_data = fetch_thingspeak_data(READ_API_KEY, results=NUM_RESULTS)

    if not df_data.empty:
        latest_entry = df_data.iloc[-1] # Get the most recent entry

        # --- Alert Detection and State Logic (Improvement 3) ---
        fall_field_name = FIELD_MAP.get('field7')
        if fall_field_name and fall_field_name in df_data.columns and not df_data[fall_field_name].isnull().all():
            fall_detected_in_history = (df_data[fall_field_name] == 1).any()
            
            # If a fall is detected AND the alert is not already active, activate it
            if fall_detected_in_history and not st.session_state.alert_active:
                st.session_state.alert_active = True
                # Save the information from the moment of the fall
                most_recent_fall_entry = df_data[df_data[fall_field_name] == 1].iloc[-1]
                st.session_state.alert_info = most_recent_fall_entry
        else:
            fall_detected_in_history = False


        # --- Alert Status (col1) (Improvement 1 & 3) ---
        with placeholder_status.container():
            st.subheader("🚨 Alert Status")
            
            # If the alert is "latched" in the session state
            if st.session_state.alert_active:
                fall_time = st.session_state.alert_info['created_at'].strftime('%H:%M:%S (%d/%m/%Y)')
                st.error(f"🔴 **FALL ALERT ACTIVE!**", icon="🚨")
                st.warning(f"🕒 Time of detection: {fall_time}")
                st.info("ℹ️ *Simulated: SMS Notification Sent to Emergency Contacts.*", icon="✉️")
                
                # Button to reset the alert (in the sidebar, col2)
                if col2.button("Acknowledge Alert / Reset", key=f"reset_btn_{counter}"):
                    st.session_state.alert_active = False
                    st.session_state.alert_info = None
                    st.rerun() # Force an immediate rerun
            
            # If no alert is active
            else:
                latest_time = latest_entry['created_at'].strftime('%H:%M:%S (%d/%m/%Y)')
                st.success(f"✅ **Status Normal.** No recent falls detected.", icon="👍")
                st.info(f"🕒 Last check: {latest_time}")
            st.divider()

        # --- Map (col1) (Improvement 4) ---
        with placeholder_map.container():
            st.subheader("📍 Location (GPS)")
            lat_field = FIELD_MAP.get('field10', 'Latitude') # Ex: 'field10'
            lon_field = FIELD_MAP.get('field11', 'Longitude') # Ex: 'field11'
            
            current_lat = FIXED_LATITUDE
            current_lon = FIXED_LONGITUDE
            
            # Try to use dynamic data if it exists
            if lat_field in latest_entry and lon_field in latest_entry and \
               pd.notna(latest_entry[lat_field]) and pd.notna(latest_entry[lon_field]):
                
                current_lat = latest_entry[lat_field]
                current_lon = latest_entry[lon_field]
                st.info(f"Showing real-time GPS location: ({current_lat:.4f}, {current_lon:.4f})", icon="🛰️")
            else:
                st.info(f"Showing fixed location (GPS data unavailable): ({current_lat:.4f}, {current_lon:.4f})", icon="🏠")

            map_data = pd.DataFrame({'lat': [current_lat], 'lon': [current_lon]})
            st.map(map_data, zoom=14)
            st.divider()

        # --- Vital Signs (col1) (Improvement 2 - Placeholder) ---
        with placeholder_vitals.container():
            st.subheader("❤️ Vital Signs (Heart Rate)")
            hr_field = FIELD_MAP.get('field9', 'Heart Rate (BPM)') # Ex: 'field9'
            
            if hr_field in df_data.columns and not df_data[hr_field].isnull().all():
                fig_hr = px.line(df_data, x='created_at', y=hr_field, title="Beats Per Minute (BPM)")
                fig_hr.update_layout(xaxis_title="Timestamp", yaxis_title="BPM")
                st.plotly_chart(fig_hr, use_container_width=True, key=f"hr_chart_{counter}")
            else:
                st.info("Heart Rate data (e.g., field9) is not being received yet.")
            st.divider()

        # --- Debug Charts (col1) (Improvement 1) ---
        with placeholder_debug_charts.container():
            with st.expander("Expand to see technical sensor data (Debug)"):
                
                # Magnitude Chart (most important for debug)
                st.subheader("📈 Acceleration Magnitude (Delta)")
                mag_field_name = FIELD_MAP.get('field8')
                if mag_field_name and mag_field_name in df_data.columns and not df_data[mag_field_name].isnull().all():
                     fig_mag = px.line(df_data, x='created_at', y=mag_field_name, title="Acceleration Magnitude (Delta) Over Time")
                     fig_mag.update_layout(xaxis_title="Timestamp", yaxis_title="Magnitude (Raw)")
                     st.plotly_chart(fig_mag, use_container_width=True, key=f"accel_mag_chart_{counter}")
                else:
                     st.warning("Acceleration Magnitude data (field 8) not found.")
                
                # Accelerometer Axes Chart
                st.subheader("📊 Accelerometer (Delta Axes)")
                accel_fields = [f for f in [FIELD_MAP.get('field4'), FIELD_MAP.get('field5'), FIELD_MAP.get('field6')] if f and f in df_data.columns]
                if accel_fields:
                    fig_accel = px.line(df_data, x='created_at', y=accel_fields, title="Accelerometer (Delta) Readings by Axis")
                    fig_accel.update_layout(xaxis_title="Timestamp", yaxis_title="Delta Acceleration (Raw)", legend_title="Axis")
                    st.plotly_chart(fig_accel, use_container_width=True, key=f"accel_chart_{counter}")
                else:
                    st.warning("Accelerometer axes data (fields 4-6) not found.")

                # Gyroscope Chart
                st.subheader("🌀 Gyroscope")
                gyro_fields = [f for f in [FIELD_MAP.get('field1'), FIELD_MAP.get('field2'), FIELD_MAP.get('field3')] if f and f in df_data.columns]
                if gyro_fields:
                    fig_gyro = px.line(df_data, x='created_at', y=gyro_fields, title="Gyroscope Readings")
                    fig_gyro.update_layout(xaxis_title="Timestamp", yaxis_title="Angular Velocity", legend_title="Axis")
                    st.plotly_chart(fig_gyro, use_container_width=True, key=f"gyro_chart_{counter}")
                else:
                     st.warning("Gyroscope data (fields 1-3) not found.")

        # --- Latest Values (col2) ---
        with placeholder_latest.container():
             st.subheader("⏱️ Latest Values")
             for field_orig, field_name in FIELD_MAP.items():
                  if field_name in latest_entry and pd.notna(latest_entry[field_name]):
                       # Don't show Lat/Lon (already on map)
                       if field_name not in ['Latitude', 'Longitude']: 
                            val = latest_entry[field_name]
                            formatted_value = f"{val:.2f}" if isinstance(val, float) else int(val)
                            st.metric(label=field_name, value=formatted_value)
             st.divider()

        # --- Fall History (col2) ---
        with placeholder_fall_history.container():
            st.subheader("📉 Fall History")
            if fall_field_name and fall_field_name in df_data.columns:
                 fig_fall = px.line(df_data, x='created_at', y=fall_field_name, markers=True,
                                    title="Detection Events (0=Normal, 1=Fall)")
                 fig_fall.update_layout(yaxis=dict(range=[-0.1, 1.1]), xaxis_title="Timestamp", yaxis_title="Status")
                 st.plotly_chart(fig_fall, use_container_width=True, key=f"fall_history_chart_{counter}")
            else:
                 st.warning("Fall history data (field 7) not found.")
            st.divider()

        # --- Raw Data Table (col2) ---
        with placeholder_df.container():
            st.subheader("📄 Raw Data (Recent)")
            display_columns = ['created_at'] + [f for f in FIELD_MAP.values() if f in df_data.columns]
            st.dataframe(df_data[display_columns].iloc[::-1].head(5), use_container_width=True) # Show the 5 most recent

    else:
        # Clear placeholders if no data
        placeholder_status.info("Waiting for data from ThingSpeak...")
        placeholder_map.empty()
        placeholder_vitals.empty()
        placeholder_debug_charts.empty()
        placeholder_latest.empty()
        placeholder_fall_history.empty()
        placeholder_df.empty()

    # --- Wait before next refresh ---
    time.sleep(REFRESH_INTERVAL_SECONDS)