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
    .vehicle-event { color: #3498db; font-weight: bold; border-left: 3px solid #3498db; padding-left: 10px; }
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
            return [{"name": e['name'], "path": e['path']} for e in entries if e['name'].endswith(('.adm', '.rpt'))]
    except Exception as e:
        st.error(f"Failed to reach Nitrado: {e}")
    return []

def download_file(path):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={path}"
    try:
        resp = requests.get(url, headers=headers).json()
        download_url = resp.get('data', {}).get('header', {}).get('url')
        return requests.get(download_url).content
    except: return None

# 5. Core Processing Engine
def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report = {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"
    
    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter", "truck"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    lifecycle_keys = ["spawned", "despawned", "cleanup", "createtoggle"]

    for content in content_list:
        lines = content.decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            low = line.lower()
            name = line.split('Player "')[1].split('"')[0] if 'Player "' in line else "Server System"
            
            # Coordinate Extraction
            coords = None
            if "pos=<" in line:
                try:
                    raw = line.split("pos=<")[1].split(">")[0]
                    parts = [p.strip() for p in raw.split(",")]
                    coords = [float(parts[0]), float(parts[1])]
                except: pass
            
            should_process = False

            if mode == "Vehicle Lifecycle":
                if any(k in low for k in lifecycle_keys): should_process = True
            elif mode == "Vehicle Activity":
                if any(v in low for v in vehicle_keys): should_process = True
            elif mode == "Area Activity Search" and coords and area_coords:
                dist = math.sqrt((coords[0]-area_coords[0])**2 + (coords[1]-area_coords[1])**2)
                if dist <= area_radius: should_process = True
            elif mode == "Movement + Raid Watch":
                if "pos=" in low or any(k in low for k in raid_keys): should_process = True
            elif mode == "Full Activity per Player" and target_player and target_player in line:
                should_process = True

            if should_process:
                raw_filtered_lines.append(f"{line.strip()}\n")
                time_val = line.split("|")[0].strip() if "|" in line else "System"
                if name not in grouped_report: grouped_report[name] = []
                grouped_report[name].append({
                    "time": time_val, 
                    "text": line.strip(), 
                    "link": f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}" if coords else None
                })
    
    return grouped_report, header + "".join(raw_filtered_lines)

# --- SIDEBAR: NITRADO FILE BROWSER ---
with st.sidebar:
    st.title("🔗 Nitrado File Browser")
    if st.button("🔎 1. Scan Nitrado Server"):
        files = get_nitrado_file_list()
        st.session_state.server_files = files
        st.success(f"Found {len(files)} logs!")

    if "server_files" in st.session_state:
        st.divider()
        file_options = [f['name'] for f in st.session_state.server_files]
        
        # Select All Toggle
        select_all = st.checkbox("Select All Files")
        if select_all:
            selected_filenames = st.multiselect("Select Logs", file_options, default=file_options)
        else:
            selected_filenames = st.multiselect("Select Logs", file_options)
        
        if st.button("📥 2. Download Selected"):
            with st.spinner("Downloading..."):
                st.session_state.active_log = []
                for fname in selected_filenames:
                    fpath = next(f['path'] for f in st.session_state.server_files if f['name'] == fname)
                    data = download_file(fpath)
                    if data: st.session_state.active_log.append(data)
                st.success(f"Synced {len(st.session_state.active_log)} files to memory.")

    if st.button("🗑️ Clear Local Session"):
        st.session_state.clear()
        st.rerun()

# --- MAIN INTERFACE ---
st.title("🛡️ CyberDayZ Scanner v27.4")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.subheader("📂 Data Source")
    manual = st.file_uploader("Optional: Add local logs", accept_multiple_files=True)
    
    # Merge Nitrado + Manual
    final_data = st.session_state.get('active_log', [])
    if manual:
        for f in manual: final_data.append(f.read())

    st.subheader("🔍 Analysis Settings")
    mode = st.selectbox("Search Mode", ["Vehicle Lifecycle", "Vehicle Activity", "Area Activity Search", "Full Activity per Player", "Movement + Raid Watch"])
    
    area_coords = None
    if mode == "Area Activity Search":
        presets = {"Tisy": [1542, 13915], "NWAF": [4530, 10245], "Zenit": [8355, 5978], "Vybor": [3824, 8912]}
        loc = st.selectbox("Quick Location", list(presets.keys()))
        area_coords = presets[loc]
        area_radius = st.slider("Radius (Meters)", 50, 2000, 500)

    if final_data and st.button("🚀 Process & Generate ADM"):
        report, raw = filter_logs(final_data, mode, area_coords=area_coords, area_radius=area_radius if mode == "Area Activity Search" else 500)
        st.session_state.results = report
        st.session_state.dl = raw

    if "results" in st.session_state:
        st.download_button("💾 Download Filtered ADM", st.session_state.dl, "CYBER_SCAN_RESULTS.adm")
        for p, events in st.session_state.results.items():
            with st.expander(f"👤 {p}"):
                for e in events:
                    st.caption(f"🕒 {e['time']}")
                    st.write(e['text'])
                    if e['link']: st.link_button("📍 Map", e['link'])

with col2:
    st.subheader("🗺️ iZurvive Live View")
    if st.button("🔄 Refresh Map"): st.session_state.mkey = st.session_state.get('mkey', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mkey',0)}", height=850)
