import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
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
    with open("login_history.txt", "a") as f:
        f.write(entry)

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
    # SECTION 2: GLOBAL CONFIG & NIGHT THEME (AESTHETICS)
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
    
    if 'mv' not in st.session_state:
        st.session_state.mv = 0

    st.markdown("""
        <style>
        /* Night Theme Backgrounds */
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        
        /* Gray Contrast for Labels/Text */
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { 
            color: #8b949e !important; 
        }

        /* Tactical Night Buttons */
        div.stButton > button {
            color: #c9d1d9 !important;
            background-color: #21262d !important; 
            border: 1px solid #30363d !important;
            font-weight: bold !important;
            border-radius: 6px;
        }
        
        /* Log Formatting */
        .death-log { color: #ff7b72 !important; font-weight: bold; border-left: 3px solid #f85149; padding-left: 10px; margin-bottom: 5px;}
        .live-log { color: #79c0ff !important; font-family: monospace; font-size: 0.85rem; background: #0d1117; border: 1px solid #30363d; padding: 5px; border-radius: 4px; margin-bottom: 2px;}
        </style>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # SECTION 3: NITRADO FTP & LOGIC
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"
    SERVER_TZ = pytz.timezone('America/Los_Angeles')

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=10)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd(FTP_PATH)
            return ftp
        except: return None

    def fetch_live_activity():
        ftp = get_ftp_connection()
        if not ftp: return ["Error: FTP Connection Failed."]
        try:
            files = []
            ftp.retrlines('NLST', files.append)
            adm_files = sorted([f for f in files if f.upper().endswith(".ADM")], reverse=True)
            if not adm_files: return ["Error: No ADM logs found."]
            
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {adm_files[0]}", buf.write)
            ftp.quit()
            
            lines = buf.getvalue().decode("utf-8", errors="ignore").splitlines()
            now_server = datetime.now(SERVER_TZ)
            hour_ago = now_server - timedelta(hours=1)
            
            live_events = []
            for line in lines:
                if " | " not in line: continue
                try:
                    time_str = line.split(" | ")[0].split("]")[-1].strip()
                    log_time = datetime.strptime(time_str, "%H:%M:%S").replace(year=now_server.year, month=now_server.month, day=now_server.day)
                    log_time = SERVER_TZ.localize(log_time)
                    if log_time >= hour_ago: live_events.append(line.strip())
                except: continue
            return live_events[::-1] if live_events else ["No activity in last 60 mins."]
        except: return ["Error scanning logs."]

    # ==============================================================================
    # SECTION 6: UI LAYOUT & SIDEBAR
    # ==============================================================================
    with st.sidebar:
        # LOG OUT TOP LEFT
        col_side_logout, col_side_title = st.columns([1, 2])
        if col_side_logout.button("🔌 Out"):
            st.session_state["password_correct"] = False
            st.rerun()
        col_side_title.markdown("### 🐺 Admin")
        
        st.write(f"Active User: **{st.session_state['current_user']}**")
        st.divider()

        # DUAL LIVE CLOCKS
        dual_clocks_html = """
        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px;">
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">Server (LA)</div>
                <div id="server-clock" style="color: #58a6ff; font-size: 1.4rem; font-family: monospace; font-weight: bold;">--:--:--</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">Device Local</div>
                <div id="device-clock" style="color: #3fb950; font-size: 1.4rem; font-family: monospace; font-weight: bold;">--:--:--</div>
            </div>
        </div>
        <script>
        function updateClocks() {
            const now = new Date();
            const sOpt = { timeZone: 'America/Los_Angeles', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('server-clock').innerText = new Intl.DateTimeFormat('en-GB', sOpt).format(now);
            const lOpt = { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('device-clock').innerText = new Intl.DateTimeFormat('en-GB', lOpt).format(now);
        }
        setInterval(updateClocks, 1000); updateClocks();
        </script>
        """
        components.html(dual_clocks_html, height=155)

        st.subheader("🔥 Live Activity (1hr)")
        if st.button("📡 Scan Live Log", use_container_width=True):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=250):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()

        # RESTORED FTP MANAGER WITH CHECKBOXES
        st.header("Nitrado FTP Manager")
        days_opt = {"Today": 0, "Last 24h": 1, "3 Days": 3, "All Time": None}
        sel_days = st.selectbox("Range:", list(days_opt.keys()))
        
        # Restore missing checkboxes
        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True)
        show_rpt = cb_cols[1].checkbox("RPT", True)
        show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True): 
            ftp = get_ftp_connection()
            if ftp:
                files_data = []
                ftp.retrlines('MLSD', files_data.append)
                processed_files = []
                now = datetime.now(SERVER_TZ)
                
                # Filter logic including checkboxes
                allowed = []
                if show_adm: allowed.append(".ADM")
                if show_rpt: allowed.append(".RPT")
                if show_log: allowed.append(".LOG")
                
                for line in files_data:
                    parts = line.split(';')
                    info = {p.split('=')[0]: p.split('=')[1] for p in parts if '=' in p}
                    filename = parts[-1].strip()
                    if filename.upper().endswith(tuple(allowed)):
                        m_time_utc = datetime.strptime(info['modify'], "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                        m_time = m_time_utc.astimezone(SERVER_TZ)
                        if days_opt[sel_days] is None or m_time >= (now - timedelta(days=days_opt[sel_days])):
                            processed_files.append({"real": filename, "display": f"{filename} ({m_time.strftime('%m/%d %H:%M')})"})
                st.session_state.all_logs = sorted(processed_files, key=lambda x: x['real'], reverse=True)
                ftp.quit()
        
        if 'all_logs' in st.session_state:
            selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in st.session_state.all_logs])
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with zipfile.ZipFile(buf, "w") as zf:
                        for disp in selected_disp:
                            real = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                            fbuf = io.BytesIO(); ftp.retrbinary(f"RETR {real}", fbuf.write); zf.writestr(real, fbuf.getvalue())
                    ftp.quit(); st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip", use_container_width=True)

    # ==============================================================================
    # MAIN PAGE CONTENT
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])
    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        st.file_uploader("Upload Admin Logs", accept_multiple_files=True)

    with col2:
        st.markdown(f"<h4 style='text-align: center;'>📍 iSurvive Live Map</h4>", unsafe_allow_html=True)
        c_map1, c_map2, c_map3 = st.columns([1, 1, 1])
        if c_map2.button("🔄 Refresh Map", use_container_width=True):
            st.session_state.mv += 1
            st.rerun()
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
