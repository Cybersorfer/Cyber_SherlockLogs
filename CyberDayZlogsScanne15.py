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
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    def password_entered():
        u_in = st.session_state.get("username", "")
        p_in = st.session_state.get("password", "")
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
        else:
            st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.subheader("🛡️ CyberDayZ Team Portal")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        if "password_correct" in st.session_state and st.session_state["username"] != "":
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
        .live-log { color: #00d4ff !important; font-family: monospace; font-size: 0.85rem; background: #00000033; padding: 2px 5px; border-radius: 4px; margin-bottom: 2px;}
        </style>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # SECTION 3: 🐺 NITRADO FTP MANAGER
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd(FTP_PATH)
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
                    keep = True
                    if days_back and m_time < (now - timedelta(days=days_back)): keep = False
                    if not (start_hour <= m_time.hour <= end_hour): keep = False
                    if keep:
                        d_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                        processed_files.append({"real": filename, "display": d_name, "time": m_time})
            st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
            ftp.quit()

    def fetch_live_activity():
        ftp = get_ftp_connection()
        if not ftp: return ["Error: FTP Connection Failed"]
        files = []
        ftp.retrlines('NLST', files.append)
        target_file = next((f for f in sorted(files, reverse=True) if f.endswith(".ADM")), None)
        if not target_file:
            ftp.quit()
            return ["Error: No active .ADM log found"]
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {target_file}", buf.write)
        ftp.quit()
        lines = buf.getvalue().decode("utf-8", errors="ignore").splitlines()
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        live_events = []
        for line in lines:
            if " | " not in line: continue
            try:
                time_str = line.split(" | ")[0].split("]")[-1].strip()
                log_time = datetime.strptime(time_str, "%H:%M:%S").replace(year=now.year, month=now.month, day=now.day)
                if log_time >= hour_ago: live_events.append(line.strip())
            except: continue
        return live_events[::-1]

    # ==============================================================================
    # SECTION 4: CORE FUNCTIONS
    # ==============================================================================
    def make_izurvive_link(coords):
        if coords and len(coords) >= 2: return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
        return ""

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

    def calculate_distance(p1, p2):
        if not p1 or not p2: return 999999
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    # ==============================================================================
    # SECTION 5: ADVANCED LOG FILTERING
    # ==============================================================================
    def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
        grouped_report, player_positions, boosting_tracker = {}, {}, {}
        raw_filtered_lines = []
        header = "******************************************************************************\nAdminLog Filtered Report\n\n"
        all_lines = []
        for uploaded_file in files:
            uploaded_file.seek(0)
            all_lines.extend(uploaded_file.read().decode("utf-8", errors="ignore").splitlines())

        building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
        raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
        session_keys = ["connected", "disconnected", "died", "killed"]

        for line in all_lines:
            if "|" not in line: continue
            time_part = line.split(" | ")[0]
            clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
            name, coords = extract_player_and_coords(line)
            low, should_process = line.lower(), False

            if mode == "Full Activity per Player":
                if target_player == name: should_process = True
            elif mode == "Building Only (Global)":
                if any(k in low for k in building_keys): should_process = True
            elif mode == "Raid Watch (Global)":
                if any(k in low for k in raid_keys): should_process = True
            elif mode == "Session Tracking (Global)":
                if any(k in low for k in session_keys): should_process = True
            elif mode == "Area Activity Search":
                if coords and area_coords and calculate_distance(coords, area_coords) <= area_radius: should_process = True

            if should_process:
                raw_filtered_lines.append(f"{line.strip()}\n") 
                status = "death" if any(d in low for d in ["died", "killed"]) else ("connect" if "connect" in low else "normal")
                event_entry = {"time": clean_time, "text": str(line.strip()), "link": make_izurvive_link(coords), "status": status}
                if name not in grouped_report: grouped_report[name] = []
                grouped_report[name].append(event_entry)
        
        return grouped_report, header + "\n".join(raw_filtered_lines)

    # ==============================================================================
    # SECTION 6: UI LAYOUT & SIDEBAR (FIXED INDENTATION)
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Console")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        if st.button("🔌 Log Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()

        st.subheader("🔥 Live activity (Past 1hr)")
        
        def get_server_now():
            ftp = get_ftp_connection()
            if ftp:
                files_data = []
                ftp.retrlines('MLSD', files_data.append)
                adm_files = [line for line in files_data if line.split(';')[-1].strip().upper().endswith('.ADM')]
                if adm_files:
                    latest = sorted(adm_files, key=lambda x: {p.split('=')[0]: p.split('=')[1] for p in x.split(';') if '=' in p}['modify'])[-1]
                    info = {p.split('=')[0]: p.split('=')[1] for p in latest.split(';') if '=' in p}
                    server_time = datetime.strptime(info['modify'], "%Y%m%d%H%M%S")
                    ftp.quit()
                    return server_time.strftime("%H:%M:%S")
            if ftp: ftp.quit()
            return "Syncing..."

        t_col1, t_col2 = st.columns(2)
        t_col1.metric("Server Time", get_server_now())
        t_col2.metric("My Time Zone", datetime.now().strftime("%H:%M:%S"))

        if st.button("📡 Scan Live Log"):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=300):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()

        if st.session_state['current_user'] in ["cybersorfer", "Admin"]:
            with st.expander("🛡️ Security Audit"):
                try:
                    with open("login_history.txt", "r") as f: st.text_area("Audit Log", f.read(), height=200)
                except: st.write("No logs yet.")

        st.header("Nitrado FTP Manager")
        days_opt = {"Today": 0, "Last 24h": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All Time": None}
        sel_days = st.selectbox("Search Range:", list(days_opt.keys()))
        hr_range = st.slider("Hour Frame (24h)", 0, 23, (0, 23))
        
        if st.button("🔄 Sync FTP List"): 
            fetch_ftp_logs(days_opt[sel_days], hr_range[0], hr_range[1])
            st.rerun()
        
        if 'all_logs' in st.session_state:
            filtered_list = [f for f in st.session_state.all_logs]
            selected_disp = st.multiselect("Select Files for ZIP:", options=[f['display'] for f in filtered_list])
            if selected_disp and st.button("📦 Prepare ZIP"):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with zipfile.ZipFile(buf, "w") as zf:
                        for disp in selected_disp:
                            real = next(f['real'] for f in filtered_list if f['display'] == disp)
                            fbuf = io.BytesIO(); ftp.retrbinary(f"RETR {real}", fbuf.write); zf.writestr(real, fbuf.getvalue())
                    ftp.quit(); st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip")

    # ==============================================================================
    # MAIN PAGE CONTENT
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])
    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        if uploaded_files:
            mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Area Activity Search"])
            t_p, area_coords, area_radius = None, None, 500
            
            if mode == "Full Activity per Player":
                all_names = []
                for f in uploaded_files:
                    f.seek(0)
                    all_names.extend([l.split('"')[1] for l in f.read().decode("utf-8", errors="ignore").splitlines() if 'Player "' in l])
                t_p = st.selectbox("Select Player", sorted(list(set(all_names))))
            elif mode == "Area Activity Search":
                cx = st.number_input("Center X", value=1542.0)
                cy = st.number_input("Center Y", value=13915.0)
                area_coords = [cx, cy]
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
