import streamlit as st
import io
import math
import streamlit.components.v1 as components

st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# Fixed CSS Block
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;} 
    header {visibility: hidden;} 
    footer {visibility: hidden;}
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 100%; }
    [data-testid='stMarkdownContainer'] h4 { margin-top: -25px !important; margin-bottom: 5px !important; }
    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid='stHorizontalBlock'] { height: 98vh; margin-top: -25px; }
        [data-testid='column'] { height: 100% !important; overflow-y: auto !important; padding-top: 15px; border: 1px solid #31333F; border-radius: 8px; }
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# Geodata with your requested locations
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": (13470, 13075),
    "Severograd": (11000, 12400),
    "Zelenogorsk": (2700, 5200),
    "Stary Sobor": (6100, 7600),
    "Novy Sobor": (7000, 7600),
    "Gorka": (9500, 6500),
    "Vybor": (3800, 8900),
    "Tisy Military Base": (11500, 14200),
    "Berezino": (12900, 9200),
    "Chernogorsk": (6700, 2500),
    "Elektrozavodsk": (10300, 2300),
}

def extract_coords(line):
    try:
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [float(p.strip()) for p in raw.split(",")]
            # DayZ logs are X, Height, Y. We return [X, Y]
            return [parts[0], parts[2]]
    except:
        return None
    return None

def filter_logs(files, town_choice, radius):
    final_output = []
    header = "AdminLog started on 00:00:00\n***********************\n"
    target_x, target_y = CHERNARUS_LOCATIONS[town_choice]
    
    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        for line in content.splitlines():
            if "pos=<" in line:
                line_pos = extract_coords(line)
                if line_pos:
                    dist = math.sqrt((line_pos[0] - target_x)**2 + (line_pos[1] - target_y)**2)
                    if dist <= radius:
                        final_output.append(line)
    return header + "\n".join(final_output)

# UI Logic
st.markdown("#### 🛡️ CyberDayZ Scanner")
col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM Files", accept_multiple_files=True)
    selected_town = st.selectbox("Select Town:", list(CHERNARUS_LOCATIONS.keys()))
    search_radius = st.slider("Search Radius (meters):", 100, 5000, 1000)
    
    if st.button("🚀 Process"):
        if uploaded_files:
            res = filter_logs(uploaded_files, selected_town, search_radius)
            st.session_state.filter_res = res
            st.success(f"Found {len(res.splitlines()) - 2} events!")
        else:
            st.error("Upload files first.")

    if "filter_res" in st.session_state and st.session_state.filter_res:
        st.download_button("💾 Download for iZurvive", st.session_state.filter_res, "MAP_READY.adm")

with col2:
    if st.button("🔄 Refresh Map"):
        st.session_state.map_v = st.session_state.get('map_v', 0) + 1
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('map_v', 0)}"
    components.iframe(map_url, height=1000, scrolling=True)
