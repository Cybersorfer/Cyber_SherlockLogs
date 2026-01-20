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

# --- 2. CSS: HIGH CONTRAST & BUTTON VISIBILITY ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    
    /* HIGH CONTRAST SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #1c2128 !important;
        border-right: 2px solid #30363d;
    }

    /* GREEN BUTTON THEME SYNC */
    .stFileUploader label [data-testid="stBaseButton-secondary"], 
    div.stButton > button {
        color: #ffffff !important;
        background-color: #238636 !important; 
        border: 1px solid #2ea043 !important;
        font-weight: bold !important;
        text-transform: uppercase;
        width: 100% !important;
    }

    /* LOG ACTIVITY COLORS (EXACT SYNC) */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 🐺 NITRADO FTP MANAGER (INDEPENDENT LOGIC) ---
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

# --- 4. 🛠️ ADVANCED LOG FILTERING (EXACT SYNC WITH v14-9 FILE) ---
def extract_data_v14_9(line):
    """Exact coordinate extraction logic from your file."""
    name, coords = "System/Server", None
    try:
        if 'Player "' in line:
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            pts = [p.strip() for p in raw.split(",")]
            # In DayZ logs: [X, Y, Z]. Area search uses X and Z.
            coords = [float(pts[0]), float(pts[2])] 
    except: pass
    return name, coords

def filter_v14_9_exact(files, mode, target_p=None, area_c=None, area_r=500):
    report, raw_lines = {}, []
    all_content = []
    
    # Header logic from your script
    first_ts = "00:00:00"
    
    for f in files:
        f.seek(0)
        content = ""
        if f.name.endswith('.zip'):
            with zipfile.ZipFile(f, 'r') as z:
                for n in z.namelist():
                    if n.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        content = z.read(n).decode("utf-8", errors="ignore")
                        all_content.extend(content.splitlines())
        else:
            content = f.read().decode("utf-8", errors="ignore")
            all_content.extend(content.splitlines())
        
        if first_ts == "00:00:00":
            ts_match = re.search(r'(\d{2}:\d{2}:\d{2})', content)
            if ts_match: first_ts = ts_match.group(1)

    header = f"******************************************************************************\nAdminLog started on {datetime.now().strftime('%Y-%m-%d')} at {first_ts}\n\n"

    # Exact keywords/objects from your v14-9 logic
    build_k = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_k = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    sess_k = ["connected", "disconnected", "died", "killed"]
    boost_obj = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]
    boost_track = {}

    for line in all_content:
        if "|" not in line: continue
        name, coords = extract_data_v14_9(line)
        low, match = line.lower(), False

        if mode == "Full Activity per Player": match = (target_p == name)
        elif mode == "Building Only (Global)": match = any(k in low for k in build_k) and "pos=" in low
        elif mode == "Raid Watch (Global)": match = any(k in low for k in raid_k) and "pos=" in low
        elif mode == "Session Tracking (Global)": match = any(k in low for k in sess_k)
        elif mode == "Area Activity Search" and coords and area_c:
            # Distance logic strictly from your file
            dist = math.sqrt((coords[0]-area_c[0])**2 + (coords[1]-area_c[1])**2)
            if dist <= area_r: match = True
        elif mode == "Suspicious Boosting Activity" and any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boost_obj):
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
col_l, col_r = st.columns([1, 1.4])

with st.sidebar:
    st.header("🐺 Nitrado FTP Manager")
    r_mode = st.radio("Range:", ["Quick Select", "Search by Date/Hour"])
    f_d, s_d, e_d, s_h, e_h = None, None, None, 0, 23
    if r_mode == "Quick Select":
        d_map = {"1 Day": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All": None}
        f_d = d_map[st.selectbox("Logs:", list(d_map.keys()))]
    else:
        s_d, e_d = st.date_input("Start"), st.date_input("End")
        s_h, e_h = st.slider("Hours", 0, 23, (0, 23))
    
    if st.button("🔄 Sync FTP"): fetch_ftp_logs(f_d, s_d, e_d, s_h, e_h); st.rerun()
    # (FTP download logic is separate here)

with col_l:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
    
    if uploaded:
        # Scan players for dropdown
        all_txt = []
        p_list = set()
        for f in uploaded:
            f.seek(0)
            txt = f.read().decode("utf-8", errors="ignore")
            p_list.update(re.findall(r'Player "([^"]+)"', txt))
        
        mode = st.selectbox("Select Filter", ["Full Activity per Player", "Building Only (Global)", "Area Activity Search", "Raid Watch (Global)", "Suspicious Boosting Activity"])
        
        t_p, a_c, a_r = None, None, 500
        if mode == "Full Activity per Player":
            t_p = st.selectbox("Select Player", sorted(list(p_list)))
        elif mode == "Area Activity Search":
            presets = {"NWAF": [4530, 10245], "Tisy": [1542, 13915], "Zenit": [8355, 5978], "Gorka": [9494, 8820], "VMC": [3824, 8912]}
            choice = st.selectbox("Quick Location", list(presets.keys()))
            a_c = presets[choice]
            a_r = st.slider("Radius", 50, 2000, 500)

        if st.button("🚀 Process Logs"):
            rep, raw = filter_v14_9_exact(uploaded, mode, t_p, a_c, a_r)
            st.session_state.res_rep, st.session_state.res_raw = rep, raw

    if "res_rep" in st.session_state and st.session_state.res_rep:
        st.download_button("💾 Download ADM", st.session_state.res_raw, "FILTERED.adm")
        for p, evs in st.session_state.res_rep.items():
            with st.expander(f"👤 {p}"):
                for ev in evs: st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)

with col_r:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
