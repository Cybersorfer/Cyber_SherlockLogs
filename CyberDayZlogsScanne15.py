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
    # SECTION 2: GLOBAL CONFIG
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
    SERVER_TZ = pytz.timezone('America/Los_Angeles')

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
    # SECTION 6: UI LAYOUT & SIDEBAR (DUAL LIVE CLOCKS)
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Console")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        if st.button("🔌 Log Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()

        st.subheader("🔥 Live Activity (Past 1hr)")
        
        # Dual Live Ticking Clocks: Server (LA) and Device (Auto)
        dual_clocks_html = """
        <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.75rem; margin-bottom: 3px; font-weight: bold; text-transform: uppercase;">Server Time (LA)</div>
                <div id="server-clock" style="color: #58a6ff; font-size: 1.6rem; font-family: 'Courier New', monospace; font-weight: bold;">--:--:--</div>
            </div>
            
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.75rem; margin-bottom: 3px; font-weight: bold; text-transform: uppercase;">Device Local Time</div>
                <div id="device-clock" style="color: #2ea043; font-size: 1.6rem; font-family: 'Courier New', monospace; font-weight: bold;">--:--:--</div>
                <div id="device-tz" style="color: #8b949e; font-size: 0.6rem; margin-top: 2px;">Detecting...</div>
            </div>
        </div>

        <script>
        function updateClocks() {
            const now = new Date();
            
            // Update Server Clock (Forced to LA/Pacific)
            const serverOptions = { timeZone: 'America/Los_Angeles', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('server-clock').innerText = new Intl.DateTimeFormat('en-GB', serverOptions).format(now);
            
            // Update Device Clock (Automatic Detection)
            const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const localOptions = { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
            document.getElementById('device-clock').innerText = new Intl.DateTimeFormat('en-GB', localOptions).format(now);
            document.getElementById('device-tz').innerText = "Zone: " + localTz;
        }
        setInterval(updateClocks, 1000);
        updateClocks();
        </script>
        """
        components.html(dual_clocks_html, height=210)

        if st.button("📡 Scan Live Log"):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=300):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()
        st.header("Nitrado FTP Manager")
        # [Remaining original FTP and Filter code follows here...]
