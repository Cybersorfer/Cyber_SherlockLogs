import streamlit as st
import io
import math
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="expanded")

# 2. CSS: Professional Dark UI
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
        width: 100%;
    }
    .debug-box { background-color: #1c1c1c; padding: 10px; border-radius: 5px; border: 1px solid #444; font-family: monospace; font-size: 12px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Updated Nitrado Credentials from your Screenshot
# Note: I updated the SERVICE_ID to 18159994 as seen in your browser URL
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994" 

# 4. API Functions with Error Reporting
def get_nitrado_file_list():
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            entries = response.json().get('data', {}).get('entries', [])
            return [{"name": e['name'], "path": e['path'], "type": e['name'].split('.')[-1].upper()} 
                    for e in entries if e['name'].endswith(('.adm', '.rpt', '.log'))]
        else:
            st.sidebar.error(f"Error {response.status_code}: Check if Token/Service ID is correct.")
            return []
    except Exception as e:
        st.sidebar.error(f"Connection Failed: {e}")
        return []

def download_file(path):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={path}"
    try:
        resp = requests.get(url, headers=headers).json()
        download_url = resp.get('data', {}).get('header', {}).get('url')
        return requests.get(download_url).content
    except: return None

# --- SIDEBAR & DASHBOARD ---
with st.sidebar:
    st.title("🖥️ Nitrado Dashboard")
    
    # Debug info to verify we are talking to the right server
    st.write(f"**Target Service ID:** `{SERVICE_ID}`")
    
    if st.button("🔎 Scan Server for Files"):
        with st.spinner("Connecting to Nitrado..."):
            files = get_nitrado_file_list()
            if files:
                st.session_state.server_files = files
                st.success(f"Found {len(files)} files!")
            else:
                st.warning("No files found. Check connection.")

    if "server_files" in st.session_state:
        st.divider()
        file_names = [f['name'] for f in st.session_state.server_files]
        selected_raw = st.multiselect("Choose files to Download Raw:", file_names)

        if selected_raw:
            for fname in selected_raw:
                fpath = next(f['path'] for f in st.session_state.server_files if f['name'] == fname)
                raw_data = download_file(fpath)
                if raw_data:
                    st.download_button(f"💾 Save {fname}", data=raw_data, file_name=fname, key=f"dl_{fname}")

# --- MAIN INTERFACE ---
st.title("🛡️ CyberDayZ Scanner v27.9")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.subheader("🔍 Analysis")
    mode = st.selectbox("Search Mode", ["Vehicle Lifecycle", "Vehicle Activity", "Area Activity Search", "Full Activity per Player"])
    
    if "server_files" in st.session_state:
        if st.button("🚀 Sync Latest Data to Scanner"):
            st.session_state.active_log = []
            # Grabbing latest ADM and RPT
            for cat in ['ADM', 'RPT']:
                cat_files = [f for f in st.session_state.server_files if f['type'] == cat]
                if cat_files:
                    data = download_file(cat_files[-1]['path'])
                    if data: st.session_state.active_log.append(data)
            st.success("Scanner Ready!")
    else:
        st.info("👈 Use the Sidebar to Scan the server first.")

with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mkey = st.session_state.get('mkey', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mkey',0)}", height=850)
