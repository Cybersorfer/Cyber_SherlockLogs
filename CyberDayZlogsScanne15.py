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
            st.rerun()
        else:
            st.error("❌ Invalid Credentials")
    return False

if check_password():
    # ==============================================================================
    # SECTION 2: GLOBAL CONFIG & THEME
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
    
    # Initialize Map version if not exists
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
        if not ftp: return ["Error: FTP Timeout. Try again."]
        try:
            files = []
            ftp.retrlines('NLST', files.append)
            # Filter for latest ADM file
            adm_files = sorted([f for f in files if f.upper().endswith(".ADM")], reverse=True)
            if not adm_files: return ["Error: No ADM logs found."]
            
            target_file = adm_files[0]
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
            return live_events[::-1] if live_events else ["No activity in the last hour."]
        except Exception as e:
            return [f"Error scanning: {str(e)}"]

    # ==============================================================================
    # SECTION 6: UI LAYOUT & SIDEBAR (FIXED CLOCKS & BUTTONS)
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Console")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        
        # Dual Live Ticking Clocks
        dual_clocks_html = """
        <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px;">
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Server Time (LA)</div>
                <div id="server-clock" style="color: #58a6ff; font-size: 1.6rem; font-family: monospace; font-weight: bold;">--:--:--</div>
            </div>
            <div style="background: #1c2128; border: 1px solid #30363d; border-radius: 8px; padding: 12px; text-align: center;">
                <div style="color: #8b949e; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Device Local Time</div>
                <div id="device-clock" style="color: #2ea043; font-size: 1.6rem; font-family: monospace; font-weight: bold;">--:--:--</div>
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
        components.html(dual_clocks_html, height=180)

        st.subheader("🔥 Live Activity (Past 1hr)")
        if st.button("📡 Scan Live Log"):
            st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(border=True):
                for entry in st.session_state.live_log_data:
                    st.markdown(f"<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        if st.button("🔌 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # ==============================================================================
    # MAIN PAGE CONTENT (MAP PERSISTENCE)
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])
    
    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        # Process files if uploaded... (Logic goes here)

    with col2:
        # This keeps the map visible even when sidebar buttons are clicked
        st.markdown(f"#### 📍 iSurvive Live Map View")
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
        if st.button("🔄 Force Map Refresh"):
            st.session_state.mv += 1
            st.rerun()
