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

# --- 2. CSS: UI TEXT VISIBILITY & HIGH CONTRAST ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
    
    /* HIGH CONTRAST SIDEBAR (Nitrado Section) */
    section[data-testid="stSidebar"] { 
        background-color: #1c2128 !important; 
        border-right: 2px solid #30363d; 
    }

    /* GREEN BUTTON THEME */
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

# --- 3. RESTORED & LOCKED: NITRADO FTP MANAGER LOGIC ---
FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except:
        return None

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
                    display_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                    processed_files.append({"real": filename, "display": display_name, "time": m_time})
        
        st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
        ftp.quit()

# --- 4. ADVANCED FILTERING LOGIC (SYNCED WITH v14-9) ---
def extract_v14_data(line):
    name, coords = "System", None
    try:
        if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            pts = [p.strip() for p in raw.split(",")]
            # X and Z plane distance calculation
            coords = [float(pts[0]), float(pts[2])] 
    except: pass
    return name, coords

def filter_v14_9_logic(files, mode, target_p=None, area_c=None, area_r=500):
    report, raw_lines = {}, []
    all_content = []
    first_ts = "00:00:00"
    
    for f in files:
        f.seek(0)
        content = f.read().decode("utf-8", errors="ignore")
        all_content.extend(content.splitlines())
        if first_ts == "00:00:00":
            t_match = re.search(r'(\d{2}:\d{2}:\d{2})', content)
            if t_match: first_ts = t_match.group(1)

    header = f"******************************************************************************\nAdminLog started on {datetime.now().strftime('%Y-%m-%d')} at {first_ts}\n\n"

    for line in all_content:
        if "|" not in line: continue
        name, coords = extract_v14_data(line)
        low, match = line.lower(), False
        
        if mode == "Full Activity per Player": match = (target_p == name)
        elif mode == "Area Activity Search" and coords and area_c:
            dist = math.sqrt((coords[0]-area_c[0])**2 + (coords[1]-area_c[1])**2)
            match = (dist <= area_r)
        # Other modes from v14-9...
        
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
    # Date/Time Selection Tools
    if st.button("🔄 Sync FTP"): fetch_ftp_logs(); st.rerun()

    if 'all_logs' in st.session_state:
        f_logs = st.session_state.all_logs
        selected_disp = st.multiselect("Files to Download:", options=[f['display'] for f in f_logs])
        
        if selected_disp and st.button("📦 Prepare ZIP"):
            zip_buffer = io.BytesIO()
            ftp = get_ftp_connection()
            if ftp:
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in f_logs if f['display'] == disp)
                        buf = io.BytesIO(); ftp.retrbinary(f"RETR {real_name}", buf.write); zf.writestr(real_name, buf.getvalue())
                ftp.quit(); st.download_button("💾 Download ZIP", zip_buffer.getvalue(), "dayz_logs.zip")

with col_l:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
    if uploaded:
        # Filtering UI and processing...
        pass

with col_r:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
