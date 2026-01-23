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
# SECTION 1: TEAM ACCESS CONTROL & IP TRACKER
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
        if "password_correct" in st.session_state and st.session_state.get("username") != "":
            st.error("❌ Invalid Credentials")
        return False
    return True

if check_password():
    # ==============================================================================
    # SECTION 2: GLOBAL CONFIG & SERVER TIMEZONE
    # ==============================================================================
    # Your Nitrado Server is fixed in LA (Pacific)
    SERVER_TZ = pytz.timezone('America/Los_Angeles')

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
            ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
            return ftp
        except: return None

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
        
        # Use localized current time for filtering logs
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
        return live_events[::-1]

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
                    server_time_utc = datetime.strptime(info['modify'], "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                    server_local = server_time_utc.astimezone(SERVER_TZ)
                    ftp.quit()
                    return server_local.strftime("%H:%M:%S")
            if ftp: ftp.quit()
            return "--:--:--"

        # SERVER TIME (Metric updates on page actions)
        st.metric("Server Time (LA)", get_server_now())

        # DEVICE LOCAL TIME (Live Ticking Clock - Automatic detection)
        # This HTML/JS block detects the local timezone and updates the clock every second
        live_clock_html = """
        <div id="clock-container" style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 15px; text-align: center;">
            <div style="color: #8b949e; font-size: 0.8rem; margin-bottom: 5px; font-weight: bold; text-transform: uppercase;">Device Local Time</div>
            <div id="device-clock" style="color: #2ea043; font-size: 1.8rem; font-family: 'Courier New', monospace; font-weight: bold;">--:--:--</div>
            <div id="tz-name" style="color: #58a6ff; font-size: 0.7rem; margin-top: 5px;">Detecting...</div>
        </div>
        <script>
        function updateClock() {
            const now = new Date();
            // Automatically detects timezone from the device
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const options = { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            const timeString = new Intl.DateTimeFormat('en-GB', options).format(now);
            
            document.getElementById('device-clock').innerText = timeString;
            document.getElementById('tz-name').innerText = "Zone: " + tz;
        }
        setInterval(updateClock, 1000);
        updateClock();
        </script>
        """
        components.html(live_clock_html, height=120)

        if st.button("📡 Scan Live Log"):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=300):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()
        st.header("Nitrado FTP Manager")
        # [Remaining original FTP logic here...]
        
        # ... (Rest of Sections 4 & 5 follow)
