import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS: HIGH CONTRAST & BUTTON VISIBILITY ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
    
    /* HIGH CONTRAST SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #1c2128 !important;
        border-right: 2px solid #30363d;
    }

    /* GREEN BUTTON THEME SYNC */
    .stFileUploader label [data-testid="stBaseButton-secondary"], 
    div.stButton > button {
        color: #ffffff !important;
        background-color: #238636 !important; 
        border: 1px solid #2ea043 !important;
        font-weight: bold !important;
        text-transform: uppercase;
        width: 100% !important;
    }
    
    /* LOG ACTIVITY COLORS (SYNCED WITH v14) */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 🐺 NITRADO FTP MANAGER (LOCKED SECTION) ---
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

# --- 4. 🛠️ ADVANCED LOG FILTERING (EXACT SYNC WITH v14-11) ---
def make_izurvive_link(coords):
    if coords and len(coords) >= 2:
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return ""

def extract_v14_data(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: 
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            # FIXED: Index 0 (X) and Index 2 (Z) to match your preset coordinates
            coords = [float(parts[0]), float(parts[2])] 
    except: pass 
    return str(name), coords

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, boosting_tracker = {}, {}
    # Header format synced with version 14-11
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
        name, coords = extract_v14_data(line)
        low, should_process = line.lower(), False

        if mode == "Full Activity per Player":
            if target_player == name: should_process = True
        elif mode == "Building Only (Global)":
            if any(k in low for k in building_keys) and "pos=" in low: should_process = True
        elif mode == "Raid Watch (Global)":
            if any(k in low for k in raid_k) and "pos=" in low: should_process = True
        elif mode == "Session Tracking (Global)":
            if any(k in low for k in session_keys): should_process = True
        elif mode == "Area Activity Search":
            if coords and area_coords:
                if calculate_distance(coords, area_coords) <= area_radius: should_process = True
        elif mode == "Suspicious Boosting Activity":
            try: current_time = datetime.strptime(clean_time, "%H:%M:%S")
            except: continue
            if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                if name not in boosting_tracker: boosting_tracker[name] = []
                boosting_tracker[name].append({"time": current_time, "pos": coords})
                if len(boosting_tracker[name]) >= 3:
                    prev = boosting_tracker[name][-3]
                    if (current_time - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                        should_process = True

        if should_process:
            link = make_izurvive_link(coords)
            status = "death" if any(d in low for d in ["died", "killed"]) else "connect" if "connect" in low else "normal"
            event_entry = {"time": clean_time, "text": str(line.strip()), "link": link, "status": status}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "\n".join([ev['text'] for p in grouped_report for ev in grouped_report[p]])

# --- 5. UI LAYOUT ---
col1, col2 = st.columns([1, 1.4])

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

    if st.button("🔄 SYNC FTP SERVER"): fetch_ftp_logs(f_days, s_dt, e_dt, s_h, e_h); st.rerun()

    if 'all_logs' in st.session_state:
        st.subheader("Filter File Types:")
        cb_cols = st.columns(3)
        s_adm, s_rpt, s_log = cb_cols[0].checkbox("ADM", True), cb_cols[1].checkbox("RPT", True), cb_cols[2].checkbox("LOG", True)
        v_ext = [ext for ext, val in zip([".ADM", ".RPT", ".LOG"], [s_adm, s_rpt, s_log]) if val]
        f_logs = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(v_ext))]
        
        selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in f_logs])
        if selected_disp and st.button("📦 PREPARE ZIP"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            if ftp:
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in f_logs if f['display'] == disp)
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {real_name}", buf.write); zf.writestr(real_name, buf.getvalue())
                ftp.quit(); st.download_button("💾 DOWNLOAD ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

with col1:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
    if uploaded:
        # Landmark list from v14-11
        presets = {
            "Custom Coordinates": None,
            "Tisy Military": [1542.0, 13915.0],
            "NWAF (Airfield)": [4530.0, 10245.0],
            "VMC (Military)": [3824.0, 8912.0],
            "Radio Zenit": [8355.0, 5978.0],
            "Zelenogorsk": [2540.0, 5085.0]
        }
        mode = st.selectbox("Select Filter", ["Full Activity per Player", "Building Only (Global)", "Raid Watch (Global)", "Area Activity Search", "Suspicious Boosting Activity"])
        
        t_player, a_coords, a_radius = None, None, 500
        if mode == "Area Activity Search":
            choice = st.selectbox("Quick Locations", list(presets.keys()))
            if choice == "Custom Coordinates":
                cx = st.number_input("X", value=4500.0)
                cz = st.number_input("Z", value=10000.0)
                a_coords = [cx, cz]
            else:
                a_coords = presets[choice]
            a_radius = st.slider("Radius (Meters)", 50, 2000, 500)
        elif mode == "Full Activity per Player":
            p_names = set()
            for f in uploaded: f.seek(0); p_names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
            t_player = st.selectbox("Select Player", sorted(list(p_names)))

        if st.button("🚀 RUN ANALYSIS"):
            report, raw = filter_logs(uploaded, mode, t_player, a_coords, a_radius)
            if report:
                st.download_button("💾 DOWNLOAD ADM", raw, "FILTERED.adm")
                for p in sorted(report.keys()):
                    with st.expander(f"👤 {p}"):
                        for ev in report[p]: st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)

with col2:
    if st.button("🔄 REFRESH MAP"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
