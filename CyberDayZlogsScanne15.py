import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Ultra-Tight CSS: Forces everything to the absolute top
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

    /* Pull logo higher to avoid overlap */
    [data-testid="stMarkdownContainer"] h4 {
        margin-top: -25px !important;
        margin-bottom: 5px !important;
    }

    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid="stHorizontalBlock"] {
            height: 98vh;
            margin-top: -25px; 
        }
        [data-testid="column"] {
            height: 100% !important;
            overflow-y: auto !important;
            padding-top: 10px;
            border: 1px solid #31333F;
            border-radius: 8px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Location Data (Fixing the ValueError)
# Ensure every town listed in your selectbox exists here exactly
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": ([12134, 12634], 1500),
    "VMC": ([12134, 12634], 500),
    "Tisy": ([12134, 12634], 1000)
}

if "filtered_result" not in st.session_state:
    st.session_state.filtered_result = None
if "map_version" not in st.session_state:
    st.session_state.map_version = 0

def filter_logs(files, main_choice, target_player=None, sub_choice=None):
    all_lines = []
    header = "******************************************************************************\n"
    header += "AdminLog started on Web_Filter_Session\n"
    for uploaded_file in files:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
        for line in stringio:
            if "|" in line and ":" in line:
                all_lines.append(line)
    return header + "".join(all_lines)

# --- WEB UI ---
st.markdown("#### 🛡️ CyberDayZ Scanner")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("") # Spacer to prevent overlap
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM", type=['adm', 'rpt'], accept_multiple_files=True)

    # TOWN EXTRACTION TOOL (The part that caused the error)
    st.write("**Town Search Tool**")
    town = st.selectbox("Select Map Area", list(CHERNARUS_LOCATIONS.keys()))
    
    # FIX: Check if town exists before accessing to prevent ValueError
    if town in CHERNARUS_LOCATIONS:
        coords, radius = CHERNARUS_LOCATIONS[town]
        st.caption(f"Searching area: {town}")

    if st.button("🚀 Process"):
        st.session_state.filtered_result = filter_logs(uploaded_files, "Global")

    if st.session_state.filtered_result:
        st.download_button(label="💾 Download ADM", data=st.session_state.filtered_result, file_name="FOR_MAP.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.write("") 
        st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"):
            st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
