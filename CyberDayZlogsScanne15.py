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

# --- 2. CSS: HIGH CONTRAST DARK UI & BUTTON SYNC ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
    
    /* LOCKED SECTION: SIDEBAR STYLING */
    section[data-testid="stSidebar"] {
        background-color: #1c2128 !important;
        border-right: 2px solid #30363d;
    }

    /* ACTION BUTTONS: GREEN THEME */
    .stFileUploader label [data-testid="stBaseButton-secondary"], 
    div.stButton > button {
        color: #ffffff !important;
        background-color: #238636 !important; 
        border: 1px solid #2ea043 !important;
        font-weight: bold !important;
        text-transform: uppercase;
        width: 100% !important;
    }
    
    /* LOG COLORS SYNCED WITH v14 */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. [LOCKED SECTION] NITRADO FTP MANAGER ---
# Finalized logic for FTP connection and management
FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
        return ftp
    except: return None

def fetch_ftp_logs(filter_days=None, start_dt=None, end_dt=None, start_h=0, end_h=23):
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
                if filter_days and m_time < (now - timedelta(days=filter_days)): keep = False
                elif start_dt and end_dt and not (start_dt <= m_time.date() <= end_dt): keep = False
                if not (start_h <= m_time.hour <= end_h): keep = False
                if keep:
                    d_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                    processed_files.append({"real": filename, "display": d_name, "time": m_time})
        st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
        ftp.quit()

# --- 4. ADVANCED LOG FILTERING (EXACT LOGIC SYNC) ---
def extract_log_data(line):
    name, coords = "System", None
    try:
        if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            pts = [p.strip() for p in raw.split(",")]
            # FIXED: X is pts[0], Z is pts[2]. Ignore Altitude (pts[1]) for town distance.
            coords = [float(pts[0]), float(pts[2])] 
    except: pass
    return name, coords

def filter_v14_logic(files, mode, target_p=None, area_c=None, area_r=500):
    report, raw_lines = {}, []
    all_content, first_ts = [], "00:00:00"
    
    for f in files:
        f.seek(0)
        content = f.read().decode("utf-8", errors="ignore")
        all_content.extend(content.splitlines())
        if first_ts == "00:00:00":
            t_match = re.search(r'(\d{2}:\d{2}:\d{2})', content)
            if t_match: first_ts = t_match.group(1)

    header = f"******************************************************************************\nAdminLog started on {datetime.now().strftime('%Y-%m-%d')} at {first_ts}\n\n"

    # Keywords strictly from your v14-10 logic
    build_k = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_k = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    sess_k = ["connected", "disconnected", "died", "killed"]
    boost_obj = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]
    boost_track = {}

    for line in all_content:
        if "|" not in line: continue
        name, coords = extract_log_data(line)
        low, match = line.lower(), False
        
        if mode == "Full Activity per Player": match = (target_p == name)
        elif mode == "Area Activity Search" and coords and area_c:
            # COORDINATE PLANE FIX: Distance using horizontal X/Z plane
            dist = math.sqrt((coords[0]-area_c[0])**2 + (coords[1]-area_c[1])**2)
            match = (dist <= area_r)
        elif mode == "Building Only (Global)": match = any(k in low for k in build_k) and "pos=" in low
        elif mode == "Raid Watch (Global)": match = any(k in low for k in raid_k) and "pos=" in low
        elif mode == "Session Tracking (Global)": match = any(k in low for k in sess_k)
        elif mode == "Suspicious Boosting Activity" and any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boost_obj):
            # Same logic from your file for boosting detection
            t_str = line.split(" | ")[0][-8:]
            try:
                t_val = datetime.strptime(t_str, "%H:%M:%S")
                if name not in boost_track: boost_track[name] = []
                boost_track[name].append({"time": t_val, "pos": coords})
                if len(boost_track[name]) >= 3:
                    prev = boost_track[name][-3]
                    if (t_val - prev["time"]).total_seconds() <= 300 and math.sqrt((coords[0]-prev["pos"][0])**2 + (coords[1]-prev["pos"][1])**2) < 15:
                        match = True
            except: continue

        if match:
            raw_lines.append(line.strip())
            status = "connect" if "connect" in low else "disconnect" if "disconnect" in low else "death" if any(x in low for x in ["died", "killed"]) else "normal"
            if name not in report: report[name] = []
            report[name].append({"time": line.split(" | ")[0][-8:], "text": line.strip(), "status": status})
            
    return report, header + "\n".join(raw_lines)

# --- 5. UI LAYOUT ---
col_left, col_right = st.columns([1, 1.4])

with st.sidebar:
    st.header("🐺 Nitrado FTP Manager")
    # Date/Time Range for FTP files
    if st.button("🔄 Sync FTP List"): fetch_ftp_logs(); st.rerun()
    if 'all_logs' in st.session_state:
        f_logs = st.session_state.all_logs
        sel_disp = st.multiselect("Select Files:", options=[f['display'] for f in f_logs])
        if sel_disp and st.button("📦 Prepare ZIP"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            if ftp:
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for disp in sel_disp:
                        real_name = next(f['real'] for f in f_logs if f['display'] == disp)
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {real_name}", buf.write); zf.writestr(real_name, buf.getvalue())
                ftp.quit(); st.download_button("💾 Download ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

with col_left:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
    if uploaded:
        # EXACT TOWN LIST SYNC
        presets = {
            "NWAF": [4530, 10245], "Tisy": [1542, 13915], "Zenit": [8355, 5978], 
            "Gorka": [9494, 8820], "VMC": [3824, 8912], "Zelenogorsk": [2540, 5085],
            "Prison Island": [2500, 1300], "Berezino": [12885, 9652], "Cherno": [6550, 2465]
        }
        mode = st.selectbox("Select Filter", ["Area Activity Search", "Full Activity per Player", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity"])
        
        t_player, a_coords, a_radius = None, None, 500
        if mode == "Area Activity Search":
            choice = st.selectbox("Quick Location", list(presets.keys()))
            a_coords, a_radius = presets[choice], st.slider("Radius (Meters)", 50, 2000, 500)
        elif mode == "Full Activity per Player":
            p_names = set()
            for f in uploaded: f.seek(0); p_names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
            t_player = st.selectbox("Select Player", sorted(list(p_names)))

        if st.button("🚀 Process Uploaded Logs"):
            rep, raw = filter_v14_logic(uploaded, mode, t_player, a_coords, a_radius)
            st.session_state.res_rep, st.session_state.res_raw = rep, raw

    if "res_rep" in st.session_state and st.session_state.res_rep:
        st.download_button("💾 Download ADM", st.session_state.res_raw, "CYBER_FILTERED.adm")
        for p, evs in st.session_state.res_rep.items():
            with st.expander(f"👤 {p}"):
                for ev in evs: st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)

with col_right:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
