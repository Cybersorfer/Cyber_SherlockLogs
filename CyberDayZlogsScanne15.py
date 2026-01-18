import streamlit as st
import io
import math
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Tightened CSS: Push content to absolute top and fix independent scrolling
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        max-width: 100%;
    }

    /* Pull logo higher and ensure it doesn't collide with column headers */
    [data-testid="stMarkdownContainer"] h4 {
        margin-top: -25px !important;
        margin-bottom: 5px !important;
        position: relative;
        z-index: 1001;
    }

    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid="stHorizontalBlock"] {
            height: 96vh;
            margin-top: -20px; 
        }
        [data-testid="column"] {
            height: 100% !important;
            overflow-y: auto !important;
            padding-top: 20px; /* Space inside columns to prevent header overlap */
            border: 1px solid #31333F;
            border-radius: 8px;
        }
    }

    /* Mobile View */
    @media (max-width: 767px) {
        [data-testid="column"] {
            height: 450px !important;
            overflow-y: scroll !important;
            border: 1px solid #31333F;
            margin-bottom: 10px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Geodata Coordinate Math
def extract_coords(line):
    """Pulls x and y from DayZ log pos=<X, Z, Y> format"""
    try:
        if "pos=<" in line:
            raw_pos = line.split("pos=<")[1].split(">")[0]
            parts = raw_pos.split(",")
            # DayZ Logs are X, Height, Y. We need X (0) and Y (2).
            return [float(parts[0].strip()), float(parts[2].strip())]
    except:
        return None
    return None

def get_distance(pos1, pos2):
    """Euclidean distance formula"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# 4. Updated CHERNARUS GEODATA (X, Y, Radius)
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": (13470, 13075, 1000),
    "Severograd (Североград)": (11000, 12400, 800),
    "Zelenogorsk (Зеленогорск)": (2700, 5200, 800),
    "Stary Sobor (Старый Собор)": (6100, 7600, 500),
    "Novy Sobor (Новый Собор)": (7000, 7600, 400),
    "Gorka (Горка)": (9500, 6500, 500),
    "Vybor (Выбор)": (3800, 8900, 400),
    "Radio Zenit / Altar": (4200, 8600, 400),
    "Krasnostav (Красностав)": (11100, 13000, 600),
    "Tisy Military Base": (11500, 14200, 800),
    "Rify Shipwreck": (13400, 9200, 500),
    "Prison Island": (2100, 1300, 600),
    "Berezino (Березино)": (12900, 9200, 1000),
    "Chernogorsk (Черногорск)": (6700, 2500, 1200),
    "Elektrozavodsk (Электрозаводск)": (10300, 2300, 1000),
}

# 5. Filter Logic
def filter_logs(files, town_choice):
    final_output = []
    header = "AdminLog started on 00:00:00\n***********************\n"
    
    target_center, target_y, radius = CHERNARUS_LOCATIONS[town_choice]
    center_point = [target_center, target_y]

    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        for line in content.splitlines():
            if "pos=<" in line:
                line_pos = extract_coords(line)
                if line_pos and get_distance(line_pos, center_point) <= radius:
                    final_output.append(line)

    return header + "\n".join(final_output)

# --- WEB UI ---
if "map_v" not in st.session_state: st.session_state.map_v = 0
if "filter_res" not in st.session_state: st.session_state.filter_res = None

st.markdown("#### 🛡️ CyberDayZ Scanner")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM Files", type=['adm', 'rpt'], accept_multiple_files=True)
    
    selected_town = st.selectbox("Select Town Geodata:", list(CHERNARUS_LOCATIONS.keys()))
    
    if st.button("🚀 Process Geodata"):
        if uploaded_files:
            st.session_state.filter_res = filter_logs(uploaded_files, selected_town)
            st.success(f"Found {len(st.session_state.filter_res.splitlines()) - 2} events near {selected_town}!")
        else:
            st.error("Please upload files first.")

    if st.session_state.filter_res:
        st.download_button(
            label=f"💾 Download {selected_town} ADM",
            data=st.session_state.filter_res,
            file_name=f"{selected_town}_filtered.adm"
        )

with col2:
    cm1, cm2 = st.columns([3, 1])
    with cm1: st.write("**2. iZurvive Map**")
    with cm2: 
        if st.button("🔄 Refresh"): st.session_state.map_v += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_v}"
    components.iframe(map_url, height=1000, scrolling=True)
