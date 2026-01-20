import streamlit as st
import io
import math
import requests
from datetime import datetime
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="expanded")

# 2. CSS: Professional Dark UI + iOS Fixes
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

# 3. Nitrado API Logic
def get_nitrado_logs(api_token, service_id):
    headers = {'Authorization': f'Bearer {api_token}'}
    # Path to DayZ Admin logs on Nitrado
    url = f"https://api.nitrado.net/services/{service_id}/gameservers/file_server/list?dir=dayzps/config/profiles"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json().get('data', {}).get('entries', [])
            # Filter for .adm files
            return [f['path'] for f in files if f['name'].endswith('.adm')]
    except Exception as e:
        st.error(f"Nitrado Error: {e}")
    return []

def download_nitrado_file(api_token, service_id, file_path):
    headers = {'Authorization': f'Bearer {api_token}'}
    url = f"https://api.nitrado.net/services/{service_id}/gameservers/file_server/download?file={file_path}"
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

def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, player_positions, boosting_tracker = {}, {}, {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for content in content_list:
        all_lines.extend(content.decode("utf-8", errors="ignore").splitlines())

    building_keys = ["placed", "built", "built base", "built wall", "built gate"]
    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter"]

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
            event_entry = {"time": clean_time, "text": str(line.strip()), "status": "normal"}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- USER INTERFACE ---
st.sidebar.header("🔗 Nitrado Connection")
api_key = st.sidebar.text_input("API Token", type="password")
sid = st.sidebar.text_input("Service ID")

log_contents = []

if api_key and sid:
    if st.sidebar.button("Get Remote Logs"):
        available_logs = get_nitrado_logs(api_key, sid)
        st.session_state.remote_files = available_logs

    if "remote_files" in st.session_state:
        selected_file = st.sidebar.selectbox("Select Log", st.session_state.remote_files)
        if st.sidebar.button("Fetch & Scan"):
            data = download_nitrado_file(api_key, sid, selected_file)
            if data: log_contents.append(data)

st.markdown("#### 🛡️ CyberDayZ Scanner v26.7")
col1, col2 = st.columns([1, 2.3])

with col1:
    manual_files = st.file_uploader("Or Upload Manually", accept_multiple_files=True)
    if manual_files:
        for f in manual_files: log_contents.append(f.read())

    if log_contents:
        mode = st.selectbox("Select Filter", ["Vehicle Activity", "Area Activity Search", "Full Activity per Player", "Suspicious Boosting Activity"])
        
        # ... (Previous Logic for target_player and area_coords goes here) ...

        if st.button("🚀 Process"):
            report, raw_file = filter_logs(log_contents, mode)
            st.session_state.track_data = report
            st.session_state.raw_download = raw_file

    # ... (Display Logic) ...

with col2:
    m_url = "https://www.izurvive.com/serverlogs/"
    st.components.v1.iframe(m_url, height=800, scrolling=True)
