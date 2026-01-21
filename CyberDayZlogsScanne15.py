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
# SECTION 1: TEAM ACCESS CONTROL & IP TRACKER (THE SHELL)
# ==============================================================================
team_accounts = {
    "cybersorfer": "cyber001",
    "Admin": "cyber001",
    "dirtmcgirrt": "dirt002",
    "TrapTyree": "trap003",
    "CAPTTipsyPants": "cap004"
}

def get_remote_ip():
    try: return st.context.headers.get("X-Forwarded-For", "Unknown/Local")
    except: return "Unknown"

def log_session(user, action):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = get_remote_ip()
    entry = f"{now} | User: {user} | Action: {action} | IP: {ip}\n"
    with open("login_history.txt", "a") as f:
        f.write(entry)

def check_password():
    def password_entered():
        u_in, p_in = st.session_state["username"], st.session_state["password"]
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
            del st.session_state["password"] 
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.subheader("🛡️ CyberDayZ Team Portal")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            st.error("❌ Invalid Credentials")
        return False
    return True

# --- ONLY RUN CORE TOOLS IF LOGGED IN ---
if check_password():

    # ==============================================================================
    # SECTION 2: GLOBAL PAGE SETUP & THEME
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #ffffff !important; }
        label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
        section[data-testid="stSidebar"] { background-color: #1c2128 !important; border-right: 2px solid #30363d; }
        div.stButton > button {
            color: #ffffff !important;
            background-color: #238636 !important; 
            border: 1px solid #2ea043 !important;
            font-weight: bold !important;
            text-transform: uppercase;
            width: 100% !important;
        }
        .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
        .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
        .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
        </style>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # SECTION 3: 🐺 NITRADO FTP MANAGER (ENHANCED WITH TIME FILTERS)
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
            return ftp
        except: return None

    def fetch_ftp_logs(days_back=None, start_hour=0, end_hour=23):
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
                    
                    # Filtering Logic
                    keep = True
                    if days_back and m_time < (now - timedelta(days=days_back)):
                        keep = False
                    if not (start_hour <= m_time.hour <= end_hour):
                        keep = False
                        
                    if keep:
                        d_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                        processed_files.append({"real": filename, "display": d_name, "time": m_time})
            
            st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
            ftp.quit()

    # ==============================================================================
    # SECTION 4: CORE FUNCTIONS (RESTORED AREA SEARCH LOGIC)
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

    # ==============================================================================
    # SECTION 5: 🛠️ ADVANCED LOG FILTERING (EXACT SYNC)
    # ==============================================================================
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
            low, should_process = line.lower(), False

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
    # SECTION 6: UI LAYOUT & SIDEBAR
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Console")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        if st.button("🔌 Log Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()

        if st.session_state['current_user'] in ["cybersorfer", "Admin"]:
            with st.expander("🛡️ Security Audit"):
                try:
                    with open("login_history.txt", "r") as f: st.text_area("Audit Log", f.read(), height=200)
                except: st.write("No logs yet.")

        st.header("Nitrado FTP Manager")
        
        # FEATURE: Days and Hours Filter
        days_opt = {"Today": 0, "Last 24h": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All Time": None}
        sel_days = st.selectbox("Search Range:", list(days_opt.keys()))
        hr_range = st.slider("Hour Frame (24h)", 0, 23, (0, 23))
        
        if st.button("🔄 Sync FTP List"): 
            fetch_ftp_logs(days_opt[sel_days], hr_range[0], hr_range[1])
            st.rerun()
        
        if 'all_logs' in st.session_state:
            st.subheader("Filter File Types:")
            cb_cols = st.columns(3)
            show_adm = cb_cols[0].checkbox("ADM", True)
            show_rpt = cb_cols[1].checkbox("RPT", True)
            show_log = cb_cols[2].checkbox("LOG", True)
            
            allowed_exts = []
            if show_adm: allowed_exts.append(".ADM")
            if show_rpt: allowed_exts.append(".RPT")
            if show_log: allowed_exts.append(".LOG")
            
            filtered_list = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(allowed_exts))]
            select_all = st.checkbox("Select All Visible Files")
            
            selected_disp = st.multiselect(
                "Select Files for ZIP:", 
                options=[f['display'] for f in filtered_list],
                default=[f['display'] for f in filtered_list] if select_all else []
            )
            
            if selected_disp and st.button("📦 Prepare ZIP"):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with zipfile.ZipFile(buf, "w") as zf:
                        for disp in selected_disp:
                            real = next(f['real'] for f in filtered_list if f['display'] == disp)
                            fbuf = io.BytesIO(); ftp.retrbinary(f"RETR {real}", fbuf.write); zf.writestr(real, fbuf.getvalue())
                    ftp.quit(); st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip")

    col1, col2 = st.columns([1, 2.3])
    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        if uploaded_files:
            mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
            t_p, area_coords, area_radius = None, None, 500
            
            if mode == "Full Activity per Player":
                all_names = []
                for f in uploaded_files:
                    f.seek(0)
                    all_names.extend([l.split('"')[1] for l in f.read().decode("utf-8", errors="ignore").splitlines() if 'Player "' in l])
                t_p = st.selectbox("Select Player", sorted(list(set(all_names))))
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
                report, raw = filter_logs(uploaded_files, mode, t_p, area_coords, area_radius)
                st.session_state.track_data = report
                st.session_state.raw_download = raw
        
        if st.session_state.get("track_data"):
            st.download_button("💾 Download Filtered ADM", st.session_state.raw_download, "FILTERED.adm")
            for p in sorted(st.session_state.track_data.keys()):
                with st.expander(f"👤 {p}"):
                    for ev in st.session_state.track_data[p]:
                        st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)
                        if ev['link']: st.link_button("📍 Map", ev['link'])

    with col2:
        if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
