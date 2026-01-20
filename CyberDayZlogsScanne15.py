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
        padding: 0.75rem 1rem !important;
        width: 100%;
    }
    [data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px dashed #4b4b4b;
        border-radius: 15px;
        padding: 10px;
    }
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Automated Nitrado Logic
# Using your provided credentials
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"

def get_nitrado_logs():
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    # Standard path for DayZ PS4 logs on Nitrado
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json().get('data', {}).get('entries', [])
            # Prioritize .adm logs for activity tracking
            return [{"name": f['name'], "path": f['path']} for f in files if f['name'].endswith('.adm')]
    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")
    return []

def download_nitrado_file(file_path):
    headers = {'Authorization': f'Bearer {NITRADO_TOKEN}'}
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            download_url = resp.json().get('data', {}).get('header', {}).get('url')
            file_data = requests.get(download_url)
            return file_data.content
    except: pass
    return None

# 4. Core Processing Functions
def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: 
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            coords = [float(parts[0]), float(parts[1])] 
    except: pass 
    return str(name), coords

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# 5. Filter Logic
def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, player_positions = {}, {}
    raw_filtered_lines = []
    # Standardized Header for iZurvive compatibility
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for content in content_list:
        all_lines.extend(content.decode("utf-8", errors="ignore").splitlines())

    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter", "bus", "truck"]
    
    for line in all_lines:
        if "|" not in line: continue
        time_part = line.split(" | ")[0]
        clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords: player_positions[name] = coords
        low = line.lower()
        should_process = False

        if mode == "Vehicle Activity":
            if any(v in low for v in vehicle_keys): should_process = True
        elif mode == "Area Activity Search":
            if coords and area_coords:
                if calculate_distance(coords, area_coords) <= area_radius: should_process = True
        elif mode == "Full Activity per Player":
            if target_player == name: should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            link = make_izurvive_link(coords) if coords else ""
            event_entry = {"time": clean_time, "text": str(line.strip()), "link": link, "status": "normal"}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

def make_izurvive_link(coords):
    return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"

# --- USER INTERFACE ---
st.sidebar.header("📡 Live Nitrado Link")
if st.sidebar.button("🔄 Sync with Server"):
    st.session_state.remote_logs = get_nitrado_logs()

log_contents = []

if "remote_logs" in st.session_state and st.session_state.remote_logs:
    selected = st.sidebar.selectbox("Select Log File", [f['name'] for f in st.session_state.remote_logs])
    if st.sidebar.button("🚀 Fetch & Scan"):
        path = next(f['path'] for f in st.session_state.remote_logs if f['name'] == selected)
        data = download_nitrado_file(path)
        if data: log_contents.append(data)
        st.success(f"Loaded {selected}")

st.markdown("#### 🛡️ CyberDayZ Scanner v26.8")
col1, col2 = st.columns([1, 2.3])

with col1:
    mode = st.selectbox("Select Filter", ["Vehicle Activity", "Area Activity Search", "Full Activity per Player", "Suspicious Boosting Activity"])
    
    area_coords = None
    area_radius = 500
    if mode == "Area Activity Search":
        presets = {
            "Tisy Military": [1542.0, 13915.0],
            "NWAF": [4530.0, 10245.0],
            "Radio Zenit": [8355.0, 5978.0],
            "Vybor Military": [3824.0, 8912.0]
        }
        loc = st.selectbox("Quick Locations", list(presets.keys()))
        area_coords = presets[loc]
        area_radius = st.slider("Radius (Meters)", 50, 2000, 500)

    if log_contents and st.button("🔍 Run Analysis"):
        report, raw_file = filter_logs(log_contents, mode, area_coords=area_coords, area_radius=area_radius)
        st.session_state.track_data = report
        st.session_state.raw_download = raw_file

    if "track_data" in st.session_state and st.session_state.track_data:
        st.download_button("💾 Download .ADM", data=st.session_state.raw_download, file_name="NITRADO_FILTER.adm")
        for p in sorted(st.session_state.track_data.keys()):
            with st.expander(f"👤 {p}"):
                for ev in st.session_state.track_data[p]:
                    st.caption(f"🕒 {ev['time']}")
                    st.write(ev['text'])
                    if ev['link']: st.link_button("📍 Map", ev['link'])

with col2:
    components.iframe("https://www.izurvive.com/serverlogs/", height=800, scrolling=True)
