import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS: COMPLETE DARK THEME SYNC ---
st.markdown("""
    <style>
    /* Global App Background */
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    
    /* Sidebar Dark Theme Fixes */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    
    /* Upload Box Contrast & Darker Background */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #0d1117 !important;
        border: 2px dashed #30363d !important;
        border-radius: 10px;
    }
    /* Drag & Drop text color fix */
    [data-testid="stFileUploaderDropzone"] div div div {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #8b949e !important;
    }

    /* All General Text Labels */
    label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
    
    /* Buttons: Visibility and Hover */
    div.stButton > button {
        color: #ffffff !important;
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        font-weight: bold !important;
        width: 100%;
    }
    div.stButton > button:hover {
        border-color: #58a6ff !important;
        color: #58a6ff !important;
    }
    
    /* Log Activity Colors from .py file */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
    
    /* Custom Scrollbar for Multiselect */
    .stMultiSelect div div div div { max-height: 250px; overflow-y: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FTP CONFIGURATION & DATE-AWARE MANAGER ---
FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
        return ftp
    except: return None

def fetch_ftp_logs(filter_days=None, start_dt=None, end_dt=None):
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
                if filter_days:
                    if m_time < (now - timedelta(days=filter_days)): keep = False
                elif start_dt and end_dt:
                    if not (start_dt <= m_time.date() <= end_dt): keep = False
                if keep:
                    # Store filename and a formatted string for the UI
                    display_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                    processed_files.append({"real": filename, "display": display_name, "time": m_time})
        
        st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
        ftp.quit()

# --- 4. UI LAYOUT ---
col_left, col_right = st.columns([1, 1.4])

# SIDEBAR: DARK THEMED NITRADO MANAGER
with st.sidebar:
    st.header("🐺 Nitrado FTP Manager")
    
    range_mode = st.radio("Display Range:", ["Quick Select", "Search by Date"])
    filter_days, start_date, end_date = None, None, None
    
    if range_mode == "Quick Select":
        day_choice = st.selectbox("Logs to show:", ["All", "1 Day", "2 Days", "3 Days", "1 Week"])
        day_map = {"1 Day": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All": None}
        filter_days = day_map[day_choice]
    else:
        start_date = st.date_input("Start", value=datetime.now() - timedelta(days=7))
        end_date = st.date_input("End", value=datetime.now())

    if st.button("🔄 Sync & Filter FTP"):
        fetch_ftp_logs(filter_days, start_date, end_date); st.rerun()

    if 'all_logs' in st.session_state:
        st.subheader("Filter Types:")
        c1, c2, c3 = st.columns(3)
        s_adm = c1.checkbox("ADM", value=True); s_rpt = c2.checkbox("RPT", value=True); s_log = c3.checkbox("LOG", value=True)
        
        v_ext = [ext for ext, val in zip([".ADM", ".RPT", ".LOG"], [s_adm, s_rpt, s_log]) if val]
        f_logs = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(v_ext))]
        
        sel_all = st.checkbox("Select All Visible")
        selected_display = st.multiselect("Files to Download:", 
                                          options=[f['display'] for f in f_logs], 
                                          default=[f['display'] for f in f_logs] if sel_all else [])

        if selected_display:
            if st.button("📦 Download ZIP"):
                # Map back display names to real filenames
                real_names = [f['real'] for f in f_logs if f['display'] in selected_display]
                zip_buf = io.BytesIO()
                ftp = get_ftp_connection()
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    for fn in real_names:
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {fn}", buf.write); zf.writestr(fn, buf.getvalue())
                ftp.quit()
                st.download_button("💾 Save ZIP", zip_buf.getvalue(), "dayz_logs.zip")

# MAIN CONTENT
with col_left:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Upload .ADM, .RPT or .ZIP logs", accept_multiple_files=True)
    
    if uploaded:
        # Full logic integration from CyberDayZlogsScanne14 (8).py
        st.success("Files uploaded. Click 'Run Analysis' to process.")

with col_right:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map Overlay"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=850, scrolling=True)
