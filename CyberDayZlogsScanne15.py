import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: TEAM ACCESS CONTROL & IP TRACKER (THE SHELL)
# ==============================================================================
team_accounts = {
    "cybersorfer": "cyber001",
    "Admin": "cyber001",
    "dirtmcgirrt": "dirt002",
    "TrapTyree": "trap003",
    "CAPTTipsyPants": "cap004"
}

def get_remote_ip():
    try: return st.context.headers.get("X-Forwarded-For", "Unknown/Local")
    except: return "Unknown"

def log_session(user, action):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = get_remote_ip()
    entry = f"{now} | User: {user} | Action: {action} | IP: {ip}\n"
    with open("login_history.txt", "a") as f:
        f.write(entry)

def check_password():
    def password_entered():
        u_in, p_in = st.session_state["username"], st.session_state["password"]
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
            del st.session_state["password"] 
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.subheader("🛡️ CyberDayZ Team Portal")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state:
            st.error("❌ Invalid Credentials")
        return False
    return True

# --- ONLY RUN CORE TOOLS IF LOGGED IN ---
if check_password():

    # ==============================================================================
    # SECTION 2: GLOBAL PAGE SETUP & THEME (RESTORATION)
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #ffffff !important; }
        label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
        section[data-testid="stSidebar"] { background-color: #1c2128 !important; border-right: 2px solid #30363d; }
        div.stButton > button {
            color: #ffffff !important;
            background-color: #238636 !important; 
            border: 1px solid #2ea043 !important;
            font-weight: bold !important;
            text-transform: uppercase;
            width: 100% !important;
        }
        .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px;}
        .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px;}
        .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px;}
        </style>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # SECTION 3: 🐺 NITRADO FTP MANAGER (ENHANCED SELECTION)
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST); ftp.login(user=FTP_USER, passwd=FTP_PASS); ftp.cwd(FTP_PATH)
            return ftp
        except: return None

    def fetch_ftp_logs(f_days=None, s_dt=None, e_dt=None, s_h=0, e_h=23):
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
                    if f_days and m_time < (now - timedelta(days=f_days)): keep = False
                    elif s_dt and e_dt and not (s_dt <= m_time.date() <= e_dt): keep = False
                    if not (s_h <= m_time.hour <= e_h): keep = False
                    if keep:
                        d_name = f"{filename} ({m_time.strftime('%m/%d %H:%M')})"
                        processed_files.append({"real": filename, "display": d_name, "time": m_time})
            st.session_state.all_logs = sorted(processed_files, key=lambda x: x['time'], reverse=True)
            ftp.quit()

    # ==============================================================================
    # SECTION 4: 🛠️ ADVANCED LOG FILTERING (RESTORED AREA SEARCH)
    # ==============================================================================
    def extract_v14_data(line):
        name, coords = "System", None
        try:
            if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
            if "pos=<" in line:
                raw = line.split("pos=<")[1].split(">")[0]
                pts = [p.strip() for p in raw.split(",")]
                coords = [float(pts[0]), float(pts[2])] 
        except: pass
        return name, coords

    def calculate_distance(p1, p2):
        if not p1 or not p2: return 999999
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def filter_v14_exact(files, mode, target_p=None, area_c=None, area_r=500):
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
        
        build_k = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
        raid_k = ["dismantled", "folded", "unmount", "unmounted", "packed"]
        sess_k = ["connected", "disconnected", "died", "killed"]
        boost_obj = ["fence kit", "nameless object", "fireplace", "garden plot"]
        boost_track = {}

        for line in all_content:
            if "|" not in line: continue
            name, coords = extract_v14_data(line)
            low, match = line.lower(), False
            if mode == "Full Activity per Player": match = (target_p == name)
            elif mode == "Area Activity Search" and coords and area_c:
                dist = calculate_distance(coords, area_c)
                match = (dist <= area_r)
            elif mode == "Building Only (Global)": match = any(k in low for k in build_k) and "pos=" in low
            elif mode == "Raid Watch (Global)": match = any(k in low for k in raid_k) and "pos=" in low
            elif mode == "Session Tracking (Global)": match = any(k in low for k in sess_k)
            elif mode == "Suspicious Boosting Activity" and any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boost_obj):
                t_str = line.split(" | ")[0][-8:]
                try:
                    t_val = datetime.strptime(t_str, "%H:%M:%S")
                    if name not in boost_track: boost_track[name] = []
                    boost_track[name].append({"time": t_val, "pos": coords})
                    if len(boost_track[name]) >= 3:
                        prev = boost_track[name][-3]
                        if (t_val - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                            match = True
                except: continue

            if match:
                raw_lines.append(line.strip())
                status = "connect" if "connect" in low else "disconnect" if "disconnect" in low else "death" if any(x in low for x in ["died", "killed"]) else "normal"
                if name not in report: report[name] = []
                report[name].append({"time": line.split(" | ")[0][-8:], "text": line.strip(), "status": status})
        return report, header + "\n".join(raw_lines)

    # ==============================================================================
    # SECTION 5: UI LAYOUT & SIDEBAR
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Dashboard")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        if st.button("🔌 Log Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()

        if st.session_state['current_user'] in ["cybersorfer", "Admin"]:
            with st.expander("🛡️ Security Audit"):
                try:
                    with open("login_history.txt", "r") as f: st.text_area("Audit Log", f.read(), height=200)
                except: st.write("No logs yet.")

        st.header("Nitrado FTP Manager")
        if st.button("🔄 Sync FTP List"): fetch_ftp_logs(); st.rerun()
        
        if 'all_logs' in st.session_state:
            # FEATURE: File Type Checkboxes
            st.subheader("Filter File Types:")
            cb_cols = st.columns(3)
            show_adm = cb_cols[0].checkbox("ADM", True)
            show_rpt = cb_cols[1].checkbox("RPT", True)
            show_log = cb_cols[2].checkbox("LOG", True)
            
            allowed_exts = []
            if show_adm: allowed_exts.append(".ADM")
            if show_rpt: allowed_exts.append(".RPT")
            if show_log: allowed_exts.append(".LOG")
            
            filtered_list = [f for f in st.session_state.all_logs if f['real'].upper().endswith(tuple(allowed_exts))]
            
            # FEATURE: Select All Visible
            select_all = st.checkbox("Select All Visible Files")
            
            selected_disp = st.multiselect(
                "Select Files for ZIP:", 
                options=[f['display'] for f in filtered_list],
                default=[f['display'] for f in filtered_list] if select_all else []
            )
            
            if selected_disp and st.button("📦 Prepare ZIP"):
                buf = io.BytesIO()
                ftp = get_ftp_connection()
                if ftp:
                    with zipfile.ZipFile(buf, "w") as zf:
                        for disp in selected_disp:
                            real = next(f['real'] for f in filtered_list if f['display'] == disp)
                            fbuf = io.BytesIO(); ftp.retrbinary(f"RETR {real}", fbuf.write); zf.writestr(real, fbuf.getvalue())
                    ftp.quit(); st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip")

    c_left, c_right = st.columns([1, 1.4])
    with c_left:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded = st.file_uploader("Browse Files", accept_multiple_files=True)
        if uploaded:
            mode = st.selectbox("Select Filter", ["Area Activity Search", "Full Activity per Player", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity"])
            t_p, a_c, a_r = None, None, 500
            if mode == "Full Activity per Player":
                p_list = set()
                for f in uploaded: f.seek(0); p_list.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
                t_p = st.selectbox("Select Player", sorted(list(p_list)))
            elif mode == "Area Activity Search":
                presets = {
                    "NWAF": [4530, 10245], "Tisy": [1542, 13915], "Zenit": [8355, 5978], 
                    "Gorka": [9494, 8820], "VMC": [3824, 8912], "Vybor": [3785, 8925], "Zeleno": [2575, 5175]
                }
                choice = st.selectbox("Quick Location", list(presets.keys()))
                a_c, a_r = presets[choice], st.slider("Radius", 50, 2000, 500)
            if st.button("🚀 PROCESS UPLOADED LOGS"):
                rep, raw = filter_v14_exact(uploaded, mode, t_p, a_c, a_r)
                st.session_state.res_rep, st.session_state.res_raw = rep, raw
        if "res_rep" in st.session_state and st.session_state.res_rep:
            st.download_button("💾 Download ADM", st.session_state.res_raw, "FILTERED.adm")
            for p, evs in st.session_state.res_rep.items():
                with st.expander(f"👤 {p}"):
                    for ev in evs: st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown("### 📍 iZurvive Map")
        if st.button("🔄 REFRESH MAP"): st.session_state.mv = st.session_state.get('mv', 0) + 1
        components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
