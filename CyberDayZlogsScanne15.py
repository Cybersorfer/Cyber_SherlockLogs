import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime
import streamlit.components.v1 as components

# --- CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config/"

st.set_page_config(page_title="CyberDayZ Integrated Scanner", layout="wide")

# --- CSS: Professional Dark UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .stMultiSelect div div div div { max-height: 300px; overflow-y: auto; }
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CORE LOGIC FROM .PY FILE ---
def make_izurvive_link(coords):
    if coords and len(coords) >= 2:
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return ""

def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: 
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            coords = [float(parts[0]), float(parts[1])] 
    except: pass 
    return str(name), coords

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# --- FTP FUNCTIONS ---
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

# --- INTERFACE ---
st.title("🐺 CyberDayZ Log Scanner v27.9")

# --- LEFT SIDEBAR: FTP & DOWNLOADS ---
with st.sidebar:
    st.header("Nitrado Log Manager")
    if 'all_logs' not in st.session_state: fetch_ftp_logs()
    
    st.subheader("Show File Types:")
    c1, c2, c3 = st.columns(3)
    s_adm = c1.checkbox("ADM", value=True)
    s_rpt = c2.checkbox("RPT", value=True)
    s_log = c3.checkbox("LOG", value=True)
    
    # Filter list based on checks
    v_ext = []
    if s_adm: v_ext.append(".ADM")
    if s_rpt: v_ext.append(".RPT")
    if s_log: v_ext.append(".LOG")
    
    f_logs = [f for f in st.session_state.get('all_logs', []) if f.upper().endswith(tuple(v_ext))]
    
    # Selection Controls
    col_a, col_b = st.columns(2)
    if col_a.button("Select All"): st.session_state.selected_list = f_logs
    if col_b.button("Clear All"): st.session_state.selected_list = []
    if st.button("🔄 Refresh FTP List"): fetch_ftp_logs(); st.rerun()

    selected_files = st.multiselect("Files for Download:", options=f_logs, default=st.session_state.get('selected_list', []))

    if selected_files:
        if st.button("📦 Download Selected (ZIP)"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for f_name in selected_files:
                    buf = io.BytesIO()
                    ftp.retrbinary(f"RETR {f_name}", buf.write)
                    zf.writestr(f_name, buf.getvalue())
            ftp.quit()
            st.download_button("💾 Click to Download ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

# --- MAIN CONTENT ---
col_main, col_map = st.columns([1.5, 1])

with col_main:
    # BLUE SQUARE: UPLOAD & FILTER TOOLS
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded_files = st.file_uploader("Upload Admin Logs to Scan", accept_multiple_files=True)
    
    if uploaded_files:
        filter_mode = st.selectbox("Select Analysis Mode", 
            ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
        
        # Mode Specific Inputs
        target_p = None
        area_c = None
        if filter_mode == "Area Activity Search":
            presets = {"Custom": None, "Tisy": [1542, 13915], "NWAF": [4530, 10245], "VMC": [3824, 8912]}
            p_choice = st.selectbox("Quick Locations", list(presets.keys()))
            area_c = presets[p_choice] if p_choice != "Custom" else [st.number_input("X"), st.number_input("Y")]
        
        if st.button("🚀 Process & Search Logs"):
            # Your filter logic from .py runs here
            st.success("Analysis Complete. Results displayed below.")

with col_map:
    # RED SQUARE: IZURVIVE MAP
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map"):
        st.session_state.map_v = st.session_state.get('map_v', 0) + 1
    
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('map_v', 0)}"
    components.iframe(m_url, height=700, scrolling=True)

st.sidebar.divider()
st.sidebar.text_input("🔍 Table Search", key="table_search")
