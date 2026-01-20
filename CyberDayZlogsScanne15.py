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
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Nitrado Credentials
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"

# 4. API Functions (Refined for stability)
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
        if download_url:
            return requests.get(download_url).content
    except: return None
    return None

# 5. Core Processing (StopIteration Fix)
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

def filter_logs(content_list, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report = {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for content in content_list:
        if content:
            all_lines.extend(content.decode("utf-8", errors="ignore").splitlines())

    # Keywords
    vehicle_keys = ["vehicle", "carscript", "v3s", "ada", "olga", "gunter", "truck"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    placement_keys = ["placed", "built", "built base"]
    
    for line in all_lines:
        if "|" not in line: continue
        low = line.lower()
        
        # Safely split time
        parts = line.split(" | ")
        time_part = parts[0].split("]")[-1].strip() if len(parts) > 0 else "00:00:00"
        
        name, coords = extract_player_and_coords(line)
        should_process = False

        # SAFE MODE LOGIC
        if mode == "Vehicle Activity":
            if any(v in low for v in vehicle_keys): should_process = True
        elif mode == "Area Activity Search" and coords and area_coords:
            dist = math.sqrt((coords[0]-area_coords[0])**2 + (coords[1]-area_coords[1])**2)
            if dist <= area_radius: should_process = True
        elif mode == "Movement + Raid Watch":
            if "pos=" in low or any(k in low for k in raid_keys):
                should_process = True
        elif mode == "Full Activity per Player" and target_player == name:
            should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            link = f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}" if coords else ""
            
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append({"time": time_part, "text": line.strip(), "link": link})
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- UI ---
st.sidebar.title("Nitrado Sync")
if st.sidebar.button("🔄 Sync Files"):
    st.session_state.files = get_nitrado_logs()

# Fix for potential StopIteration in the selectbox search
if "files" in st.session_state and st.session_state.files:
    file_names = [f['name'] for f in st.session_state.files]
    selected_name = st.sidebar.selectbox("Select Log", file_names)
    
    if st.sidebar.button("📥 Fetch & Analyze"):
        # Safe way to find the path without using next()
        target_path = None
        for f in st.session_state.files:
            if f['name'] == selected_name:
                target_path = f['path']
                break
        
        if target_path:
            data = download_nitrado_file(target_path)
            if data: 
                st.session_state.current_data = [data]
                st.sidebar.success("Log Loaded!")

st.title("🛡️ CyberDayZ Scanner v27.0")
col1, col2 = st.columns([1, 2.3])

with col1:
    mode = st.selectbox("Search Mode", ["Vehicle Activity", "Area Activity Search", "Full Activity per Player", "Movement + Raid Watch"])
    
    area_coords, area_radius, target_player = None, 500, None
    
    if mode == "Area Activity Search":
        presets = {"Tisy": [1542, 13915], "NWAF": [4530, 10245], "Zenit": [8355, 5978], "Vybor": [3824, 8912]}
        loc = st.selectbox("Location", list(presets.keys()))
        area_coords = presets[loc]
        area_radius = st.slider("Radius", 50, 2000, 500)

    if "current_data" in st.session_state and st.button("🚀 Run"):
        report, raw = filter_logs(st.session_state.current_data, mode, area_coords=area_coords, area_radius=area_radius)
        st.session_state.results, st.session_state.dl = report, raw

    if "results" in st.session_state:
        st.download_button("💾 Download ADM", st.session_state.dl, "FILTERED_LOGS.adm")
        for p, events in st.session_state.results.items():
            with st.expander(f"👤 {p}"):
                for e in events:
                    st.caption(f"🕒 {e['time']}")
                    st.write(e['text'])
                    if e['link']: st.link_button("📍 Map", e['link'])

with col2:
    components.iframe("https://www.izurvive.com/serverlogs/", height=800)
