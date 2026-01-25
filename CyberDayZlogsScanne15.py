import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
import sqlite3
from datetime import datetime, timedelta, time
import pytz 
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: TEAM ACCESS CONTROL (Unchanged)
# ==============================================================================
team_accounts = {
    "cybersorfer": "cyber001",
    "Admin": "cyber001",
    "dirtmcgirrt": "dirt002",
    "TrapTyree": "trap003",
    "CAPTTipsyPants": "cap004"
}

def log_session(user, action):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = st.context.headers.get("X-Forwarded-For", "Unknown/Local")
    entry = f"{now} | User: {user} | Action: {action} | IP: {ip}\n"
    try:
        with open("login_history.txt", "a") as f:
            f.write(entry)
    except: pass

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.subheader("🛡️ CyberDayZ Team Portal")
    u_in = st.text_input("Username", key="login_user")
    p_in = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
            st.rerun()
        else:
            st.error("❌ Invalid Credentials")
    return False

# ==============================================================================
# MAIN APPLICATION BLOCK
# ==============================================================================
if check_password():
    if 'page_configured' not in st.session_state:
        st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
        st.session_state.page_configured = True

    # Session State Initialization
    if 'mv' not in st.session_state: st.session_state.mv = 0
    if 'all_logs' not in st.session_state: st.session_state.all_logs = []
    if 'track_data' not in st.session_state: st.session_state.track_data = {}
    if 'raw_download' not in st.session_state: st.session_state.raw_download = ""
    if 'current_mode' not in st.session_state: st.session_state.current_mode = "Filter"

    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { color: #8b949e !important; }
        div.stButton > button { color: #c9d1d9 !important; background-color: #21262d !important; border: 1px solid #30363d !important; font-weight: bold !important; border-radius: 6px; }
        .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px; background: #2a1212; }
        .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px; background: #122a16; }
        .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px; background: #2a2612; }
        .hotspot-log { color: #00d4ff !important; border-left: 3px solid #00d4ff; padding-left: 10px; margin-bottom: 5px; background: #0e2433; }
        </style>
        """, unsafe_allow_html=True)

    FTP_HOST, FTP_USER, FTP_PASS = "usla643.gamedata.io", "ni11109181_1", "343mhfxd"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=20)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd("/dayzps/config")
            return ftp
        except: return None

    def make_izurvive_link(coords):
        if coords: return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
        return ""

    def extract_player_and_coords(line):
        name, coords = "System/Server", None
        try:
            if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
            if "pos=<" in line:
                raw = line.split("pos=<")[1].split(">")[0]
                parts = [p.strip() for p in raw.split(",")]
                coords = [float(parts[0]), float(parts[2] if len(parts)>2 else parts[1])] 
        except: pass 
        return str(name), coords

    def calculate_distance(p1, p2):
        if not p1 or not p2: return 999999
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    # --- NEW: VEHICLE & BASE TRACKER LOGIC ---
    def process_hotspots(files):
        # Create an in-memory database for fast processing
        db = sqlite3.connect(":memory:")
        cursor = db.cursor()
        cursor.execute("CREATE TABLE records (file TEXT, text TEXT, x REAL, z REAL)")
        
        target_keys = ["Transport", "Placement", "built", "constructed"]
        
        for uploaded_file in files:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            for line in content.splitlines():
                if any(k in line for k in target_keys):
                    name, coords = extract_player_and_coords(line)
                    if coords:
                        cursor.execute("INSERT INTO records VALUES (?, ?, ?, ?)", 
                                       (uploaded_file.name, line.strip()[:100], coords[0], coords[1]))
        
        # Identify coordinates seen in more than one restart/file
        cursor.execute("""
            SELECT x, z, COUNT(DISTINCT file) as count, GROUP_CONCAT(DISTINCT file) 
            FROM records GROUP BY x, z HAVING count > 1 ORDER BY count DESC
        """)
        results = cursor.fetchall()
        
        hotspot_report = {"Hotspots Found": []}
        raw_out = "HOTSPOT REPORT\n================\n"
        for x, z, count, files_list in results:
            entry = {
                "time": f"Seen in {count} logs",
                "text": f"Asset detected at {x}, {z} (Persistent across restarts)",
                "link": make_izurvive_link([x, z]),
                "status": "hotspot"
            }
            hotspot_report["Hotspots Found"].append(entry)
            raw_out += f"COORD: {x}, {z} | Restarts: {count} | Logs: {files_list}\n"
            
        return hotspot_report, raw_out

    def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
        if mode == "Vehicle & Base Tracker":
            return process_hotspots(files)

        grouped_report, boosting_tracker = {}, {}
        raw_filtered_lines = []
        now_str = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
        header = f"******************************************************************************\nAdminLog started on {now_str}\n\n"

        building_keys = ["placed", "built", "constructed", "base", "wall", "gate", "platform", "watchtower"]
        raid_keys = ["dismantled", "folded", "unmount", "destroyed", "packed", "cut"]
        session_keys = ["connected", "disconnected", "died", "killed", "suicide"]
        boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]

        for uploaded_file in files:
            uploaded_file.seek(0)
            lines = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                if "|" not in line: continue
                try:
                    time_part = line.split(" | ")[0]
                    clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
                except: clean_time = "00:00:00"

                name, coords = extract_player_and_coords(line)
                low = line.lower()
                should_process = False

                if mode == "Full Activity per Player":
                    if target_player and target_player == name: should_process = True
                elif mode == "Building Only (Global)":
                    if any(k in low for k in building_keys) and "pos=" in low: should_process = True
                elif mode == "Raid Watch (Global)":
                    if any(k in low for k in raid_keys) and "pos=" in low: should_process = True
                elif mode == "Session Tracking (Global)":
                    if any(k in low for k in session_keys): should_process = True
                elif mode == "Area Activity Search":
                    if coords and area_coords:
                        if calculate_distance(coords, area_coords) <= area_radius: should_process = True
                elif mode == "Suspicious Boosting Activity":
                    try: 
                        curr_t = datetime.strptime(clean_time, "%H:%M:%S")
                        if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                            if name not in boosting_tracker: boosting_tracker[name] = []
                            boosting_tracker[name].append({"time": curr_t, "pos": coords})
                            if len(boosting_tracker[name]) >= 3:
                                prev = boosting_tracker[name][-3]
                                if (curr_t - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                                    should_process = True
                    except: continue

                if should_process:
                    raw_filtered_lines.append(f"{line.strip()}\n")
                    status = "normal"
                    if any(d in low for d in ["died", "killed"]): status = "death"
                    elif "connected" in low: status = "connect"
                    elif "disconnected" in low: status = "disconnect"
                    entry = {"time": clean_time, "text": line.strip(), "link": make_izurvive_link(coords), "status": status}
                    if name not in grouped_report: grouped_report[name] = []
                    grouped_report[name].append(entry)
                    
        return grouped_report, header + "".join(raw_filtered_lines)

    # --- SIDEBAR & FTP (Unchanged) ---
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        st.divider()
        debug_mode = st.toggle("🐞 Debug Mode")
        st.header("Nitrado FTP Manager")
        date_range = st.date_input("Select Date Range:", value=(datetime.now() - timedelta(days=1), datetime.now()))
        hours_list = [time(h, 0) for h in range(24)]
        t_cols = st.columns(2)
        start_t_obj = t_cols[0].selectbox("From:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=0)
        end_t_obj = t_cols[1].selectbox("To:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=23)
        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True); show_rpt = cb_cols[1].checkbox("RPT", True); show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True):
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                ftp = get_ftp_connection()
                if ftp:
                    files_raw = []
                    ftp.retrlines('MLSD', files_raw.append)
                    processed = []
                    start_dt = datetime.combine(start_date, start_t_obj).replace(tzinfo=pytz.UTC)
                    end_dt = datetime.combine(end_date, end_t_obj).replace(hour=end_t_obj.hour, minute=59, second=59, tzinfo=pytz.UTC)
                    for line in files_raw:
                        filename = line.split(';')[-1].strip()
                        exts = ([".ADM"] if show_adm else []) + ([".RPT"] if show_rpt else []) + ([".LOG"] if show_log else [])
                        if any(filename.upper().endswith(e) for e in exts):
                            if 'modify=' in line:
                                m_str = next(p for p in line.split(';') if 'modify=' in p).split('=')[1]
                                try:
                                    dt = datetime.strptime(m_str, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                                    if start_dt <= dt <= end_dt:
                                        processed.append({"real": filename, "dt": dt, "display": f"{filename} ({dt.strftime('%m/%d %I:%M%p')})"})
                                except: continue
                    st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                    ftp.quit()

        if st.session_state.all_logs:
            st.success(f"✅ Found {len(st.session_state.all_logs)} files")
            all_opts = [f['display'] for f in st.session_state.all_logs]
            select_all = st.checkbox("Select All Files")
            selected_disp = st.multiselect("Select Logs:", options=all_opts, default=all_opts if select_all else [])
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp_z = get_ftp_connection()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                        f_data = io.BytesIO(); ftp_z.retrbinary(f"RETR {real_name}", f_data.write)
                        zf.writestr(real_name, f_data.getvalue())
                ftp_z.quit()
                st.download_button("💾 Download ZIP", buf.getvalue(), "cyber_logs.zip", use_container_width=True)

    # --- MAIN DASHBOARD ---
    col1, col2 = st.columns([1, 2.5])
    with col1:
        st.markdown("### 🛠️ Ultimate Log Processor")
        uploaded_files = st.file_uploader("Upload Logs", accept_multiple_files=True)
        if uploaded_files:
            # ADDED NEW MODE HERE
            mode = st.selectbox("Mode", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search", "Vehicle & Base Tracker"])
            st.session_state.current_mode = mode 
            
            t_p, area_coords, area_radius = None, None, 500
            if mode == "Full Activity per Player":
                names = set()
                for f in uploaded_files:
                    f.seek(0)
                    names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
                t_p = st.selectbox("Player", sorted(list(names)))
            
            elif mode == "Area Activity Search":
                presets = {"Custom / Paste": None, "Tisy": [1542, 13915], "NWAF": [4530, 10245], "VMC": [3824, 8912]}
                loc = st.selectbox("Locations", list(presets.keys()))
                if loc == "Custom / Paste":
                    raw_paste = st.text_input("Paste iZurvive Coords (X / Y)", placeholder="10146.06 / 3953.27")
                    if raw_paste and "/" in raw_paste:
                        try:
                            parts = raw_paste.split("/")
                            val_x, val_z = float(parts[0].strip()), float(parts[1].strip())
                        except: val_x, val_z = 0.0, 0.0
                    else:
                        c1, c2 = st.columns(2)
                        val_x, val_z = c1.number_input("X", value=0.0), c2.number_input("Z", value=0.0)
                    area_coords = [val_x, val_z]
                else:
                    area_coords = presets[loc]
                area_radius = st.slider("Radius (Meters)", 50, 5000, 500)
            
            if st.button("🚀 Process Logs", use_container_width=True):
                with st.spinner("Analyzing..."):
                    report, raw = filter_logs(uploaded_files, mode, t_p, area_coords, area_radius)
                    st.session_state.track_data, st.session_state.raw_download = report, raw

        if st.session_state.get("track_data"):
            clean_mode = st.session_state.current_mode.replace(" ", "_")
            file_name = f"{clean_mode}.adm"
            st.download_button(f"💾 Save {file_name}", st.session_state.raw_download, file_name)
            
            for player, events in st.session_state.track_data.items():
                with st.expander(f"👤 {player} ({len(events)} events)"):
                    for ev in events:
                        st.markdown(f"<div class='{ev['status']}-log'>[{ev['time']}] {ev['text']}</div>", unsafe_allow_html=True)
                        if ev['link']: st.link_button("📍 Map", ev['link'])

    with col2:
        if st.button("🔄 Refresh Map"): st.session_state.mv += 1
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=850, scrolling=True)
