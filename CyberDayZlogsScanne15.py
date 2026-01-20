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
    
    /* LOG ACTIVITY COLORS (SYNCED WITH v14-9) */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 🐺 NITRADO FTP MANAGER LOGIC ---
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

# --- 4. 🛠️ ADVANCED LOG FILTERING LOGIC (SYNCED WITH v14-9) ---
def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            pts = [p.strip() for p in raw.split(",")]
            # COORDINATE FIX: Use X (pts[0]) and Z (pts[2])
            coords = [float(pts[0]), float(pts[2])] 
    except: pass
    return str(name), coords

def filter_v14_9_logic(lines, mode, target_p=None, area_c=None, area_r=500, start_time="00:00:00"):
    report, raw_lines = {}, []
    header = f"******************************************************************************\nAdminLog started on {datetime.now().strftime('%Y-%m-%d')} at {start_time}\n\n"
    
    # Exact keywords from your file
    build_k = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_k = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    sess_k = ["connected", "disconnected", "died", "killed"]
    boost_obj = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]
    boost_track = {}

    for line in lines:
        if "|" not in line: continue
        name, coords = extract_player_and_coords(line)
        low, match = line.lower(), False
        
        if mode == "Full Activity per Player": match = (target_p == name)
        elif mode == "Building Only (Global)": match = any(k in low for k in build_k) and "pos=" in low
        elif mode == "Raid Watch (Global)": match = any(k in low for k in raid_k) and "pos=" in low
        elif mode == "Session Tracking (Global)": match = any(k in low for k in sess_k)
        elif mode == "Area Activity Search" and coords and area_c:
            # AREA FIX: Distance logic on X/Z plane
            dist = math.sqrt((coords[0]-area_c[0])**2 + (coords[1]-area_c[1])**2)
            match = (dist <= area_r)
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
c_left, c_right = st.columns([1, 1.4])

with st.sidebar:
    st.header("🐺 Nitrado FTP Manager")
    r_mode = st.radio("Display Range:", ["Quick Select", "Search by Date/Hour"])
    f_d, s_d, e_d, s_h, e_h = None, None, None, 0, 23
    if r_mode == "Quick Select":
        d_map = {"1 Day": 1, "2 Days": 2, "3 Days": 3, "1 Week": 7, "All": None}
        f_d = d_map[st.selectbox("Show Logs:", list(d_map.keys()))]
    else:
        s_d, e_d = st.date_input("Start Date"), st.date_input("End Date")
        s_h, e_h = st.slider("Hour Range", 0, 23, (0, 23))

    if st.button("🔄 Sync & Filter FTP"): fetch_ftp_logs(f_d, s_d, e_d, s_h, e_h); st.rerun()

    if 'all_logs' in st.session_state:
        st.subheader("Filter Types:")
        c1, c2, c3 = st.columns(3)
        s_adm = c1.checkbox("ADM", value=True); s_rpt = c2.checkbox("RPT", value=True); s_log = c3.checkbox("LOG", value=True)
        v_ext = [ext for ext, val in zip([".ADM", ".RPT", ".LOG"], [s_adm, s_rpt, s_log]) if val]
        f_logs = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(v_ext))]
        sel_all = st.checkbox("Select All Visible")
        selected_disp = st.multiselect("Files for Download:", options=[f['display'] for f in f_logs], default=[f['display'] for f in f_logs] if sel_all else [])
        if selected_disp and st.button("📦 Prepare ZIP Download"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            if ftp:
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in f_logs if f['display'] == disp)
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {real_name}", buf.write); zf.writestr(real_name, buf.getvalue())
                ftp.quit(); st.download_button("💾 Download ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

with c_left:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
    
    if uploaded:
        # Separate logic for Player Scan
        all_lines, player_list, s_time = [], set(), "00:00:00"
        for f in uploaded:
            f.seek(0)
            content = f.read().decode("utf-8", errors="ignore")
            all_lines.extend(content.splitlines())
            player_list.update(re.findall(r'Player "([^"]+)"', content))
            if s_time == "00:00:00":
                t_match = re.search(r'(\d{2}:\d{2}:\d{2})', content)
                if t_match: s_time = t_match.group(1)

        mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
        target_p, area_c, area_r = None, None, 500
        if mode == "Full Activity per Player":
            target_p = st.selectbox("Select Player", sorted(list(player_list)))
        elif mode == "Area Activity Search":
            presets = {"NWAF": [4530, 10245], "Tisy": [1542, 13915], "Zenit": [8355, 5978], "Gorka": [9494, 8820]}
            choice = st.selectbox("Quick Location", list(presets.keys()))
            area_c, area_r = presets[choice], st.slider("Radius (Meters)", 50, 2000, 500)

        if st.button("🚀 Process Uploaded Logs"):
            report, raw = filter_v14_9_logic(all_lines, mode, target_p, area_c, area_r, s_time)
            st.session_state.res_report, st.session_state.res_raw = report, raw

    if "res_report" in st.session_state and st.session_state.res_report:
        st.download_button("💾 Download Result ADM", st.session_state.res_raw, "FILTERED.adm")
        for p, evs in st.session_state.res_report.items():
            with st.expander(f"👤 {p}"):
                for ev in evs: st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)

with c_right:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map Overlay"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
