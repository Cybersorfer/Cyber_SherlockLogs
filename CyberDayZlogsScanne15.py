import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
import requests
from datetime import datetime, timedelta, time
import pytz 
import streamlit.components.v1 as components
import json

# ==============================================================================
# SECTION 1: TEAM ACCESS CONTROL
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
    u_in = st.text_input("Username")
    p_in = st.text_input("Password", type="password")
    if st.button("Login"):
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
            st.rerun()
        else:
            st.error("❌ Invalid Credentials")
    return False

if check_password():
    # ==============================================================================
    # SECTION 2: GLOBAL CONFIG & THEME
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
    
    # Initialize Session States
    if 'mv' not in st.session_state: st.session_state.mv = 0
    if 'track_data' not in st.session_state: st.session_state.track_data = None
    if 'map_click_x' not in st.session_state: st.session_state.map_click_x = 1542.0
    if 'map_click_y' not in st.session_state: st.session_state.map_click_y = 13915.0
    if 'all_logs' not in st.session_state: st.session_state.all_logs = []

    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { color: #8b949e !important; }
        div.stButton > button { color: #c9d1d9 !important; background-color: #21262d !important; border: 1px solid #30363d !important; font-weight: bold !important; border-radius: 6px; }
        .death-log { color: #ff7b72 !important; font-weight: bold; border-left: 3px solid #f85149; padding-left: 10px; margin-bottom: 5px;}
        .connect-log { color: #3fb950 !important; border-left: 3px solid #3fb950; padding-left: 10px; margin-bottom: 5px;}
        div[data-testid="stExpander"] { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px; }
        </style>
        """, unsafe_allow_html=True)

    # FTP / API Config
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"
    SERVER_TZ = pytz.timezone('America/Los_Angeles')

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=15)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd(FTP_PATH)
            return ftp
        except Exception as e:
            st.error(f"FTP Error: {e}")
            return None

    def extract_dt_from_filename(filename):
        try:
            match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                date_part = match.group(1)
                time_part = match.group(2).replace('-', ':')
                return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except: pass
        return None

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

    def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
        grouped_report, raw_filtered_lines = {}, []
        all_lines = []
        log_start_header = ""
        
        for uploaded_file in files:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
            if not log_start_header and content:
                for first_lines in content[:5]:
                    if "AdminLog started on" in first_lines:
                        log_start_header = first_lines.strip()
                        break
            all_lines.extend(content)

        building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
        raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
        session_keys = ["connected", "disconnected", "died", "killed"]

        for line in all_lines:
            if "|" not in line: continue
            time_part = line.split(" | ")[0]
            clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
            name, coords = extract_player_and_coords(line)
            low, should_process = line.lower(), False

            if mode == "Full Activity per Player" and target_player == name: should_process = True
            elif mode == "Building Only (Global)" and any(k in low for k in building_keys): should_process = True
            elif mode == "Raid Watch (Global)" and any(k in low for k in raid_keys): should_process = True
            elif mode == "Session Tracking (Global)" and any(k in low for k in session_keys): should_process = True
            elif mode == "Area Activity Search" and coords and area_coords and math.sqrt((coords[0]-area_coords[0])**2 + (coords[1]-area_coords[1])**2) <= area_radius: should_process = True

            if should_process:
                raw_filtered_lines.append(f"{line.strip()}\n")
                status = "death" if any(d in low for d in ["died", "killed"]) else ("connect" if "connect" in low else "normal")
                event_entry = {"time": clean_time, "text": str(line.strip()), "link": f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}" if coords else "", "status": status}
                if name not in grouped_report: grouped_report[name] = []
                grouped_report[name].append(event_entry)

        final_raw = f"{log_start_header}\n" + "".join(raw_filtered_lines) if log_start_header else "".join(raw_filtered_lines)
        return grouped_report, final_raw

    # ==============================================================================
    # SECTION 3: SIDEBAR (FTP LOGIC)
    # ==============================================================================
    with st.sidebar:
        c_logout, c_title = st.columns([1, 2])
        if c_logout.button("🔌 Out"):
            st.session_state["password_correct"] = False
            st.rerun()
        c_title.markdown("### 🐺 Admin")
        
        # Dual Clocks
        components.html("""
        <div style="display: flex; gap: 5px; margin-bottom: 5px; margin-top: -10px;">
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 2px; flex: 1; text-align: center;">
                <div style="color: #8b949e; font-size: 0.5rem; font-weight: bold;">SERVER (LA)</div>
                <div id="server-clock" style="color: #58a6ff; font-size: 1.15rem; font-family: monospace; font-weight: bold;">--:--</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 2px; flex: 1; text-align: center;">
                <div style="color: #8b949e; font-size: 0.5rem; font-weight: bold;">DEVICE</div>
                <div id="device-clock" style="color: #3fb950; font-size: 1.15rem; font-family: monospace; font-weight: bold;">--:--</div>
            </div>
        </div>
        <script>
            function updateClocks() {
                const now = new Date();
                const sOpt = { timeZone: 'America/Los_Angeles', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
                document.getElementById('server-clock').innerText = new Intl.DateTimeFormat('en-GB', sOpt).format(now);
                document.getElementById('device-clock').innerText = now.toLocaleTimeString('en-GB', {hour12: false});
            }
            setInterval(updateClocks, 1000); updateClocks();
        </script>
        """, height=55)

        st.divider()
        st.header("Nitrado FTP Manager")
        
        range_mode = st.selectbox("Range Mode:", ["Today", "Last 24h", "Calendar & Time Range", "All Time"])
        f_start, f_end = None, None
        if range_mode == "Calendar & Time Range":
            d_range = st.date_input("Select Dates", value=[datetime.now().date(), datetime.now().date()])
            h_range = st.slider("Time Range (0:00 - 24:00)", 0, 24, (0, 24))
            if len(d_range) == 2:
                f_start = datetime.combine(d_range[0], time(hour=h_range[0])).replace(tzinfo=pytz.UTC)
                f_end = datetime.combine(d_range[1], time(hour=h_range[1] if h_range[1] < 24 else 23, minute=59)).replace(tzinfo=pytz.UTC)

        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True)
        show_rpt = cb_cols[1].checkbox("RPT", True)
        show_log = cb_cols[2].checkbox("LOG", True)
        
        # --- FIXED SYNC LOGIC ---
        if st.button("🔄 Sync FTP List", use_container_width=True):
            ftp = get_ftp_connection()
            if ftp:
                with st.spinner("Fetching logs..."):
                    files_raw = []
                    ftp.retrlines('MLSD', files_raw.append)
                    processed = []
                    allowed = [ext for ext, s in [(".ADM", show_adm), (".RPT", show_rpt), (".LOG", show_log)] if s]
                    now_utc = datetime.now(pytz.UTC)
                    
                    for line in files_raw:
                        parts = line.split(';')
                        filename = parts[-1].strip()
                        if filename.upper().endswith(tuple(allowed)):
                            dt = extract_dt_from_filename(filename)
                            if not dt:
                                try:
                                    m_str = line.split('modify=')[1].split(';')[0]
                                    dt = datetime.strptime(m_str, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                                except: continue
                            
                            include = True
                            if range_mode == "Today": include = dt.date() == now_utc.date()
                            elif range_mode == "Last 24h": include = dt > (now_utc - timedelta(hours=24))
                            elif range_mode == "Calendar & Time Range" and f_start and f_end:
                                include = f_start <= dt <= f_end
                            
                            if include:
                                disp = f"{filename} ({dt.strftime('%I:%M %p').lower()})"
                                processed.append({"real": filename, "dt": dt, "display": disp})
                    
                    st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                    ftp.quit()
                    st.success(f"Loaded {len(st.session_state.all_logs)} files.")

        # Display selection and ZIP logic OUTSIDE the sync button click block
        if st.session_state.all_logs:
            st.divider()
            selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in st.session_state.all_logs])
            
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with st.spinner("Downloading and Zipping..."):
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for disp in selected_disp:
                                real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                                fbuf = io.BytesIO()
                                ftp.retrbinary(f"RETR {real_name}", fbuf.write)
                                zf.writestr(real_name, fbuf.getvalue())
                        ftp.quit()
                        st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip", use_container_width=True)

    # ==============================================================================
    # SECTION 4: MAIN CONTENT (LOG SCANNER & MAP)
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])

    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        if uploaded_files:
            mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Area Activity Search"])
            
            target_p, area_coords, area_radius = None, None, 500
            if mode == "Full Activity per Player":
                names = set()
                for f in uploaded_files:
                    f.seek(0)
                    names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
                target_p = st.selectbox("Select Player", sorted(list(names)))
            elif mode == "Area Activity Search":
                raw_paste = st.text_input("iSurvive Coords (Paste here)", placeholder="e.g. 4823 / 6129")
                if raw_paste:
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", raw_paste)
                    if len(nums) >= 2:
                        st.session_state.map_click_x, st.session_state.map_click_y = float(nums[0]), float(nums[1])
                cx = st.number_input("X", value=float(st.session_state.map_click_x))
                cy = st.number_input("Y", value=float(st.session_state.map_click_y))
                area_coords, area_radius = [cx, cy], st.slider("Radius (m)", 50, 2000, 500)

            if st.button("🚀 Process Logs", use_container_width=True):
                report, raw = filter_logs(uploaded_files, mode, target_p, area_coords, area_radius)
                st.session_state.track_data, st.session_state.raw_download = report, raw
        
        if st.session_state.get("track_data"):
            st.download_button("💾 Download Filtered ADM", st.session_state.raw_download, "FILTERED.adm", use_container_width=True)
            for p in sorted(st.session_state.track_data.keys()):
                with st.expander(f"👤 {p}"):
                    for ev in st.session_state.track_data[p]:
                        st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)
                        if ev['link']: st.link_button("📍 Map", ev['link'])

    with col2:
        st.markdown("<h4 style='text-align: center;'>📍 iSurvive Serverlogs Map</h4>", unsafe_allow_html=True)
        # Handle Map Coordinates from URL
        p = st.query_params
        if "map_x" in p and "map_y" in p:
            nx, ny = float(p["map_x"]), float(p["map_y"])
            if nx != st.session_state.map_click_x or ny != st.session_state.map_click_y:
                st.session_state.map_click_x, st.session_state.map_click_y = nx, ny
                st.rerun()
        
        if st.button("🔄 Refresh Map", use_container_width=True): 
            st.session_state.mv += 1
            st.rerun()
        
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
