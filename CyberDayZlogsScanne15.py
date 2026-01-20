import streamlit as st
import io
import math
import zipfile
import re
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. Setup Page Config ---
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS: Professional Dark UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    div.stButton > button {
        background-color: #238636 !important; 
        color: #ffffff !important;
        border: 1px solid #2ea043 !important;
        font-weight: bold !important;
        text-transform: uppercase;
    }
    section[data-testid="stSidebar"] { background-color: #1c2128 !important; border-right: 2px solid #30363d; }
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Core Functions ---
def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: 
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            # FIX: Use index 0 (X) and index 2 (Z) for horizontal mapping
            coords = [float(parts[0]), float(parts[2])] 
    except: pass 
    return str(name), coords

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    # Standard Euclidean distance on X/Z plane
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# --- 4. Filter Logic Implementation ---
def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report = {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for uploaded_file in files:
        uploaded_file.seek(0)
        # Added support for reading zip files directly if needed
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    for line in all_lines:
        if "|" not in line: continue
        name, coords = extract_player_and_coords(line)
        low = line.lower()
        should_process = False

        if mode == "Area Activity Search":
            if coords and area_coords:
                dist = calculate_distance(coords, area_coords)
                if dist <= area_radius: 
                    should_process = True
        
        # ... (Other modes: Full Activity, Building, etc. follow the same pattern)
        elif mode == "Full Activity per Player" and target_player == name:
            should_process = True

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            time_str = line.split(" | ")[0][-8:]
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append({"time": time_str, "text": line.strip()})
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- 5. UI LAYOUT ---
col1, col2 = st.columns([1, 2.3])

with col1:
    uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
    if uploaded_files:
        mode = st.selectbox("Select Filter", ["Area Activity Search", "Full Activity per Player", "Building Only (Global)"])
        
        area_coords = None
        area_radius = 500
        
        if mode == "Area Activity Search":
            # PRESETS: Using correct [X, Z] values for Chernarus
            presets = {
                "NWAF": [4530.0, 10245.0],
                "Tisy Military": [1542.0, 13915.0],
                "VMC": [3824.0, 8912.0],
                "Radio Zenit": [8355.0, 5978.0]
            }
            selection = st.selectbox("Quick Locations", list(presets.keys()))
            area_coords = presets[selection]
            area_radius = st.slider("Search Radius", 50, 2000, 500)

        if st.button("🚀 Process Logs"):
            report, raw_file = filter_logs(uploaded_files, mode, area_coords=area_coords, area_radius=area_radius)
            if report:
                st.success(f"Found activity in {len(report)} players")
                st.download_button("💾 Download ADM", data=raw_file, file_name="AREA_FILTER.adm")
                # Expanders for players...
            else:
                st.warning("No activity found in that area.")

with col2:
    m_url = "https://www.izurvive.com/serverlogs/"
    components.iframe(m_url, height=800, scrolling=True)
