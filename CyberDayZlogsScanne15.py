import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Tightened CSS: Fixes overlap and pushes content to the absolute top
st.markdown(
    """
    <style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Remove padding from the main container */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100%;
    }

    /* Fixed alignment for the title and columns */
    [data-testid="stMarkdownContainer"] h4 {
        margin-top: -15px !important; /* Pull the main logo/title higher */
        margin-bottom: 10px !important;
    }

    /* DESKTOP VIEW: Independent Columns */
    @media (min-width: 768px) {
        .main {
            overflow: hidden;
        }
        [data-testid="stHorizontalBlock"] {
            height: 98vh;
            margin-top: -20px; /* Pulls columns up to meet the title */
        }
        [data-testid="column"] {
            height: 100% !important;
            overflow-y: auto !important;
            padding-top: 15px; /* Adds space inside the border so text doesn't touch the top */
            border: 1px solid #31333F;
            border-radius: 8px;
        }
    }

    /* MOBILE VIEW: Individual scroll zones */
    @media (max-width: 767px) {
        [data-testid="column"] {
            height: 450px !important;
            overflow-y: scroll !important;
            border: 1px solid #31333F;
            margin-bottom: 10px;
        }
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #4b4b4b;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Initialize Session State
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

    final_output = []
    placement_keys = ["placed", "built", "folded", "shelterfabric", "mounted"]
    session_keys = ["connected", "disconnected", "lost connection", "choosing to respawn"]
    raid_keys = ["dismantled", "unmount", "packed", "barbedwirehit", "fireplace", "gardenplot", "fence kit"]

    if main_choice == "Activity per Specific Player" and target_player:
        for line in all_lines:
            low = line.lower()
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
        final_output = [l for l in all_lines if any(x in l.lower() for x in ["killed", "died", "suicide", "bled out"])]
    elif main_choice == "All Placements":
        final_output = [l for l in all_lines if any(x in l.lower() for x in placement_keys)]
    elif main_choice == "Session Tracking (Global)":
        final_output = [l for l in all_lines if any(x in l.lower() for x in session_keys)]
    elif main_choice == "RAID WATCH (Global)":
        final_output = [l for l in all_lines if any(x in l.lower() for x in raid_keys) and "built" not in l.lower()]

    final_output.sort()
    return header + "".join(final_output)

# --- WEB UI ---
# The main logo/title - CSS pulls this to the top
st.markdown("#### 🛡️ CyberDayZ Scanner")

col1, col2 = st.columns([1, 2.5])

with col1:
    # Adding a small space to ensure "1. Filter Logs" doesn't touch the top border
    st.write("") 
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Select Filter", [
            "Activity per Specific Player", "All Death Locations", 
            "All Placements", "Session Tracking (Global)", "RAID WATCH (Global)"
        ])

        target_player = None
        sub_choice = None

        if mode == "Activity per Specific Player":
            temp_all = []
            for f in uploaded_files:
                temp_all.extend(f.getvalue().decode("utf-8", errors="ignore").splitlines())
            player_list = sorted(list(set(line.split('"')[1] for line in temp_all if 'Player "' in line)))
            target_player = st.selectbox("Select Player", player_list)
            sub_choice = st.radio("Detail", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice)

    if st.session_state.filtered_result:
        st.download_button(label="💾 Download ADM", data=st.session_state.filtered_result, file_name="FOR_MAP.adm")

with col2:
    # Layout row for the map header and refresh button
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.write("") 
        st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"):
            st.session_state.map_version += 1
    
    # Map with dynamic versioning to avoid refresh errors
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
