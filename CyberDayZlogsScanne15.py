import streamlit as st
import io
import math
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 1. Setup Page Config - Set to 'auto' to ensure the toggle button is handled by Streamlit
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="auto")

# 2. CSS: Professional Dark UI + Layout Fixes
st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Ensure buttons are consistent */
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        width: 100%;
    }
    
    /* Styling for the manual upload area */
    [data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px dashed #4b4b4b;
        border-radius: 12px;
        padding: 10px;
    }

    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Nitrado Credentials
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"

# 4. API & Processing Functions
def get_nitrado_logs():
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json().get('data', {}).get('entries', [])
            return [{"name": f['name'], "path": f['path']} for f in files if f['name'].endswith('.adm')]
    except: return []
    return []

def download_nitrado_file(file_path):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
    try:
        resp = requests.get(url, headers=headers).json()
        download_url = resp.get('data', {}).get('header', {}).get('url')
        if download_url: return requests.get(download_url).content
    except: return None

def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            coords = [float(parts[0]), float(parts[1])] 
    except: pass 
    return str(name), coords

def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, raw_filtered_lines = {}, []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"
    
    all_lines = []
    for content in content_list:
        if content: all_lines.extend(content.decode("utf-8", errors="ignore").splitlines())

    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter", "truck"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    
    for line in all_lines:
        if "|" not in line: continue
        low, (name, coords) = line.lower(), extract_player_and_coords(line)
        should_process = False

        if mode == "Vehicle Activity" and any(v in low for v in vehicle_keys): should_process = True
        elif mode == "Area Activity Search" and coords and area_coords:
            if math.sqrt((coords[0]-area_coords[0])**2 + (coords[1]-area_coords[1])**2) <= area_radius: should_process = True
        elif mode == "Movement + Raid Watch" and ("pos=" in low or any(k in low for k in raid_keys)): should_process = True
        elif mode == "Full Activity per Player" and target_player == name: should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append({"time": line.split(" | ")[0].split("]")[-1].strip(), "text": line.strip(), "link": f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}" if coords else ""})
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- UI STRUCTURE ---

# A. SIDEBAR: Nitrado Connection
with st.sidebar:
    st.title("🔗 Nitrado Sync")
    if st.button("🔄 Sync Files List"):
        st.session_state.files = get_nitrado_logs()

    if "files" in st.session_state and st.session_state.files:
        selected_name = st.selectbox("Select Remote Log", [f['name'] for f in st.session_state.files])
        if st.button("📥 Fetch Remote Log"):
            path = next(f['path'] for f in st.session_state.files if f['name'] == selected_name)
            data = download_nitrado_file(path)
            if data: 
                st.session_state.active_log = [data]
                st.success("Log Synced!")

# B. MAIN INTERFACE
st.title("🛡️ CyberDayZ Scanner v27.1")

col1, col2 = st.columns([1, 2.3])

with col1:
    # 1. Manual Upload Section (Always Visible)
    st.subheader("📂 1. Load Data")
    manual_files = st.file_uploader("Upload .ADM logs manually", accept_multiple_files=True)
    
    # Logic to combine Nitrado data and Manual data
    final_data = st.session_state.get('active_log', [])
    if manual_files:
        for f in manual_files: final_data.append(f.read())

    # 2. Filter Section
    st.subheader("🔍 2. Analysis Settings")
    mode = st.selectbox("Search Mode", ["Vehicle Activity", "Area Activity Search", "Full Activity per Player", "Movement + Raid Watch"])
    
    area_coords, area_radius, target_player = None, 500, None
    if mode == "Area Activity Search":
        presets = {"Tisy": [1542, 13915], "NWAF": [4530, 10245], "Zenit": [8355, 5978], "Vybor": [3824, 8912]}
        loc = st.selectbox("Location", list(presets.keys()))
        area_coords, area_radius = presets[loc], st.slider("Radius", 50, 2000, 500)
    
    if final_data and st.button("🚀 Run Analysis"):
        report, raw = filter_logs(final_data, mode, area_coords=area_coords, area_radius=area_radius)
        st.session_state.results, st.session_state.dl = report, raw

    # 3. Results Display
    if "results" in st.session_state:
        st.download_button("💾 Download ADM", st.session_state.dl, "CYBER_SCAN.adm")
        for p, events in st.session_state.results.items():
            with st.expander(f"👤 {p}"):
                for e in events:
                    st.caption(f"🕒 {e['time']}")
                    st.write(e['text'])
                    if e['link']: st.link_button("📍 Map", e['link'])

with col2:
    # 4. Map Section (Always Visible)
    st.subheader("🗺️ 3. iZurvive Live View")
    if st.button("🔄 Refresh Map View"):
        st.session_state.map_key = st.session_state.get('map_key', 0) + 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('map_key', 0)}"
    components.iframe(map_url, height=850, scrolling=True)
