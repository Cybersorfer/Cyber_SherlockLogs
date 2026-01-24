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
        </style>
        """, unsafe_allow_html=True)

    # FTP CREDENTIALS
    FTP_HOST = "usla643.gamedata.io"
    FTP_USER = "ni11109181_1"
    FTP_PASS = "343mhfxd"
    TARGET_DIR = "/dayzps/config"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=20)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            
            # Step-by-step navigation to ensure path exists
            ftp.cwd("/")
            for folder in ["dayzps", "config"]:
                try:
                    ftp.cwd(folder)
                except:
                    st.sidebar.error(f"Could not find folder: {folder}")
                    return None
            return ftp
        except Exception as e:
            st.error(f"FTP Connection Failed: {e}")
            return None

    def extract_dt_from_filename(filename):
        # Pattern for DayZ log format: 2026-01-23_12-30-05
        try:
            match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                dt_str = f"{match.group(1)} {match.group(2).replace('-', ':')}"
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except: pass
        return None

    # ==============================================================================
    # SECTION 3: SIDEBAR (LOG SYNC)
    # ==============================================================================
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        st.divider()
        st.header("Nitrado FTP Manager")
        
        range_mode = st.selectbox("Range Mode:", ["Today", "Last 24h", "All Time"])
        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True)
        show_rpt = cb_cols[1].checkbox("RPT", True)
        show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True):
            ftp = get_ftp_connection()
            if ftp:
                with st.spinner("Scanning /dayzps/config..."):
                    files_raw = []
                    # Use MLSD for detailed file info, fallback to NLST for just names
                    try:
                        ftp.retrlines('MLSD', files_raw.append)
                    except:
                        ftp.retrlines('LIST', files_raw.append)
                    
                    processed = []
                    allowed_ext = []
                    if show_adm: allowed_ext.append(".ADM")
                    if show_rpt: allowed_ext.append(".RPT")
                    if show_log: allowed_ext.append(".LOG")
                    
                    now_utc = datetime.now(pytz.UTC)
                    
                    for line in files_raw:
                        # Parse MLSD format or LIST format to get the filename
                        filename = line.split(';')[-1].strip() if ';' in line else line.split()[-1]
                        
                        if any(filename.upper().endswith(ext) for ext in allowed_ext):
                            dt = extract_dt_from_filename(filename)
                            
                            # Fallback if filename date extraction fails
                            if not dt:
                                try:
                                    if 'modify=' in line:
                                        m_str = next(p for p in line.split(';') if 'modify=' in p).split('=')[1]
                                        dt = datetime.strptime(m_str, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                                    else:
                                        dt = now_utc # Default to now if no metadata
                                except: continue
                            
                            # Filtering Logic
                            include = True
                            if range_mode == "Today": include = dt.date() == now_utc.date()
                            elif range_mode == "Last 24h": include = dt > (now_utc - timedelta(hours=24))
                            
                            if include:
                                disp = f"{filename} ({dt.strftime('%I:%M %p').lower()})"
                                processed.append({"real": filename, "dt": dt, "display": disp})
                    
                    st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                    ftp.quit()
                    
                    if not st.session_state.all_logs:
                        st.sidebar.warning("No matching files found in /dayzps/config.")
                    else:
                        st.sidebar.success(f"Loaded {len(st.session_state.all_logs)} logs.")

        if st.session_state.all_logs:
            st.divider()
            selected_disp = st.multiselect("Select Logs:", options=[f['display'] for f in st.session_state.all_logs])
            
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
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
                    st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip", use_container_width=True)

    # ==============================================================================
    # SECTION 4: MAIN DASHBOARD
    # ==============================================================================
    col1, col2 = st.columns([1, 2.5])
    
    with col1:
        st.markdown("### 🛠️ Log Processor")
        uploaded_files = st.file_uploader("Upload or use synced logs", accept_multiple_files=True)
        
        if uploaded_files:
            hits = []
            for f in uploaded_files:
                text = f.read().decode("utf-8", errors="ignore")
                # Updated Regex to find coordinates/positions in ADM logs
                pattern = r"(\d{2}:\d{2}:\d{2}).*?pos=<([\d\.]+), ([\d\.]+), ([\d\.]+)>"
                matches = re.findall(pattern, text)
                for m in matches:
                    hits.append({"Time": m[0], "X": float(m[1]), "Z": float(m[3])})
            
            if hits:
                df = pd.DataFrame(hits)
                st.write("Latest Positions Found:")
                st.dataframe(df.tail(10), use_container_width=True)
                if st.button("📍 Center Map on Latest"):
                    st.session_state.mv += 1

    with col2:
        st.markdown("<h4 style='text-align: center;'>📍 Live Tracking Map</h4>", unsafe_allow_html=True)
        # Using versioning parameter to force iframe refresh when coordinates update
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=800, scrolling=True)
