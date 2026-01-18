import streamlit as st
import io
import math
import streamlit.components.v1 as components

st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 1. Ultra-Tight CSS
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 100%; }
    [data-testid="stMarkdownContainer"] h4 { margin-top: -25px !important; margin-bottom: 5px !important; }
    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid="stHorizontalBlock"] { height: 98vh; margin-top: -25px; }
        [data-testid="column"] { height: 100% !important; overflow-y: auto !important; padding-top: 15px; border: 1px solid #31333F; border-radius: 8px; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Location Helper Functions
def extract_coords(line):
    """DayZ logs use: pos=<X, Z, Y>. iZurvive needs the X (index 0) and Y (index 2)"""
    try:
        if "pos=<" in line:
            raw_pos = line.split("pos=<")[1].split(">")[0]
            parts = raw_pos.split(",")
            return [float(parts[0].strip()), float(parts[2].strip())]
    except:
        return None
    return None

def get_distance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# Location Coords (X, Y)
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": ([12134, 12634], 1500),
    "VMC (Base)": ([7960, 5990], 600),
    "Tisy Military": ([1700, 13900], 1200),
}

# 3. FIXED Filter Logic for iZurvive
def filter_logs(files, main_choice, target_player=None, town_choice=None):
    final_output = []
    
    # CRITICAL: This exact header is required for iZurvive to trigger its map plotter
    header = "AdminLog started on 00:00:00\n" 
    header += "******************************************************************************\n"

    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        lines = content.splitlines()
        
        town_coords, town_radius = (None, 0)
        if main_choice == "Activity Near Specific Town" and town_choice in CHERNARUS_LOCATIONS:
            town_coords, town_radius = CHERNARUS_LOCATIONS[town_choice]

        for line in lines:
            # iZurvive only cares about lines that have a timestamp and position
            if ":" in line and "|" in line and "pos=<" in line:
                
                if town_coords:
                    line_coords = extract_coords(line)
                    if line_coords and get_distance(line_coords, town_coords) <= town_radius:
                        final_output.append(line)
                elif target_player and target_player in line:
                    final_output.append(line)
                elif main_choice == "Everything with Coordinates":
                    final_output.append(line)
                elif main_choice == "All Death Locations" and any(x in line.lower() for x in ["killed", "died", "suicide"]):
                    final_output.append(line)

    # Clean the output to ensure NO empty lines which can break the iZurvive parser
    cleaned_output = [l for l in final_output if l.strip()]
    return header + "\n".join(cleaned_output)

# --- WEB UI ---
if "filtered_result" not in st.session_state: st.session_state.filtered_result = None
if "map_version" not in st.session_state: st.session_state.map_version = 0

st.markdown("#### 🛡️ CyberDayZ Scanner")
col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("")
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Select Filter Feature", ["Everything with Coordinates", "Activity Near Specific Town", "Activity per Specific Player", "All Death Locations"])
        
        target_player = None
        town_choice = None

        if mode == "Activity Near Specific Town":
            town_choice = st.selectbox("Select Town/Area", list(CHERNARUS_LOCATIONS.keys()))
        elif mode == "Activity per Specific Player":
            temp_all = []
            for f in uploaded_files: temp_all.extend(f.getvalue().decode("utf-8", errors="ignore").splitlines())
            player_list = sorted(list(set(line.split('"')[1] for line in temp_all if 'Player "' in line)))
            target_player = st.selectbox("Select Player", player_list)

        if st.button("🚀 Process"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, town_choice)
            st.success(f"Done! Found {len(st.session_state.filtered_result.splitlines()) - 2} events.")

    if st.session_state.filtered_result:
        st.download_button(label="💾 Download for Map", data=st.session_state.filtered_result, file_name="IZURVIVE_FIXED.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: st.write("") ; st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"): st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
