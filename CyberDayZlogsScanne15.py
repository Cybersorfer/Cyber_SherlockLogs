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
    
    if 'mv' not in st.session_state: st.session_state.mv = 0
    if 'all_logs' not in st.session_state: st.session_state.all_logs = []

    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { color: #8b949e !important; }
        div.stButton > button { color: #c9d1d9 !important; background-color: #21262d !important; border: 1px solid #30363d !important; font-weight: bold !important; border-radius: 6px; }
        .death-log { color: #ff7b72 !important; font-weight: bold; border-left: 3px solid #f85149; padding-left: 10px; margin-bottom: 5px; background: #21262d; border-radius: 4px;}
        .raid-log { color: #e3b341 !important; font-weight: bold; border-left: 3px solid #e3b341; padding-left: 10px; margin-bottom: 5px; background: #21262d; }
        </style>
        """, unsafe_allow_html=True)

    FTP_HOST = "usla643.gamedata.io"
    FTP_USER = "ni11109181_1"
    FTP_PASS = "343mhfxd"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=20)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd("/")
            for folder in ["dayzps", "config"]:
                ftp.cwd(folder)
            return ftp
        except: return None

    def extract_dt_from_filename(filename):
        try:
            match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                dt_str = f"{match.group(1)} {match.group(2).replace('-', ':')}"
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except: pass
        return None

    # ==============================================================================
    # SECTION 3: SIDEBAR (NITRADO FTP MANAGER)
    # ==============================================================================
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        st.divider()
        st.header("Nitrado FTP Manager")
        
        sel_dates = st.date_input("Select Date Range:", [datetime.now(), datetime.now()])
        
        hours_list = [time(h, 0) for h in range(24)]
        def format_hour(t): return t.strftime("%I:00%p").lower()

        t_cols = st.columns(2)
        start_t_obj = t_cols[0].selectbox("From:", options=hours_list, format_func=format_hour, index=0)
        end_t_obj = t_cols[1].selectbox("To:", options=hours_list, format_func=format_hour, index=23)
        
        start_date, end_date = (sel_dates[0], sel_dates[1]) if len(sel_dates) == 2 else (sel_dates[0], sel_dates[0])
        global_start_dt = datetime.combine(start_date, start_t_obj).replace(tzinfo=pytz.UTC)
        global_end_dt = datetime.combine(end_date, end_t_obj).replace(hour=end_t_obj.hour, minute=59, second=59, tzinfo=pytz.UTC)

        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True)
        show_rpt = cb_cols[1].checkbox("RPT", True)
        show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True):
            ftp = get_ftp_connection()
            if ftp:
                files_raw = []
                try: ftp.retrlines('MLSD', files_raw.append)
                except: ftp.retrlines('LIST', files_raw.append)
                
                processed = []
                allowed_ext = [ext for ext, s in [(".ADM", show_adm), (".RPT", show_rpt), (".LOG", show_log)] if s]
                
                for line in files_raw:
                    filename = line.split(';')[-1].strip() if ';' in line else line.split()[-1]
                    if any(filename.upper().endswith(ext) for ext in allowed_ext):
                        dt = extract_dt_from_filename(filename)
                        if dt and global_start_dt <= dt <= global_end_dt:
                            disp = f"{filename} ({dt.strftime('%I:%M %p').lower()})"
                            processed.append({"real": filename, "dt": dt, "display": disp})
                
                st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                ftp.quit()
                st.sidebar.success(f"Loaded {len(st.session_state.all_logs)} logs.")

        if st.session_state.all_logs:
            st.divider()
            select_all = st.checkbox("Select All Logs")
            log_options = [f['display'] for f in st.session_state.all_logs]
            selected_disp = st.multiselect("Select Logs:", options=log_options, default=log_options if select_all else None)
            
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                zip_name = f"Logs_{global_start_dt.strftime('%Y-%m-%d_%H%M')}_to_{global_end_dt.strftime('%Y-%m-%d_%H%M')}.zip"
                buf = io.BytesIO()
                ftp_z = get_ftp_connection()
                if ftp_z:
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for disp in selected_disp:
                            real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                            f_data = io.BytesIO()
                            ftp_z.retrbinary(f"RETR {real_name}", f_data.write)
                            zf.writestr(real_name, f_data.getvalue())
                    ftp_z.quit()
                    st.download_button(f"💾 Download {zip_name}", buf.getvalue(), zip_name, use_container_width=True)

    # ==============================================================================
    # SECTION 4: ULTIMATE LOG PROCESSOR (FULLY RESTORED)
    # ==============================================================================
    col1, col2 = st.columns([1.4, 2.3])
    
    with col1:
        st.markdown("### 🛠️ Ultimate Log Processor")
        uploaded_files = st.file_uploader("Drop Logs Here (.ADM, .RPT, .LOG)", accept_multiple_files=True)
        
        if uploaded_files:
            lines = []
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                lines.extend(content.splitlines())
            
            st.divider()
            # Restore Advanced Filtering Interface
            analysis_mode = st.radio("Activity Scanners:", 
                ["Full Activity Log", "Building & Base Activity", "Raid Watch (Explosives)", "Suspicious Activity", "Player Deep Search", "Search by Area"])

            if analysis_mode == "Full Activity Log":
                st.subheader("📋 Full Server Activity")
                # Pattern for basic position logging
                pattern = r"(\d{2}:\d{2}:\d{2}).*?pos=<([\d\.]+), ([\d\.]+), ([\d\.]+)>"
                hits = []
                for line in lines:
                    m = re.search(pattern, line)
                    if m:
                        hits.append({"Time": m.group(1), "X": float(m.group(2)), "Z": float(m.group(4)), "Raw": line[:100]+"..."})
                if hits:
                    st.dataframe(pd.DataFrame(hits), use_container_width=True)

            elif analysis_mode == "Building & Base Activity":
                st.subheader("🏗️ Construction & Dismantling")
                # Pattern for building/placing/dismantling
                build_pattern = r"(\d{2}:\d{2}:\d{2}).*?(built|placed|dismantled|destroyed).*?at pos=<([\d\.]+), ([\d\.]+), ([\d\.]+)>"
                build_data = []
                for line in lines:
                    m = re.search(build_pattern, line, re.I)
                    if m:
                        build_data.append({"Time": m.group(1), "Action": m.group(2), "Coord": f"{m.group(3)}, {m.group(5)}", "Full": line})
                if build_data:
                    st.table(pd.DataFrame(build_data)[["Time", "Action", "Coord"]])
                else:
                    st.info("No building activity found.")

            elif analysis_mode == "Raid Watch (Explosives)":
                st.subheader("🧨 Explosive & Raid Item Detection")
                raid_items = ["Explosive", "Plastic Explosive", "Grenade", "Claymore", "Detonator", "Mine", "Satchel"]
                raids_found = [l for l in lines if any(x.lower() in l.lower() for x in raid_items)]
                if raids_found:
                    for r in raids_found[-50:]: 
                        st.markdown(f"<div class='raid-log'>{r}</div>", unsafe_allow_html=True)
                else:
                    st.info("No raid items detected.")

            elif analysis_mode == "Suspicious Activity":
                st.subheader("🚨 Admin & Speed Alerts")
                # Pattern for teleports or admin commands
                sus_keywords = ["admin", "teleport", "speed", "godmode", "banned", "kick"]
                sus_logs = [l for l in lines if any(k in l.lower() for k in sus_keywords)]
                if sus_logs:
                    for s in sus_logs: st.warning(s)
                else:
                    st.info("No admin/suspicious activity found.")

            elif analysis_mode == "Player Deep Search":
                st.subheader("👤 Player Activity Tracker")
                p_query = st.text_input("Enter Player Name or ID:")
                if p_query:
                    results = [l for l in lines if p_query.lower() in l.lower()]
                    if results:
                        st.success(f"Found {len(results)} entries.")
                        st.text_area("Activity Results", "\n".join(results), height=400)
                    else:
                        st.error("No data found for this player.")

            elif analysis_mode == "Search by Area":
                st.subheader("🗺️ Coordinate Radius Search")
                c_cols = st.columns(3)
                target_x = c_cols[0].number_input("X Coord", value=0.0)
                target_z = c_cols[1].number_input("Z Coord", value=0.0)
                radius = c_cols[2].number_input("Radius (m)", value=100)
                
                area_hits = []
                pos_pattern = r"pos=<([\d\.]+), ([\d\.]+), ([\d\.]+)>"
                for line in lines:
                    m = re.search(pos_pattern, line)
                    if m:
                        lx, lz = float(m.group(1)), float(m.group(3))
                        dist = math.sqrt((target_x - lx)**2 + (target_z - lz)**2)
                        if dist <= radius:
                            area_hits.append(line)
                
                if area_hits:
                    st.success(f"Found {len(area_hits)} events in area.")
                    st.text_area("Area Logs", "\n".join(area_hits), height=300)

            if st.button("📍 Update Map Markers"):
                st.session_state.mv += 1

    with col2:
        st.markdown("<h4 style='text-align: center;'>📍 Live Tracking Map</h4>", unsafe_allow_html=True)
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
