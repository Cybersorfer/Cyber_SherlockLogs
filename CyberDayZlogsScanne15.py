import streamlit as st
import io
import math
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Tightened CSS: Fixes overlap and pushes content to the absolute top
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100%;
    }

    [data-testid='stMarkdownContainer'] h4 {
        margin-top: -15px !important;
        margin-bottom: 10px !important;
    }

    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid='stHorizontalBlock'] {
            height: 98vh;
            margin-top: -20px;
        }
        [data-testid='column'] {
            height: 100% !important;
            overflow-y: auto !important;
            padding-top: 15px;
            border: 1px solid #31333F;
            border-radius: 8px;
        }
    }

    @media (max-width: 767px) {
        [data-testid='column'] {
            height: 450px !important;
            overflow-y: scroll !important;
            border: 1px solid #31333F;
            margin-bottom: 10px;
        }
    }

    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-thumb { background-color: #4b4b4b; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Geodata Locations (X, Y)
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": (13470, 13075),
    "Severograd (Североград)": (11000, 12400),
    "Zelenogorsk (Зеленогорск)": (2700, 5200),
    "Stary Sobor (Старый Собор)": (6100, 7600),
    "Novy Sobor (Новый Собор)": (7000, 7600),
    "Gorka (Горка)": (9500, 6500),
    "Vybor (Выбор)": (3800, 8900),
    "Radio Zenit / Altar": (4200, 8600),
    "Krasnostav (Красностав)": (11100, 13000),
    "Tisy Military Base": (11500, 14200),
    "Rify Shipwreck": (13400, 9200),
    "Prison Island": (2100, 1300),
    "Berezino (Березино)": (12900, 9200),
    "Chernogorsk (Черногорск)": (6700, 2500),
    "Elektrozavodsk (Электрозаводск)": (10300, 2300),
}

# 4. Helper Functions
def extract_coords(line):
    try:
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [float(p.strip()) for p in raw.split(",")]
            # DayZ logs: X, Z(height), Y. We need X and Y.
            return [parts[0], parts[2]]
    except:
        return None
    return None

def filter_logs(files, main_choice, target_player=None, sub_choice=None, town_choice=None, radius=1000):
    final_output = []
    header = "AdminLog started on 00:00:00\n******************************************************************************\n"
    
    target_town_coords = CHERNARUS_LOCATIONS.get(town_choice) if town_choice else None
    
    all_lines = []
    for uploaded_file in files:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
        all_lines.extend(stringio.readlines())

    placement_keys = ["placed", "built", "folded", "shelterfabric", "mounted"]
    session_keys = ["connected", "disconnected", "lost connection", "choosing to respawn"]
    raid_keys = ["dismantled", "unmount", "packed", "barbedwirehit", "fireplace", "gardenplot", "fence kit"]

    for line in all_lines:
        if "|" not in line or ":" not in line:
            continue
            
        low = line.lower()
        
        # Geodata Filter Logic
        if main_choice == "Activity Near Specific Town" and target_town_coords:
            line_pos = extract_coords(line)
            if line_pos:
                dist = math.sqrt((line_pos[0] - target_town_coords[0])**2 + (line_pos[1] - target_town_coords[1])**2)
                if dist <= radius:
                    final_output.append(line)
            continue

        # Existing Filter Logic
        if main_choice == "Activity per Specific Player" and target_player:
            if target_player in line:
                if sub_choice == "Full History": final_output.append(line)
                elif sub_choice == "Movement Only" and "pos=" in low: final_output.append(line)
                elif sub_choice == "Movement + Building":
                    if ("pos=" in low or any(k in low for k in placement_keys)) and "hit" not in low:
                        final_output.append(line)
                elif sub_choice == "Movement + Raid Watch":
                    if ("pos=" in low or any(k in low for k in raid_keys)) and "built" not in low:
                        final_output.append(line)

        elif main_choice == "All Death Locations":
            if any(x in low for x in ["killed", "died", "suicide", "bled out"]): final_output.append(line)
        elif main_choice == "All Placements":
            if any(x in low for x in placement_keys): final_output.append(line)
        elif main_choice == "Session Tracking (Global)":
            if any(x in low for x in session_keys): final_output.append(line)
        elif main_choice == "RAID WATCH (Global)":
            if any(x in low for x in raid_keys) and "built" not in low: final_output.append(line)

    final_output.sort()
    return header + "".join(final_output)

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
        mode = st.selectbox("Select Filter", [
            "Activity Near Specific Town", "Activity per Specific Player", 
            "All Death Locations", "All Placements", "Session Tracking (Global)", "RAID WATCH (Global)"
        ])

        target_player = None
        sub_choice = None
        town_choice = None
        radius_choice = 1000

        if mode == "Activity Near Specific Town":
            town_choice = st.selectbox("Select Town Geodata", list(CHERNARUS_LOCATIONS.keys()))
            radius_choice = st.slider("Search Radius (meters)", 100, 5000, 1000)

        elif mode == "Activity per Specific Player":
            temp_all = []
            for f in uploaded_files:
                temp_all.extend(f.getvalue().decode("utf-8", errors="ignore").splitlines())
            player_list = sorted(list(set(line.split('"')[1] for line in temp_all if 'Player "' in line)))
            target_player = st.selectbox("Select Player", player_list)
            sub_choice = st.radio("Detail", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice, town_choice, radius_choice)
            st.success(f"Done! Found {len(st.session_state.filtered_result.splitlines()) - 2} events.")

    if st.session_state.filtered_result:
        st.download_button(label="💾 Download ADM", data=st.session_state.filtered_result, file_name="CYBER_SCAN.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.write("") 
        st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"): st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
