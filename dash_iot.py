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
# Based on your C code, you seem to send 6+ values.
# Adjust the names here to match what each field represents.
FIELD_MAP = {
    'field1': 'Accel X (mg)',
    'field2': 'Accel Y (mg)',
    'field3': 'Accel Z (mg)',
    'field4': 'Gyro X (raw/scaled?)', # Check unit/scale sent from C code
    'field5': 'Gyro Y (raw/scaled?)', # Check unit/scale sent from C code
    'field6': 'Gyro Z (raw/scaled?)', # Check unit/scale sent from C code
    'field7': 'Fall Detected (0/1)', # Assuming you send fall status to field 7
    # Add 'field8' if needed for Heart Rate or GPS
}

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
        for field in FIELD_MAP.values():
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce') # 'coerce' turns errors into NaN

        # Convert 'created_at' to datetime and adjust timezone (if needed)
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('Europe/Paris') # Adjust to your timezone!
            # Or use .dt.tz_localize(None) if you don't need timezone handling

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
    page_icon="🩺",
    layout="wide"
)

st.title("📈 Dashboard - Real-Time Monitoring")
st.markdown(f"Displaying the last {NUM_RESULTS} entries from ThingSpeak Channel ID: {CHANNEL_ID}")

# --- Placeholders for charts and metrics ---
placeholder_accel = st.empty()
placeholder_gyro = st.empty()
placeholder_fall = st.empty()
placeholder_latest = st.empty()
placeholder_df = st.empty()

# --- Auto-Refresh Loop ---
counter = 0
while True:
    counter += 1
    df_data = fetch_thingspeak_data(READ_API_KEY, results=NUM_RESULTS)

    if not df_data.empty:
        # --- Accelerometer Chart ---
        with placeholder_accel.container():
            st.subheader("📊 Accelerometer (mg)")
            accel_fields = [f for f in [FIELD_MAP.get('field1'), FIELD_MAP.get('field2'), FIELD_MAP.get('field3')] if f and f in df_data.columns]
            if accel_fields:
                fig_accel = px.line(df_data, x='created_at', y=accel_fields,
                                    title="Accelerometer Readings Over Time",
                                    labels={'created_at': 'Timestamp', 'value': 'Acceleration (mg)'})
                fig_accel.update_layout(xaxis_title="Timestamp", yaxis_title="Acceleration (mg)")
                st.plotly_chart(fig_accel, use_container_width=True, key=f"accel_chart{counter}")
            else:
                st.warning("Could not find accelerometer data (fields 1, 2, 3).")

        # --- Gyroscope Chart ---
        with placeholder_gyro.container():
            st.subheader("🌀 Gyroscope")
            gyro_fields = [f for f in [FIELD_MAP.get('field4'), FIELD_MAP.get('field5'), FIELD_MAP.get('field6')] if f and f in df_data.columns]
            if gyro_fields:
                fig_gyro = px.line(df_data, x='created_at', y=gyro_fields,
                                   title="Gyroscope Readings Over Time",
                                   labels={'created_at': 'Timestamp', 'value': 'Angular Velocity'}) # Adjust unit label if needed
                fig_gyro.update_layout(xaxis_title="Timestamp", yaxis_title="Angular Velocity")
                st.plotly_chart(fig_gyro, use_container_width=True, key=f"gyro_chart{counter}")
            else:
                 st.warning("Could not find gyroscope data (fields 4, 5, 6).")

        # --- Fall Detection Indicator ---
        with placeholder_fall.container():
            st.subheader("❗ Fall Detection")
            fall_field = FIELD_MAP.get('field7')
            if fall_field and fall_field in df_data.columns and not df_data[fall_field].isnull().all():
                # Get the latest fall detection status
                latest_fall_status = df_data[fall_field].iloc[-1]
                latest_fall_time = df_data['created_at'].iloc[-1].strftime('%H:%M:%S (%d/%m/%Y)')

                if latest_fall_status == 1:
                    st.error(f"🔴 FALL DETECTED! Last update: {latest_fall_time}", icon="🚨")
                else:
                    st.success(f"✅ No recent falls detected. Last update: {latest_fall_time}", icon="👍")

                # Optional: Show a historical chart of fall detections
                fig_fall = px.line(df_data, x='created_at', y=fall_field, markers=True,
                                    title="Fall Detection History (0 = Normal, 1 = Fall)",
                                    labels={'created_at': 'Timestamp', fall_field: 'Fall Status'})
                fig_fall.update_layout(yaxis=dict(range=[-0.1, 1.1])) # Fix Y-axis between 0 and 1
                st.plotly_chart(fig_fall, use_container_width=True, key=f"fall_chart{counter}")

            else:
                st.warning("Could not find fall detection data (field 7) or all values are null.")

        # --- Display Latest Values ---
        with placeholder_latest.container():
             st.subheader("⏱️ Latest Received Values")
             latest_data = df_data.iloc[-1] # Get the last row
             cols = st.columns(len(FIELD_MAP))
             col_index = 0
             for field_orig, field_name in FIELD_MAP.items():
                 if field_name in latest_data and pd.notna(latest_data[field_name]):
                     # Format value to 2 decimal places if it's a float
                     formatted_value = f"{latest_data[field_name]:.2f}" if isinstance(latest_data[field_name], float) else latest_data[field_name]
                     cols[col_index].metric(label=field_name, value=formatted_value)
                     col_index += 1
                 elif field_name in df_data.columns: # Show N/A if column exists but latest value is null
                      cols[col_index].metric(label=field_name, value="N/A")
                      col_index += 1
                 # If the column doesn't even exist in the dataframe, don't show anything


        # --- Display Raw Data Table (Optional) ---
        with placeholder_df.container():
            st.subheader("📄 Raw Data Table (Latest Entries)")
            # Show relevant columns and reverse order (most recent first)
            display_columns = ['created_at'] + [f for f in FIELD_MAP.values() if f in df_data.columns]
            st.dataframe(df_data[display_columns].iloc[::-1].head(10)) # Show latest 10

    else:
        # Clear placeholders if no data
        placeholder_accel.empty()
        placeholder_gyro.empty()
        placeholder_fall.empty()
        placeholder_latest.empty()
        placeholder_df.empty()
        st.info("Waiting for data from ThingSpeak...")


    # --- Wait before the next refresh ---
    time.sleep(REFRESH_INTERVAL_SECONDS)