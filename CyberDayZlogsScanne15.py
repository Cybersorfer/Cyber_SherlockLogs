import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = "YOUR_NITRADO_TOKEN"  # Replace with your actual token
SERVICE_ID = "18159994"
BASE_URL = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- API FUNCTIONS ---
def get_log_files():
    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.get(f"{BASE_URL}/file_server/list?path=dayzps/profiles", headers=headers)
    if response.status_code == 200:
        files = response.json().get('data', {}).get('entries', [])
        return [f['path'] for f in files if f['path'].endswith('.adm')]
    return []

def download_log(file_path):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    params = {'file': file_path}
    response = requests.get(f"{BASE_URL}/file_server/download", headers=headers, params=params)
    if response.status_code == 200:
        download_url = response.json().get('data', {}).get('header', {}).get('url')
        log_content = requests.get(download_url)
        return log_content.text
    return ""

# --- PARSING LOGIC ---
def parse_logs(log_text):
    # Regex for coordinates and player activity
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2}) \| Player "(.*)" \(id=(.*) pos=<(.*)>\)')
    data = []
    for line in log_text.split('\n'):
        match = pattern.search(line)
        if match:
            time, name, uid, pos = match.groups()
            coords = [float(x) for x in pos.split(',')]
            data.append({"Time": time, "Player": name, "UID": uid, "X": coords[0], "Z": coords[2]})
    return pd.DataFrame(data)

# --- UI LAYOUT ---
st.title("🛡️ CyberDayZ Log Scanner v27.9")

with st.sidebar:
    st.header("Server Controls")
    if st.button("Scan Server Logs"):
        logs = get_log_files()
        st.session_state['log_list'] = logs
        st.success(f"Found {len(logs)} .adm files")

    selected_file = st.selectbox("Select Log File", st.session_state.get('log_list', []))

if selected_file:
    raw_data = download_log(selected_file)
    df = parse_logs(raw_data)

    # Area Activity Filter
    st.subheader("📍 Area Activity Search")
    col1, col2 = st.columns(2)
    with col1:
        target_x = st.number_input("Target X", value=0.0)
        radius = st.number_input("Radius (meters)", value=100.0)
    with col2:
        target_z = st.number_input("Target Z", value=0.0)
    
    if not df.empty:
        # Distance calculation
        df['Dist'] = ((df['X'] - target_x)**2 + (df['Z'] - target_z)**2)**0.5
        filtered_df = df[df['Dist'] <= radius]
        
        st.write(f"Found {len(filtered_df)} activities in this area.")
        st.dataframe(filtered_df)
        
        # iZurvive Export
        if st.button("Generate iZurvive Markers"):
            marker_text = ""
            for _, row in filtered_df.iterrows():
                marker_text += f"{row['Player']} at {row['Time']}\n{row['X']} / {row['Z']}\n\n"
            st.text_area("Copy into iZurvive", value=marker_text)
