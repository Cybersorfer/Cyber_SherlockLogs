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

# --- 2. CSS: UI TEXT VISIBILITY & BUTTON FIXES ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; }
    
    /* Force all text labels and descriptions to be visible */
    label, p, span, .stMarkdown, .stCaption { color: #ffffff !important; font-weight: 500 !important; }
    
    /* Fix Button Text Visibility */
    div.stButton > button {
        color: #ffffff !important;
        background-color: #262730 !important;
        border: 1px solid #4b4b4b !important;
        font-weight: bold !important;
    }
    
    /* Expander text fix */
    .streamlit-expanderHeader { color: #ffffff !important; background-color: #161b22 !important; }
    
    /* Log Activity Colors from your script */
    .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; }
    .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE LOGIC (SYNCED WITH YOUR FILE) ---
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

# --- 4. FILTER LOGIC (EXACT SYNC WITH CyberDayZlogsScanne14 (8).py) ---
def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, raw_filtered_lines = {}, []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for uploaded_file in files:
        # HANDLE ZIP FILES OR INDIVIDUAL LOGS
        if uploaded_file.name.endswith('.zip'):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for n in z.namelist():
                    if n.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        all_lines.extend(z.read(n).decode("utf-8", errors="ignore").splitlines())
        else:
            uploaded_file.seek(0)
            all_lines.extend(uploaded_file.read().decode("utf-8", errors="ignore").splitlines())

    # Keys from your specific logic
    building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    session_keys = ["connected", "disconnected", "died", "killed"]
    boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]
    boosting_tracker = {}

    for line in all_lines:
        if "|" not in line: continue
        name, coords = extract_player_and_coords(line)
        low = line.lower()
        should_process = False

        if mode == "Full Activity per Player":
            if target_player == name: should_process = True
        elif mode == "Building Only (Global)":
            if any(k in low for k in building_keys) and "pos=" in low: should_process = True
        elif mode == "Raid Watch (Global)":
            if any(k in low for k in raid_keys) and "pos=" in low: should_process = True
        elif mode == "Session Tracking (Global)":
            if any(k in low for k in session_keys): should_process = True
        elif mode == "Area Activity Search":
            if coords and area_coords:
                if calculate_distance(coords, area_coords) <= area_radius: should_process = True
        elif mode == "Suspicious Boosting Activity":
            if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                time_part = line.split(" | ")[0][-8:]
                try: current_time = datetime.strptime(time_part, "%H:%M:%S")
                except: continue
                if name not in boosting_tracker: boosting_tracker[name] = []
                boosting_tracker[name].append({"time": current_time, "pos": coords})
                if len(boosting_tracker[name]) >= 3:
                    prev = boosting_tracker[name][-3]
                    if (current_time - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                        should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            status = "normal"
            if any(d in low for d in ["died", "killed"]): status = "death"
            elif "connect" in low: status = "connect"
            elif "disconnect" in low: status = "disconnect"
            
            entry = {"time": line.split(" | ")[0][-8:], "text": line.strip(), "link": make_izurvive_link(coords), "status": status}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(entry)
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- 5. UI LAYOUT ---
col_left, col_right = st.columns([1, 1.4])

with col_left:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Upload Admin Logs (.ADM, .RPT, .ZIP)", accept_multiple_files=True)
    
    if uploaded:
        mode = st.selectbox("Select Filter", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
        
        target_player, area_coords, area_radius = None, None, 500
        
        if mode == "Full Activity per Player":
            # Extract player names for the dropdown
            names = set()
            for f in uploaded:
                f.seek(0)
                content = f.read().decode("utf-8", errors="ignore")
                names.update(re.findall(r'Player "([^"]+)"', content))
            target_player = st.selectbox("Select Player", sorted(list(names)))
            
        elif mode == "Area Activity Search":
            presets = {"NWAF": [4530, 10245], "Tisy": [1542, 13915], "VMC": [3824, 8912], "Zenit": [8355, 5978]}
            choice = st.selectbox("Quick Locations", list(presets.keys()))
            area_coords = presets[choice]
            area_radius = st.slider("Search Radius (Meters)", 50, 2000, 500)

        if st.button("🚀 Process Logs"):
            report, raw_file = filter_logs(uploaded, mode, target_player, area_coords, area_radius)
            st.session_state.report = report
            st.session_state.raw = raw_file

    if "report" in st.session_state and st.session_state.report:
        st.download_button("💾 Download Filtered ADM", data=st.session_state.raw, file_name="FILTERED_LOGS.adm")
        for p in sorted(st.session_state.report.keys()):
            with st.expander(f"👤 {p}"):
                for ev in st.session_state.report[p]:
                    st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)
                    if ev['link']: st.link_button("📍 Map", ev['link'])

with col_right:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=850, scrolling=True)

# SIDEBAR FTP MANAGER (STAYS SAME)
with st.sidebar:
    st.header("Nitrado Manager")
    # ... (Include your previous FTP retrieval and multi-select download logic here)
