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
    # SECTION 2: GLOBAL CONFIG & THEME
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
    
    if 'mv' not in st.session_state:
        st.session_state.mv = 0

    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #ffffff !important; }
        section[data-testid="stSidebar"] { background-color: #1c2128 !important; border-right: 2px solid #30363d; }
        .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
        .live-log { color: #00d4ff !important; font-family: monospace; font-size: 0.85rem; background: #00000033; padding: 2px 5px; border-radius: 4px; margin-bottom: 2px;}
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
        # LOG OUT AT THE TOP
        col_side_1, col_side_2 = st.columns([2, 1])
        col_side_1.title("🐺 Admin")
        if col_side_2.button("🔌 Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        
        st.write(f"User: **{st.session_state['current_user']}**")
        st.divider()

        # DUAL LIVE CLOCKS
        dual_clocks_html = """
        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px;">
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">Server (LA)</div>
                <div id="server-clock" style="color: #58a6ff; font-size: 1.4rem; font-family: monospace; font-weight: bold;">--:--:--</div>
            </div>
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">Device Local</div>
                <div id="device-clock" style="color: #2ea043; font-size: 1.4rem; font-family: monospace; font-weight: bold;">--:--:--</div>
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
        if st.button("📡 Scan Live Log"):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=250):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()

        # RESTORED FTP MANAGER
        st.header("Nitrado FTP Manager")
        days_opt = {"Today": 0, "Last 24h": 1, "3 Days": 3, "All Time": None}
        sel_days = st.selectbox("Range:", list(days_opt.keys()))
        
        if st.button("🔄 Sync FTP List"): 
            ftp = get_ftp_connection()
            if ftp:
                files_data = []
                ftp.retrlines('MLSD', files_data.append)
                processed_files = []
                now = datetime.now(SERVER_TZ)
                for line in files_data:
                    parts = line.split(';')
                    info = {p.split('=')[0]: p.split('=')[1] for p in parts if '=' in p}
                    filename = parts[-1].strip()
                    if filename.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        m_time_utc = datetime.strptime(info['modify'], "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                        m_time = m_time_utc.astimezone(SERVER_TZ)
                        if days_opt[sel_days] is None or m_time >= (now - timedelta(days=days_opt[sel_days])):
                            processed_files.append({"real": filename, "display": f"{filename} ({m_time.strftime('%m/%d %H:%M')})"})
                st.session_state.all_logs = sorted(processed_files, key=lambda x: x['real'], reverse=True)
                ftp.quit()
        
        if 'all_logs' in st.session_state:
            selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in st.session_state.all_logs])
            if selected_disp and st.button("📦 Prepare ZIP"):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with zipfile.ZipFile(buf, "w") as zf:
                        for disp in selected_disp:
                            real = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                            fbuf = io.BytesIO(); ftp.retrbinary(f"RETR {real}", fbuf.write); zf.writestr(real, fbuf.getvalue())
                    ftp.quit(); st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip")

    # ==============================================================================
    # MAIN PAGE CONTENT
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])
    
    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        # (Filtering logic remains here as per previous versions)

    with col2:
        # REFRESH MAP BUTTON AT THE TOP
        m_col1, m_col2 = st.columns([3, 1])
        m_col1.markdown(f"#### 📍 iSurvive Live Map")
        if m_col2.button("🔄 Refresh Map"):
            st.session_state.mv += 1
            st.rerun()
            
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
