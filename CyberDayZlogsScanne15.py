import streamlit as st
import io
import math
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="auto")

# 2. CSS: Professional Dark UI
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    #MainMenu, header, footer { visibility: hidden; }
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
    }
    .vehicle-event { color: #3498db; font-weight: bold; border-left: 3px solid #3498db; padding-left: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Nitrado Credentials
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"

# 4. API Functions
def get_nitrado_files(extension):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    # Fetching from profiles where .adm and .rpt logs are stored
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            entries = response.json().get('data', {}).get('entries', [])
            return [{"name": e['name'], "path": e['path']} for e in entries if e['name'].endswith(extension)]
    except: return []
    return []

def download_file(path):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={path}"
    try:
        resp = requests.get(url, headers=headers).json()
        download_url = resp.get('data', {}).get('header', {}).get('url')
        return requests.get(download_url).content
    except: return None

# 5. Core Processing for Vehicle Lifecycle
def filter_vehicle_lifecycle(content_list):
    grouped_report = {"Server System": []}
    raw_lines = []
    # Keywords for Spawn, Despawn, and Movement
    lifecycle_keys = ["spawned", "despawned", "cleanup", "vehicle", "carscript", "createtoggle"]
    
    for content in content_list:
        lines = content.decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            low = line.lower()
            if any(k in low for k in lifecycle_keys):
                raw_lines.append(f"{line.strip()}\n")
                # Attempt to extract time and name
                time_val = line.split("|")[0].strip() if "|" in line else "System"
                grouped_report["Server System"].append({"time": time_val, "text": line.strip()})
    
    return grouped_report, "".join(raw_lines)

# --- UI STRUCTURE ---

with st.sidebar:
    st.title("🔗 Nitrado Sync")
    
    # NEW: Specific Vehicle Lifecycle Fetching
    st.subheader("🚗 Vehicle Data")
    if st.button("📥 Fetch Vehicle Lifecycle Log (.RPT)"):
        with st.spinner("Searching server for vehicle data..."):
            rpt_files = get_nitrado_files(".rpt")
            if rpt_files:
                # Get the most recent RPT file
                latest_rpt = rpt_files[-1]
                data = download_file(latest_rpt['path'])
                if data:
                    st.session_state.active_log = [data]
                    st.session_state.force_mode = "Vehicle Lifecycle"
                    st.success(f"Loaded: {latest_rpt['name']}")
            else:
                st.error("No .rpt logs found on server.")

    st.divider()
    if st.button("🔄 Sync Admin Logs (.ADM)"):
        st.session_state.files = get_nitrado_files(".adm")

    if "files" in st.session_state:
        selected = st.selectbox("Select Admin Log", [f['name'] for f in st.session_state.files])
        if st.button("📥 Fetch Admin Log"):
            path = next(f['path'] for f in st.session_state.files if f['name'] == selected)
            data = download_file(path)
            st.session_state.active_log = [data]
            st.success("Admin Log Loaded!")

st.title("🛡️ CyberDayZ Scanner v27.2")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.subheader("📂 Data Control")
    # Manual Upload still available
    manual = st.file_uploader("Upload manual logs", accept_multiple_files=True)
    
    final_data = st.session_state.get('active_log', [])
    if manual:
        for f in manual: final_data.append(f.read())

    st.subheader("🔍 Analysis")
    # Use the forced mode if vehicle lifecycle button was pressed
    default_mode = st.session_state.get("force_mode", "Vehicle Activity")
    mode = st.selectbox("Search Mode", ["Vehicle Lifecycle", "Vehicle Activity", "Area Activity Search", "Full Activity per Player"], index=0 if default_mode == "Vehicle Lifecycle" else 1)
    
    if final_data and st.button("🚀 Run Analysis"):
        if mode == "Vehicle Lifecycle":
            report, raw = filter_vehicle_lifecycle(final_data)
        else:
            # Re-using your existing filter_logs function logic here
            from __main__ import filter_logs # Placeholder for your existing logic
            report, raw = filter_logs(final_data, mode)
            
        st.session_state.results, st.session_state.dl = report, raw

    if "results" in st.session_state:
        st.download_button("💾 Download Lifecycle ADM", st.session_state.dl, "VEHICLE_LIFECYCLE.adm")
        for p, events in st.session_state.results.items():
            with st.expander(f"👤 {p}"):
                for e in events:
                    st.markdown(f"<div class='vehicle-event'>{e['text']}</div>", unsafe_allow_html=True)

with col2:
    st.subheader("🗺️ Live View")
    if st.button("🔄 Refresh Map"): st.session_state.mkey = st.session_state.get('mkey', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mkey',0)}", height=850)
