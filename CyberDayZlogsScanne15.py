import streamlit as st
import io
import math
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 1. Setup Page Config - Force sidebar to be visible on load
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="expanded")

# 2. CSS: Professional Dark UI
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #31333F; }
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        width: 100%;
    }
    .raw-download-btn { background-color: #28a745 !important; margin-bottom: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Nitrado Credentials
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"

# 4. API Functions
def get_nitrado_file_list():
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            entries = response.json().get('data', {}).get('entries', [])
            return [{"name": e['name'], "path": e['path'], "type": e['name'].split('.')[-1].upper()} 
                    for e in entries if e['name'].endswith(('.adm', '.rpt', '.log'))]
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

# --- SIDEBAR: NITRADO DASHBOARD ---
with st.sidebar:
    st.title("🖥️ Nitrado Dashboard")
    st.info("Step 1: Scan for files. Step 2: Select and Download Raw.")
    
    if st.button("🔎 Scan Server for Files"):
        st.session_state.server_files = get_nitrado_file_list()

    if "server_files" in st.session_state:
        st.divider()
        st.subheader("📥 Download Raw Logs")
        
        # Filter files by type for easier selection
        file_names = [f['name'] for f in st.session_state.server_files]
        selected_raw_files = st.multiselect("Choose files to save locally:", file_names)

        if selected_raw_files:
            for fname in selected_raw_files:
                fpath = next(f['path'] for f in st.session_state.server_files if f['name'] == fname)
                raw_data = download_file(fpath)
                if raw_data:
                    st.download_button(
                        label=f"💾 Save {fname}",
                        data=raw_data,
                        file_name=fname,
                        mime="text/plain",
                        key=f"dl_{fname}"
                    )
        
        st.divider()
        st.subheader("⚡ App Sync")
        if st.button("🚀 Sync Latest to Scanner"):
            st.session_state.active_log = []
            for cat in ['ADM', 'RPT']:
                cat_files = [f for f in st.session_state.server_files if f['type'] == cat]
                if cat_files:
                    data = download_file(cat_files[-1]['path'])
                    if data: st.session_state.active_log.append(data)
            st.success("Scanner Ready!")

# --- MAIN INTERFACE ---
st.title("🛡️ CyberDayZ Scanner v27.7")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.subheader("🔍 Analysis")
    mode = st.selectbox("Search Mode", ["Vehicle Lifecycle", "Vehicle Activity", "Area Activity Search", "Full Activity per Player"])
    
    # Check if we have data to analyze
    has_data = "active_log" in st.session_state and st.session_state.active_log
    
    if not has_data:
        st.warning("👈 Open the sidebar and Sync files to start analysis.")
    
    if has_data and st.button("🚀 Run Local Filter"):
        # Processing logic goes here
        st.write("Processing data...")

with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mkey = st.session_state.get('mkey', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mkey',0)}", height=850)
