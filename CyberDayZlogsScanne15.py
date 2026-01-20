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
    #MainMenu, header, footer { visibility: hidden; }
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
        width: 100%;
    }
    .stMultiSelect [data-baseweb="tag"] { background-color: #3498db !important; }
    .stDownloadButton > button { background-color: #28a745 !important; border: none !important; }
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

# 5. Core Processing
def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, raw_filtered_lines = {}, []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"
    
    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter", "truck"]
    lifecycle_keys = ["spawned", "despawned", "cleanup", "createtoggle"]

    for content in content_list:
        lines = content.decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            low = line.lower()
            should_process = False
            
            # Simple keyword checks to ensure data is found
            if mode == "Vehicle Lifecycle" and any(k in low for k in lifecycle_keys): should_process = True
            elif mode == "Vehicle Activity" and any(v in low for v in vehicle_keys): should_process = True
            # ... (rest of filtering logic)

            if should_process:
                raw_filtered_lines.append(f"{line.strip()}\n")
                # Grouping for UI expanders
                name = line.split('Player "')[1].split('"')[0] if 'Player "' in line else "Server System"
                if name not in grouped_report: grouped_report[name] = []
                grouped_report[name].append({"text": line.strip()})
    
    return grouped_report, header + "".join(raw_filtered_lines)

# --- SIDEBAR: NITRADO DASHBOARD ---
with st.sidebar:
    st.title("🖥️ Nitrado Dashboard")
    if st.button("🔎 Scan Server"):
        st.session_state.server_files = get_nitrado_file_list()

    if "server_files" in st.session_state:
        adms = [f['name'] for f in st.session_state.server_files if f['type'] == 'ADM']
        rpts = [f['name'] for f in st.session_state.server_files if f['type'] == 'RPT']
        
        st.markdown("### 📥 Select Raw Files")
        selected_raw = st.multiselect("Select files to download manually", adms + rpts)

        if selected_raw:
            for fname in selected_raw:
                fpath = next(f['path'] for f in st.session_state.server_files if f['name'] == fname)
                raw_data = download_file(fpath)
                if raw_data:
                    st.download_button(f"💾 Save Raw: {fname}", data=raw_data, file_name=fname)

        st.divider()
        st.markdown("### ⚡ Quick Sync (For App Filters)")
        if st.button("🚀 Sync Latest Files Only"):
            st.session_state.active_log = []
            # Automatically grab the last file in each category
            for cat in ['ADM', 'RPT']:
                cat_files = [f for f in st.session_state.server_files if f['type'] == cat]
                if cat_files:
                    latest = cat_files[-1]
                    data = download_file(latest['path'])
                    if data: st.session_state.active_log.append(data)
            st.success("Synced latest logs to scanner.")

# --- MAIN INTERFACE ---
st.title("🛡️ CyberDayZ Scanner v27.6")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.subheader("🔍 Local Analysis")
    final_data = st.session_state.get('active_log', [])
    mode = st.selectbox("Search Mode", ["Vehicle Lifecycle", "Vehicle Activity", "Area Activity Search", "Full Activity per Player"])
    
    if final_data and st.button("🚀 Run Analysis"):
        report, raw = filter_logs(final_data, mode)
        st.session_state.results, st.session_state.dl = report, raw

    if "results" in st.session_state and st.session_state.results:
        st.download_button("💾 Export Filtered results (.ADM)", st.session_state.dl, "FILTERED_VIEW.adm")
        for p, events in st.session_state.results.items():
            with st.expander(f"👤 {p}"):
                for e in events: st.write(e['text'])

with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mkey = st.session_state.get('mkey', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mkey',0)}", height=850)
