import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

# --- 2. PROFESSIONAL DARK UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    /* Horizontal Checkbox Styling */
    [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    /* Death and Activity Logs */
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    /* Map Container Fix */
    iframe { border-radius: 10px; border: 1px solid #4b4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FTP CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config/"

# --- 4. CORE FUNCTIONS (Integrated from .py) ---
def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def fetch_ftp_logs():
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst()
        valid = ('.ADM', '.RPT', '.log')
        st.session_state.all_logs = sorted([f for f in files if f.upper().endswith(valid)], reverse=True)
        ftp.quit()

def download_file(file_name):
    ftp = get_ftp_connection()
    if ftp:
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {file_name}", buffer.write)
        ftp.quit()
        return buffer.getvalue()
    return None

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# --- 5. UI LAYOUT ---

# --- SIDEBAR: NITRADO LOG MANAGER ---
with st.sidebar:
    st.header("🐺 CyberDayZ Manager")
    if 'all_logs' not in st.session_state: fetch_ftp_logs()
    
    st.subheader("Show File Types:")
    c1, c2, c3 = st.columns(3)
    s_adm = c1.checkbox("ADM", value=True)
    s_rpt = c2.checkbox("RPT", value=True)
    s_log = c3.checkbox("LOG", value=True)
    
    # Filter list
    v_ext = []
    if s_adm: v_ext.append(".ADM")
    if s_rpt: v_ext.append(".RPT")
    if s_log: v_ext.append(".LOG")
    f_logs = [f for f in st.session_state.get('all_logs', []) if f.upper().endswith(tuple(v_ext))]
    
    # Controls
    col_a, col_b = st.columns(2)
    if col_a.button("Select All"): st.session_state.sel_list = f_logs
    if col_b.button("Clear All"): st.session_state.sel_list = []
    
    if st.button("🔄 Refresh FTP List"): fetch_ftp_logs(); st.rerun()

    sel_files = st.multiselect("Files for Download:", options=f_logs, default=st.session_state.get('sel_list', []))

    if sel_files:
        if st.button("📦 Bundle & Download (ZIP)"):
            zip_buf = io.BytesIO()
            ftp = get_ftp_connection()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for fn in sel_files:
                    buf = io.BytesIO()
                    ftp.retrbinary(f"RETR {fn}", buf.write)
                    zf.writestr(fn, buf.getvalue())
            ftp.quit()
            st.download_button("💾 Download ZIP Archive", zip_buf.getvalue(), "cyber_logs.zip")

    st.divider()
    table_search = st.text_input("🔍 Table Search", key="tbl_search")

# --- MAIN DASHBOARD: THE TWO SQUARES ---
col_left, col_right = st.columns([1, 1.8]) # Map gets 1.8x the space

with col_left:
    # THE BLUE SQUARE: ADVANCED LOG FILTERING
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Upload logs for content analysis", accept_multiple_files=True)
    
    if uploaded:
        mode = st.selectbox("Analysis Mode", ["Full Activity per Player", "Session Tracking", "Building Only", "Raid Watch", "Area Activity Search"])
        if st.button("🚀 Process Uploaded Logs"):
            # Your filter_logs() logic would execute here
            st.success("Analysis results generated below.")
            # Example Placeholder output
            st.info("Results table would appear here as per your .py file.")

with col_right:
    # THE RED SQUARE: IZURVIVE MAP (MAX SIZE)
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map Overlay"):
        st.session_state.mv = st.session_state.get('mv', 0) + 1
    
    # Using the iframe from your screenshot requirements
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=850, scrolling=True)
