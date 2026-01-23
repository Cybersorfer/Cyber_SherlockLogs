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
    if 'track_data' not in st.session_state: st.session_state.track_data = None
    if 'map_click_x' not in st.session_state: st.session_state.map_click_x = 1542.0
    if 'map_click_y' not in st.session_state: st.session_state.map_click_y = 13915.0
    if 'all_logs' not in st.session_state: st.session_state.all_logs = []
    if 'current_path' not in st.session_state: st.session_state.current_path = "/"

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

    # UPDATED CONFIG: Based on common Nitrado structures
    FTP_HOST = "usla643.gamedata.io"
    FTP_USER = "ni11109181_1"
    FTP_PASS = "343mhfxd"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=15)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            return ftp
        except Exception as e:
            st.error(f"FTP Connection Error: {e}")
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

    # ==============================================================================
    # SECTION 3: SIDEBAR (FOLDER EXPLORER & SYNC)
    # ==============================================================================
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        
        # Folder Explorer Tool
        with st.expander("📂 FTP Folder Explorer", expanded=False):
            st.info(f"Current Path: `{st.session_state.current_path}`")
            ftp_explore = get_ftp_connection()
            if ftp_explore:
                try:
                    ftp_explore.cwd(st.session_state.current_path)
                    items = ftp_explore.nlst()
                    for item in items:
                        if st.button(f"📁 {item}", key=f"dir_{item}"):
                            st.session_state.current_path = f"{st.session_state.current_path.rstrip('/')}/{item}/"
                            st.rerun()
                    if st.button("⬅️ Go Back to Root"):
                        st.session_state.current_path = "/"
                        st.rerun()
                except: st.error("Could not read directory")
                finally: ftp_explore.quit()

        st.divider()
        st.header("Nitrado FTP Manager")
        
        # Manual Path Input (Update this after exploring)
        manual_path = st.text_input("Target Log Folder:", value=st.session_state.current_path)
        
        range_mode = st.selectbox("Range Mode:", ["Today", "Last 24h", "Calendar", "All Time"])
        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True)
        show_rpt = cb_cols[1].checkbox("RPT", True)
        show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True):
            ftp = get_ftp_connection()
            if ftp:
                try:
                    ftp.cwd(manual_path)
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
                            
                            if include:
                                disp = f"{filename} ({dt.strftime('%I:%M %p').lower()})"
                                processed.append({"real": filename, "dt": dt, "display": disp, "path": manual_path})
                    
                    st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                    st.success(f"Found {len(st.session_state.all_logs)} logs!")
                except Exception as e:
                    st.error(f"Sync failed: {e}")
                finally: ftp.quit()

        if st.session_state.all_logs:
            selected_disp = st.multiselect("Select Files:", options=[f['display'] for f in st.session_state.all_logs])
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp_zip = get_ftp_connection()
                if ftp_zip:
                    with st.spinner("Zipping..."):
                        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for disp in selected_disp:
                                file_info = next(f for f in st.session_state.all_logs if f['display'] == disp)
                                ftp_zip.cwd(file_info['path'])
                                fbuf = io.BytesIO()
                                ftp_zip.retrbinary(f"RETR {file_info['real']}", fbuf.write)
                                zf.writestr(file_info['real'], fbuf.getvalue())
                        st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip", use_container_width=True)
                    ftp_zip.quit()

    # ==============================================================================
    # SECTION 4: MAIN CONTENT (UNCHANGED SCANNER LOGIC)
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])
    # ... (Rest of your filter_logs and UI logic remains the same)
    with col1:
        st.info("Upload logs below or use the FTP Manager to sync directly from your server.")
        # [Remainder of original scanning code]
    
