import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
import pytz # <-- Added for timezone-aware date filtering

# --- ThingSpeak Configuration (Replace with YOUR values!) ---
CHANNEL_ID = "3134375"  # Your Channel ID
READ_API_KEY = "O729N63F5UVJ6IOZ" # Your Read API Key
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
NUM_RESULTS = 1000 # Number of recent entries to fetch (use 100 for "Today" filter)
REFRESH_INTERVAL_SECONDS = 20 # Refresh interval

# --- Field Mapping (Adjust as needed!) ---
FIELD_MAP = {
    'field1': 'Gyro X',
    'field2': 'Gyro Y',
    'field3': 'Gyro Z',
    'field4': 'Delta Accel X',
    'field5': 'Delta Accel Y',
    'field6': 'Delta Accel Z',
    'field7': 'Fall Detected (0/1)',
    'field8': 'Accel Magnitude',
    # --- Placeholders for future data ---
    'field9': 'Heart Rate (BPM)', 
    'field10': 'Latitude',
    'field11': 'Longitude'
}

# --- Fixed Location for Map (Fallback) ---
FIXED_LATITUDE = 48.7111  # Near CentraleSupélec
FIXED_LONGITUDE = 2.2034 # Near CentraleSupélec
TIMEZONE = 'Europe/Paris' # IMPORTANT: Set your local timezone

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
            # Convert to datetime and then localize to our target timezone
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert(TIMEZONE) 

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from ThingSpeak: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame()

# --- Initialize Session State (for Persistent Alert) ---
if 'alert_active' not in st.session_state:
    st.session_state.alert_active = False
if 'alert_info' not in st.session_state:
    st.session_state.alert_info = None
if 'last_acknowledged_fall_time' not in st.session_state:
    st.session_state.last_acknowledged_fall_time = None
### FIX 1: Add a variable to store the time of the last acknowledged fall ###
if 'last_acknowledged_fall_time' not in st.session_state:
    st.session_state.last_acknowledged_fall_time = None

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Dashboard - Safety Bracelet",
    page_icon="👵",
    layout="wide"
)

st.title("❤️‍🩹 Safety Bracelet Dashboard")
st.caption(f"Real-time monitoring from ThingSpeak Channel: {CHANNEL_ID}")

# --- Placeholder for the "Fixed" Row 1 (Alert Status) ---
placeholder_status = st.empty()

### NEW FEATURE 2: Date Filter ###
# Place the filter in the main body, above the tabs
time_filter = st.radio(
    "Select data range:",
    ("All history", "Today"),
    horizontal=True,
    key="time_filter"
)
### END NEW FEATURE 2 ###

# --- Placeholder for the "Menu" Row 2 (Tabs) ---
placeholder_tabs = st.empty()

counter = 0
# --- Auto-Refresh Loop ---
while True:
    counter += 1
    df_data = fetch_thingspeak_data(READ_API_KEY, results=NUM_RESULTS)

    # --- Apply Date Filter ---
    df_filtered = df_data.copy()
    if time_filter == "Today" and not df_data.empty:
        today = datetime.now(pytz.timezone(TIMEZONE)).date()
        df_filtered = df_data[df_data['created_at'].dt.date == today]

    if not df_filtered.empty:
        latest_entry = df_filtered.iloc[-1] # Get the most recent entry *from the filtered data*

        # --- Alert Detection and State Logic ---
        fall_field_name = FIELD_MAP.get('field7')
        if fall_field_name and fall_field_name in df_filtered.columns and not df_filtered[fall_field_name].isnull().all():
            fall_detected_in_history = (df_filtered[fall_field_name] == 1).any()
            
            if fall_detected_in_history:
                # Get the most recent fall from the *filtered* data
                most_recent_fall_entry = df_filtered[df_filtered[fall_field_name] == 1].iloc[-1]
                
                ### FIX 1: Check if this fall is NEWER than the last one we acknowledged ###
                is_new_fall = (st.session_state.last_acknowledged_fall_time is None) or \
                              (most_recent_fall_entry['created_at'] > st.session_state.last_acknowledged_fall_time)
                
                if is_new_fall and not st.session_state.alert_active:
                    st.session_state.alert_active = True
                    st.session_state.alert_info = most_recent_fall_entry
        else:
            fall_detected_in_history = False


        # --- ROW 1: "Fixed" Alert Status Row ---
        with placeholder_status.container():
            status_col, button_col = st.columns([3, 1]) 
            
            with status_col:
                if st.session_state.alert_active:
                    fall_time = st.session_state.alert_info['created_at'].strftime('%H:%M:%S (%d/%m/%Y)')
                    st.error(f"🔴 **FALL ALERT ACTIVE!** (Detected at: {fall_time})", icon="🚨")
                    st.info("ℹ️ *EMAIL Notification Sent.*", icon="✉️")
                else:
                    latest_time = latest_entry['created_at'].strftime('%H:%M:%S (%d/%m/%Y)')
                    st.success(f"✅ **Status: Normal.** (Last check: {latest_time})", icon="👍")

            with button_col:
                if st.session_state.alert_active:
                    st.write("") 
                    st.write("")
                    ### FIX 1: Update button logic to store acknowledged time ###
                    if st.button("Acknowledge Alert / Reset", key=f"reset_btn_{counter}", type="primary"):
                        # Store the timestamp of the fall we are acknowledging
                        st.session_state.last_acknowledged_fall_time = st.session_state.alert_info['created_at']
                        # Now reset the active alert
                        st.session_state.alert_active = False
                        st.session_state.alert_info = None
                        st.rerun()
            
            st.divider()


        # --- ROW 2: Menu with Tabs ---
        with placeholder_tabs.container():
            
            # Create the tabs (menu)
            ### NEW FEATURE 4: Added Report Tab ###
            tab_map, tab_vitals, tab_fall, tab_debug, tab_raw, tab_report = st.tabs([
                "📍 Location", 
                "❤️ Vitals", 
                "📉 Fall Analysis", 
                "🔬 Sensor Debug", 
                "📄 Raw Data",
                "📊 Report"
            ])

            # --- Tab 1: Map ---
            with tab_map:
                st.subheader("Last Known Location (GPS)")
                lat_field = FIELD_MAP.get('field10', 'Latitude') 
                lon_field = FIELD_MAP.get('field11', 'Longitude') 
                
                current_lat = FIXED_LATITUDE
                current_lon = FIXED_LONGITUDE
                
                if lat_field in latest_entry and lon_field in latest_entry and \
                   pd.notna(latest_entry[lat_field]) and pd.notna(latest_entry[lon_field]):
                    
                    current_lat = latest_entry[lat_field]
                    current_lon = latest_entry[lon_field]
                    st.info(f"Showing real-time GPS location: ({current_lat:.4f}, {current_lon:.4f})", icon="🛰️")
                else:
                    st.info(f"Showing fixed location (GPS data unavailable): ({current_lat:.4f}, {current_lon:.4f})", icon="🏠")

                map_data = pd.DataFrame({'lat': [current_lat], 'lon': [current_lon]})
                st.map(map_data, zoom=14)

            # --- Tab 2: Vital Signs ---
            with tab_vitals:
                st.subheader("Heart Rate (BPM)")
                hr_field = FIELD_MAP.get('field9', 'Heart Rate (BPM)') 
                
                if hr_field in df_filtered.columns and not df_filtered[hr_field].isnull().all():
                    st.metric(label="Latest Heart Rate", value=f"{int(latest_entry[hr_field])} BPM")
                    fig_hr = px.line(df_filtered, x='created_at', y=hr_field, title="Heart Rate Over Time")
                    fig_hr.update_layout(xaxis_title="Timestamp", yaxis_title="BPM")
                    st.plotly_chart(fig_hr, key=f"hr_chart_{counter}", use_container_width=True)
                else:
                    st.info("Heart Rate data (e.g., field9) is not being received yet.")
            
            # --- Tab 3: Fall Analysis ---
            with tab_fall:
                st.subheader("Fall Detection Data Analysis")
                col_mag_hist, col_fall_hist = st.columns(2)

                with col_mag_hist:
                    mag_field_name = FIELD_MAP.get('field8')
                    if mag_field_name and mag_field_name in df_filtered.columns and not df_filtered[mag_field_name].isnull().all():
                         st.metric(label="Latest Accel. Magnitude", value=int(latest_entry[mag_field_name]))
                         fig_mag = px.line(df_filtered, x='created_at', y=mag_field_name, title="Acceleration Magnitude (Delta) Over Time")
                         fig_mag.update_layout(xaxis_title="Timestamp", yaxis_title="Magnitude (Raw)")
                         st.plotly_chart(fig_mag, key=f"accel_mag_chart_{counter}", use_container_width=True)
                    else:
                         st.warning("Acceleration Magnitude data (field 8) not found.")
                
                with col_fall_hist:
                    if fall_field_name and fall_field_name in df_filtered.columns:
                         st.metric(label=f"Total Falls (Last {NUM_RESULTS})", value=int(df_filtered[fall_field_name].sum()))
                         fig_fall = px.line(df_filtered, x='created_at', y=fall_field_name, markers=True,
                                            title="Detection Events (0=Normal, 1=Fall)")
                         fig_fall.update_layout(yaxis=dict(range=[-0.1, 1.1]), xaxis_title="Timestamp", yaxis_title="Status")
                         st.plotly_chart(fig_fall, key=f"fall_history_chart_{counter}", use_container_width=True)
                    else:
                         st.warning("Fall history data (field 7) not found.")
            # --- Tab 4: Sensor Debug ---
            with tab_debug:
                st.subheader("Raw Sensor Data (IMU)")
                col_gyro, col_accel = st.columns(2)

                with col_gyro:
                    gyro_fields = [f for f in [FIELD_MAP.get('field1'), FIELD_MAP.get('field2'), FIELD_MAP.get('field3')] if f and f in df_filtered.columns]
                    if gyro_fields:
                        fig_gyro = px.line(df_filtered, x='created_at', y=gyro_fields, title="Gyroscope Readings")
                        fig_gyro.update_layout(xaxis_title="Timestamp", yaxis_title="Angular Velocity", legend_title="Axis")
                        st.plotly_chart(fig_gyro, key=f"gyro_chart_{counter}", use_container_width=True)
                    else:
                         st.warning("Gyroscope data (fields 1-3) not found.")

                with col_accel:
                    accel_fields = [f for f in [FIELD_MAP.get('field4'), FIELD_MAP.get('field5'), FIELD_MAP.get('field6')] if f and f in df_filtered.columns]
                    if accel_fields:
                        fig_accel = px.line(df_filtered, x='created_at', y=accel_fields, title="Accelerometer (Delta) Readings by Axis")
                        fig_accel.update_layout(xaxis_title="Timestamp", yaxis_title="Delta Acceleration (Raw)", legend_title="Axis")
                        st.plotly_chart(fig_accel, key=f"accel_chart_{counter}", use_container_width=True)
                    else:
                        st.warning("Accelerometer axes data (fields 4-6) not found.")

            # --- Tab 5: Raw Data ---
            with tab_raw:
                st.subheader(f"Raw Data Table ({time_filter})")
                display_columns = ['created_at'] + [f for f in FIELD_MAP.values() if f in df_filtered.columns]
                # Fix for dataframe deprecation
                st.dataframe(df_filtered[display_columns].iloc[::-1], width='stretch') # Show all filtered data
            
            ### NEW FEATURE 4: Report Tab ###
            with tab_report:
                st.subheader(f"Data Report ({time_filter})")
                
                st.info(f"This is a summary of all data collected for the selected time range: **{time_filter}**.")
                
                report_col1, report_col2 = st.columns(2)
                
                with report_col1:
                    st.subheader("Fall & Impact Summary")
                    total_falls = int(df_filtered[fall_field_name].sum())
                    st.metric(label="Total Falls Detected", value=total_falls)
                    
                    if not df_filtered[FIELD_MAP.get('field8')].isnull().all():
                        max_mag = int(df_filtered[FIELD_MAP.get('field8')].max())
                        st.metric(label="Max Impact Magnitude", value=max_mag)
                    
                with report_col2:
                    st.subheader("Vital Signs Summary")
                    hr_field = FIELD_MAP.get('field9', 'Heart Rate (BPM)')
                    if hr_field in df_filtered.columns and not df_filtered[hr_field].isnull().all():
                        avg_hr = int(df_filtered[hr_field].mean())
                        min_hr = int(df_filtered[hr_field].min())
                        max_hr = int(df_filtered[hr_field].max())
                        st.metric(label="Average Heart Rate", value=f"{avg_hr} BPM")
                        st.metric(label="Min Heart Rate", value=f"{min_hr} BPM")
                        st.metric(label="Max Heart Rate", value=f"{max_hr} BPM")
                    else:
                        st.write("No Heart Rate data available for this report.")
            ### END NEW FEATURE 4 ###
        
    else:
        # Clear placeholders if no data
        placeholder_status.info("Waiting for data from ThingSpeak...")
        placeholder_tabs.empty() 

    # --- Wait before next refresh ---
    time.sleep(REFRESH_INTERVAL_SECONDS)