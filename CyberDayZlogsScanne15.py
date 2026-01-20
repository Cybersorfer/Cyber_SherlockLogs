import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: GLOBAL PAGE SETUP & THEMING (CSS)
# ==============================================================================
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Global Button & Link Styling */
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        width: 100%;
    }
    
    /* High-Contrast Sidebar (Nitrado Area) */
    section[data-testid="stSidebar"] {
        background-color: #1c2128 !important;
        border-right: 2px solid #30363d;
    }

    /* File Uploader Appearance */
    [data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px dashed #4b4b4b;
        border-radius: 15px;
        padding: 10px;
    }

    /* Responsive Column Handling */
    @media (max-width: 768px) {
        [data-testid="column"] { width: 100% !important; flex: 1 1 auto !important; }
    }

    /* Log Result Color Coding */
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    .disconnect-log { color: #ffc107; border-left: 3px solid #ffc107; padding-left: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# SECTION 2: 🐺 NITRADO FTP MANAGER (LOCKED LOGIC)
# ==============================================================================
FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
        return ftp
    except: return None

def fetch_ftp_logs(f_days=None, s_dt=None, e_dt=None, s_h=0, e_h=23):
    ftp = get_ftp_connection()
    if ftp:
        files_data = []
        ftp.retrlines('MLSD', files_data.append)
        processed_files = []
        valid_ext = ('.ADM', '.RPT', '.LOG')
        now = datetime.now()
        for line in files_data:
            parts = line.split(';')
            info = {p.split('=')[0]: p.split('=')[1] for p in parts if '=' in p}
            filename = parts[-1].strip()
            if filename.upper().endswith(valid_ext):
                m_time = datetime.strptime(info['modify'], "%Y%m%d%H%M%S")
                keep = True
                if f_days and m_time < (now - timedelta(days=f_days)): keep = False
                elif s_dt and e_dt and not (s_dt <= m_time.date() <= e_dt): keep = False
                if not (s_h <= m_time.hour <= e_h): keep = False
                
                if keep:
                    d_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                    processed_files.append({"real": filename, "display": d_name, "time": m_time})
        st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
        ftp.quit()

# ==============================================================================
# SECTION 3: 🛠️ ADVANCED LOG FILTERING (CORE BACKEND)
# ==============================================================================

def make_izurvive_link(coords):
    if coords and len(coords) >= 2:
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return ""

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

def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, player_positions, boosting_tracker = {}, {}, {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for uploaded_file in files:
        uploaded_file.seek(0)
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    session_keys = ["connected", "disconnected", "died", "killed"]
    boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]

    for line in all_lines:
        if "|" not in line: continue
        time_part = line.split(" | ")[0]
        clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords: player_positions[name] = coords
        low = line.lower()
        should_process = False

        if mode == "Full Activity per Player":
            if target_player == name: should_process = True
        elif mode == "Building Only (Global)":
            if any(k in low for k in building_keys) and "pos=" in low: should_process = True
        elif mode == "Raid Watch (Global)":
            if any(k in low for k in raid_keys) and "pos=" in low: should_process = True
        elif mode == "Session Tracking (Global)":
            if any(k in low for k in session_keys): should_process = True
        elif mode == "Area Activity Search":
            if coords and area_coords:
                dist = calculate_distance(coords, area_coords)
                if dist <= area_radius: should_process = True
        elif mode == "Suspicious Boosting Activity":
            try: current_time = datetime.strptime(clean_time, "%H:%M:%S")
            except: continue
            if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                if name not in boosting_tracker: boosting_tracker[name] = []
                boosting_tracker[name].append({"time": current_time, "pos": coords})
                if len(boosting_tracker[name]) >= 3:
                    prev = boosting_tracker[name][-3]
                    time_diff = (current_time - prev["time"]).total_seconds()
                    dist = calculate_distance(coords, prev["pos"])
                    if time_diff <= 300 and dist < 15: should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            link = make_izurvive_link(coords)
            status = "normal"
            if any(d in low for d in ["died", "killed"]): status = "death"
            elif "connect" in low: status = "connect"
            event_entry = {"time": clean_time, "text": str(line.strip()), "link": link, "status": status}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# ==============================================================================
# SECTION 4: USER INTERFACE (SIDEBAR & COLUMNS)
# ==============================================================================

# --- UI ELEMENT: Initialization ---
if "track_data" not in st.session_state: st.session_state.track_data = {}
if "raw_download" not in st.session_state: st.session_state.raw_download = ""

# --- UI ELEMENT: NITRADO FTP MANAGER (SIDEBAR) ---
with st.sidebar:
    st.header("🐺 Nitrado FTP Manager")
    t_mode = st.radio("Time Frame:", ["Quick Select", "Search by Date/Hour"])
    f_days, s_dt, e_dt, s_h, e_h = None, None, None, 0, 23
    
    if t_mode == "Quick Select":
        d_map = {"1 Day": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All": None}
        f_days = d_map[st.selectbox("Select Duration:", list(d_map.keys()))]
    else:
        s_dt, e_dt = st.date_input("Start"), st.date_input("End")
        s_h, e_h = st.slider("Hour Range", 0, 23, (0, 23))

    if st.button("🔄 SYNC FTP SERVER"):
        fetch_ftp_logs(f_days, s_dt, e_dt, s_h, e_h); st.rerun()

    if 'all_logs' in st.session_state:
        st.subheader("Filter File Types:")
        cb_cols = st.columns(3)
        s_adm, s_rpt, s_log = cb_cols[0].checkbox("ADM", True), cb_cols[1].checkbox("RPT", True), cb_cols[2].checkbox("LOG", True)
        
        v_ext = [ext for ext, val in zip([".ADM", ".RPT", ".LOG"], [s_adm, s_rpt, s_log]) if val]
        f_logs = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(v_ext))]
        
        sel_all = st.checkbox("Select All Visible")
        selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in f_logs], default=[f['display'] for f in f_logs] if sel_all else [])
        
        if selected_disp and st.button("📦 PREPARE ZIP"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            if ftp:
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in f_logs if f['display'] == disp)
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {real_name}", buf.write); zf.writestr(real_name, buf.getvalue())
                ftp.quit(); st.download_button("💾 DOWNLOAD ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

# --- UI ELEMENT: DASHBOARD COLUMNS (Filtering & Map) ---
st.markdown("#### 🛡️ CyberDayZ Scanner v26.6")
col1, col2 = st.columns([1, 2.3])

# UI ELEMENT: 🛠️ ADVANCED LOG FILTERING (LEFT PANEL)
with col1:
    uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
    
    if uploaded_files:
        mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
        
        target_player, area_coords, area_radius = None, None, 500
        
        if mode == "Full Activity per Player":
            all_names = []
            for f in uploaded_files:
                f.seek(0)
                content = f.read().decode("utf-8", errors="ignore")
                all_names.extend([line.split('"')[1] for line in content.splitlines() if 'Player "' in line])
            player_list = sorted(list(set(all_names)))
            target_player = st.selectbox("Select Player", player_list)
            
        elif mode == "Area Activity Search":
            presets = {
                "Custom Coordinates": None,
                "Tisy Military": [1542.0, 13915.0],
                "NWAF (North West Airfield)": [4530.0, 10245.0],
                "VMC (Vybor Military)": [3824.0, 8912.0],
                "Vybor (Town Center)": [3785.0, 8925.0],
                "Radio Zenit": [8355.0, 5978.0],
                "Zelenogorsk": [2540.0, 5085.0]
            }
            selection = st.selectbox("Quick Locations", list(presets.keys()))
            
            if selection == "Custom Coordinates":
                cx = st.number_input("Center X", value=1542.0)
                cy = st.number_input("Center Y", value=13915.0)
                area_coords = [cx, cy]
            else:
                area_coords = presets[selection]
                st.write(f"Coords: {area_coords}")
                
            area_radius = st.slider("Search Radius (Meters)", 50, 2000, 500)

        if st.button("🚀 Process Logs"):
            report, raw_file = filter_logs(uploaded_files, mode, target_player, area_coords, area_radius)
            st.session_state.track_data = report
            st.session_state.raw_download = raw_file

    if st.session_state.track_data:
        st.download_button("💾 Download ADM", data=st.session_state.raw_download, file_name="CYBER_LOGS.adm")
        for p in sorted(st.session_state.track_data.keys()):
            with st.expander(f"👤 {p}"):
                for ev in st.session_state.track_data[p]:
                    st.caption(f"🕒 {ev['time']}")
                    st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)
                    if ev['link']: st.link_button("📍 Map", ev['link'])
                    st.divider()

# UI ELEMENT: 📍 iZurvive Map (RIGHT PANEL)
with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=800, scrolling=True)
