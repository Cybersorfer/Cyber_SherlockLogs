import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
import requests
from datetime import datetime, timedelta
import pytz 
import streamlit.components.v1 as components
import json

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
    # SECTION 2: GLOBAL CONFIG & NIGHT THEME
    # ==============================================================================
    st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
    
    if 'mv' not in st.session_state: st.session_state.mv = 0
    if 'track_data' not in st.session_state: st.session_state.track_data = None
    
    if 'map_click_x' not in st.session_state: st.session_state.map_click_x = 1542.0
    if 'map_click_y' not in st.session_state: st.session_state.map_click_y = 13915.0

    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { color: #8b949e !important; }
        div.stButton > button { color: #c9d1d9 !important; background-color: #21262d !important; border: 1px solid #30363d !important; font-weight: bold !important; border-radius: 6px; }
        .death-log { color: #ff7b72 !important; font-weight: bold; border-left: 3px solid #f85149; padding-left: 10px; margin-bottom: 5px;}
        .connect-log { color: #3fb950 !important; border-left: 3px solid #3fb950; padding-left: 10px; margin-bottom: 5px;}
        .live-log { color: #79c0ff !important; font-family: monospace; font-size: 0.85rem; background: #0d1117; border: 1px solid #30363d; padding: 5px; border-radius: 4px; margin-bottom: 2px;}
        div[data-testid="stExpander"] { background-color: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px; }
        </style>
        """, unsafe_allow_html=True)

    # ==============================================================================
    # SECTION 3: CORE LOGIC & FTP
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"
    NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
    NITRADO_SERVICE_ID = "18197890"
    SERVER_TZ = pytz.timezone('America/Los_Angeles')

    def get_ftp_connection():
        try:
            ftp = FTP(FTP_HOST, timeout=10)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.cwd(FTP_PATH)
            return ftp
        except: return None

    def make_izurvive_link(coords):
        if coords and len(coords) >= 2: return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
        return ""

    def extract_player_and_coords(line):
        name, coords = "System/Server", None
        try:
            if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
            if "pos=<" in line:
                raw = line.split("pos=<")[1].split(">")[0]
                parts = [p.strip() for p in raw.split(",")]
                coords = [float(parts[0]), float(parts[1])] 
        except: pass 
        return str(name), coords

    def calculate_distance(p1, p2):
        if not p1 or not p2: return 999999
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

    def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
        grouped_report, raw_filtered_lines = {}, []
        all_lines = []
        log_start_header = ""
        
        for uploaded_file in files:
            uploaded_file.seek(0)
            content = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
            
            # --- FEATURE: CAPTURE ORIGINAL LOG HEADER ---
            # Looks for "AdminLog started on YYYY-MM-DD at HH:MM:SS"
            if not log_start_header and content:
                for first_lines in content[:5]:
                    if "AdminLog started on" in first_lines:
                        log_start_header = first_lines.strip()
                        break
            
            all_lines.extend(content)

        building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
        raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
        session_keys = ["connected", "disconnected", "died", "killed"]

        for line in all_lines:
            if "|" not in line: continue
            time_part = line.split(" | ")[0]
            clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
            name, coords = extract_player_and_coords(line)
            low, should_process = line.lower(), False

            if mode == "Full Activity per Player" and target_player == name: should_process = True
            elif mode == "Building Only (Global)" and any(k in low for k in building_keys): should_process = True
            elif mode == "Raid Watch (Global)" and any(k in low for k in raid_keys): should_process = True
            elif mode == "Session Tracking (Global)" and any(k in low for k in session_keys): should_process = True
            elif mode == "Area Activity Search" and coords and area_coords and calculate_distance(coords, area_coords) <= area_radius: should_process = True

            if should_process:
                raw_filtered_lines.append(f"{line.strip()}\n") 
                status = "death" if any(d in low for d in ["died", "killed"]) else ("connect" if "connect" in low else "normal")
                event_entry = {"time": clean_time, "text": str(line.strip()), "link": make_izurvive_link(coords), "status": status}
                if name not in grouped_report: grouped_report[name] = []
                grouped_report[name].append(event_entry)
        
        # Prepend the captured header to the raw output
        final_raw = ""
        if log_start_header:
            final_raw = f"{log_start_header}\n" + "".join(raw_filtered_lines)
        else:
            final_raw = "".join(raw_filtered_lines)
            
        return grouped_report, final_raw

    # ==============================================================================
    # SECTION 5: MAIN CONTENT
    # ==============================================================================
    col1, col2 = st.columns([1, 2.3])

    with col1:
        st.markdown("### 🛠️ Advanced Log Filtering")
        uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
        if uploaded_files:
            mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Area Activity Search"])
            
            t_p, area_coords, area_radius = None, None, 500
            
            if mode == "Full Activity per Player":
                all_names = []
                for f in uploaded_files:
                    f.seek(0)
                    all_names.extend([l.split('"')[1] for l in f.read().decode("utf-8", errors="ignore").splitlines() if 'Player "' in l])
                t_p = st.selectbox("Select Player", sorted(list(set(all_names))))
                
            elif mode == "Area Activity Search":
                st.write("📋 **Paste from iSurvive Serverlogs Map:**")
                raw_paste = st.text_input("e.g. 4823.45 / 6129.29", placeholder="Paste coordinates here...")
                
                if raw_paste:
                    try:
                        extracted = re.findall(r"[-+]?\d*\.\d+|\d+", raw_paste)
                        if len(extracted) >= 2:
                            st.session_state.map_click_x = float(extracted[0])
                            st.session_state.map_click_y = float(extracted[1])
                            st.success(f"Parsed: X={extracted[0]}, Y={extracted[1]}")
                    except:
                        st.error("Format error. Use: 'X / Y'")

                cx = st.number_input("Center X", value=float(st.session_state.map_click_x), format="%.2f")
                cy = st.number_input("Center Y", value=float(st.session_state.map_click_y), format="%.2f")
                
                area_coords = [cx, cy]
                area_radius = st.slider("Search Radius (m)", 50, 2000, 500)

            if st.button("🚀 Process Logs", use_container_width=True):
                report, raw = filter_logs(uploaded_files, mode, t_p, area_coords, area_radius)
                st.session_state.track_data = report
                st.session_state.raw_download = raw
        
        if st.session_state.get("track_data"):
            st.download_button("💾 Download Filtered ADM", st.session_state.raw_download, "FILTERED.adm", use_container_width=True)
            for p in sorted(st.session_state.track_data.keys()):
                with st.expander(f"👤 {p}"):
                    for ev in st.session_state.track_data[p]:
                        status_class = f"{ev['status']}-log"
                        st.markdown(f"<div class='{status_class}'>{ev['text']}</div>", unsafe_allow_html=True)
                        if ev['link']: st.link_button("📍 Map", ev['link'])

    with col2:
        st.markdown(f"<h4 style='text-align: center;'>📍 iSurvive Live Map</h4>", unsafe_allow_html=True)
        
        bridge_js = f"""
            <script>
            window.addEventListener('message', function(event) {{
                if (event.data && event.data.coords) {{
                    const coords = event.data.coords;
                    const url = new URL(window.location.href);
                    url.searchParams.set('map_x', coords[0]);
                    url.searchParams.set('map_y', coords[1]);
                    window.parent.location.href = url.href;
                }}
            }});
            </script>
        """
        components.html(bridge_js, height=0)
        
        params = st.query_params
        if "map_x" in params and "map_y" in params:
            new_x = float(params["map_x"])
            new_y = float(params["map_y"])
            if new_x != st.session_state.map_click_x or new_y != st.session_state.map_click_y:
                st.session_state.map_click_x = new_x
                st.session_state.map_click_y = new_y
                st.rerun()

        cm1, cm2, cm3 = st.columns([1, 1, 1])
        if cm2.button("🔄 Refresh Map", use_container_width=True):
            st.session_state.mv += 1; st.rerun()
        
        components.iframe(f"https://www.izurvive.com/chernarusplus/?v={st.session_state.mv}", height=800, scrolling=True)
