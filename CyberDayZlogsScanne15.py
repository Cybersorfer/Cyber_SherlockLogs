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

# --- 2. CSS: UI FIXES & BUTTON VISIBILITY ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    /* Fix Button Text Visibility */
    div.stButton > button {
        color: #ffffff !important;
        background-color: #262730 !important;
        border: 1px solid #4b4b4b !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }
    /* Log Styling */
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    /* Layout Adjustments */
    iframe { border-radius: 10px; border: 1px solid #4b4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FTP & CORE FUNCTIONS (RE-INTEGRATED) ---
FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
        return ftp
    except: return None

def fetch_ftp_logs():
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst()
        valid = ('.ADM', '.RPT', '.log')
        st.session_state.all_logs = sorted([f for f in files if f.upper().endswith(valid)], reverse=True)
        ftp.quit()

def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            coords = [float(parts[0]), float(parts[1])]
    except: pass
    return name, coords

def calculate_distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) if p1 and p2 else 999999

# --- 4. ADVANCED FILTERING LOGIC (FROM PY FILE) ---
def filter_logs(files, mode, target_p=None, area_c=None, area_r=500):
    report, raw_lines = {}, []
    all_content = []
    
    for f in files:
        if f.name.endswith('.zip'):
            with zipfile.ZipFile(f, 'r') as z:
                for n in z.namelist():
                    if n.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        all_content.extend(z.read(n).decode("utf-8", errors="ignore").splitlines())
        else:
            all_content.extend(f.read().decode("utf-8", errors="ignore").splitlines())

    boosting_tracker = {}
    for line in all_content:
        if "|" not in line: continue
        low = line.lower()
        name, coords = extract_player_and_coords(line)
        should_process = False

        if mode == "Full Activity per Player" and target_p == name: should_process = True
        elif mode == "Building Only (Global)" and any(k in low for k in ["placed", "built"]) and "pos=" in low: should_process = True
        elif mode == "Area Activity Search" and coords and area_c:
            if calculate_distance(coords, area_c) <= area_r: should_process = True
        elif mode == "Suspicious Boosting Activity" and any(k in low for k in ["placed", "built"]):
            if any(obj in low for obj in ["fence kit", "fireplace", "barrel"]):
                # Logic simplified for performance
                should_process = True

        if should_process:
            raw_lines.append(line)
            if name not in report: report[name] = []
            report[name].append({"text": line, "time": line.split(" | ")[0][-8:]})
            
    return report, "\n".join(raw_lines)

# --- 5. UI LAYOUT ---

# --- SIDEBAR: NITRADO MANAGER ---
with st.sidebar:
    st.header("🐺 CyberDayZ Manager")
    if 'all_logs' not in st.session_state: fetch_ftp_logs()
    
    st.subheader("Show File Types:")
    c1, c2, c3 = st.columns(3)
    s_adm = c1.checkbox("ADM", value=True); s_rpt = c2.checkbox("RPT", value=True); s_log = c3.checkbox("LOG", value=True)
    
    v_ext = [ext for ext, val in zip([".ADM", ".RPT", ".LOG"], [s_adm, s_rpt, s_log]) if val]
    f_logs = [f for f in st.session_state.get('all_logs', []) if f.upper().endswith(tuple(v_ext))]
    
    cola, colb = st.columns(2)
    if cola.button("Select All"): st.session_state.sel = f_logs
    if colb.button("Clear All"): st.session_state.sel = []
    if st.button("🔄 Refresh FTP List"): fetch_ftp_logs(); st.rerun()

    selected = st.multiselect("Files for Download:", options=f_logs, default=st.session_state.get('sel', []))

    if selected:
        if st.button("📦 Download ZIP"):
            zip_buf = io.BytesIO()
            ftp = get_ftp_connection()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for fn in selected:
                    buf = io.BytesIO(); ftp.retrbinary(f"RETR {fn}", buf.write); zf.writestr(fn, buf.getvalue())
            ftp.quit()
            st.download_button("💾 Save ZIP", zip_buf.getvalue(), "dayz_logs.zip")

# --- MAIN DASHBOARD ---
col_left, col_right = st.columns([1, 1.3])

with col_left:
    st.header("🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Upload .ADM, .RPT or .ZIP logs", accept_multiple_files=True)
    
    if uploaded:
        mode = st.selectbox("Analysis Mode", ["Full Activity per Player", "Building Only (Global)", "Area Activity Search", "Suspicious Boosting Activity"])
        target_player = st.text_input("Player Search", "")
        
        if st.button("🚀 Run Analysis"):
            with st.spinner("Processing..."):
                report, raw = filter_logs(uploaded, mode, target_p=target_player)
                if report:
                    st.success("Analysis Complete")
                    st.download_button("💾 Download Result ADM", raw, "FILTERED.adm")
                    for p in sorted(report.keys()):
                        with st.expander(f"👤 {p}"):
                            for ev in report[p]: st.caption(f"🕒 {ev['time']}"); st.text(ev['text'])
                else:
                    st.warning("No matches found.")

with col_right:
    st.header("📍 iZurvive Map")
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=800, scrolling=True)
