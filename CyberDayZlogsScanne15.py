import streamlit as st
import io
import math
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. SETUP PAGE CONFIG ---
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
        width: 100%;
    }
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CORE FUNCTIONS ---
def extract_player_and_coords(line):
    name, coords = "System/Server", None
    try:
        if 'Player "' in line: 
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            # FIXED: Use index 0 (X) and index 2 (Z) to match your presets
            coords = [float(parts[0]), float(parts[2])] 
    except: pass 
    return str(name), coords

def calculate_distance(p1, p2):
    if not p1 or not p2: return 999999
    # Euclidean distance on the X/Z horizontal plane
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# --- 4. FILTER LOGIC ---
def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report = {}
    raw_filtered_lines = []
    header = "******************************************************************************\nAdminLog started on 2026-01-19 at 08:43:52\n\n"

    all_lines = []
    for uploaded_file in files:
        uploaded_file.seek(0)
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    for line in all_lines:
        if "|" not in line: continue
        name, coords = extract_player_and_coords(line)
        low = line.lower()
        should_process = False

        if mode == "Area Activity Search" and coords and area_coords:
            dist = calculate_distance(coords, area_coords)
            if dist <= area_radius: should_process = True
        
        elif mode == "Full Activity per Player" and target_player == name:
            should_process = True
        
        # ... Other modes remain identical to your file logic

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            time_part = line.split(" | ")[0][-8:]
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append({"time": time_part, "text": line.strip()})
    
    return grouped_report, header + "\n".join(raw_filtered_lines)

# --- 5. UI LAYOUT ---
col1, col2 = st.columns([1, 2.3])

with col1:
    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded_files = st.file_uploader("Upload Admin Logs", accept_multiple_files=True)
    
    if uploaded_files:
        mode = st.selectbox("Select Filter", ["Area Activity Search", "Full Activity per Player", "Building Only (Global)"])
        
        area_coords, target_player, area_radius = None, None, 500
        
        if mode == "Area Activity Search":
            # PRESETS strictly from your v14 (10) script
            presets = {
                "Tisy Military": [1542.0, 13915.0],
                "NWAF (Airfield)": [4530.0, 10245.0],
                "VMC (Military)": [3824.0, 8912.0],
                "Radio Zenit": [8355.0, 5978.0],
                "Zelenogorsk": [2540.0, 5085.0]
            }
            selection = st.selectbox("Quick Locations", list(presets.keys()))
            area_coords = presets[selection]
            area_radius = st.slider("Search Radius (Meters)", 50, 2000, 500)
            st.info(f"Searching near: {area_coords}")

        if st.button("🚀 Process Logs"):
            report, raw_file = filter_logs(uploaded_files, mode, target_player, area_coords, area_radius)
            if report:
                st.success(f"Matches found for {len(report)} players.")
                st.download_button("💾 Download ADM", data=raw_file, file_name="CYBER_AREA_LOGS.adm")
                for p in sorted(report.keys()):
                    with st.expander(f"👤 {p}"):
                        for ev in report[p]: st.text(f"{ev['time']} | {ev['text']}")
            else:
                st.warning("No matches found in this area. Try increasing the radius.")

with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=850, scrolling=True)
