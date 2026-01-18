import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Advanced CSS: Move content to the TOP, hide header, and fix mobile scrolling
st.markdown(
    """
    <style>
    /* Hide the Streamlit Header and Padding at the top */
    header {visibility: hidden;}
    .main .block-container {
        max-width: 100%;
        padding-top: 0rem !important;
        padding-bottom: 0rem;
        height: 100vh;
    }

    /* DESKTOP VIEW: Independent Columns */
    @media (min-width: 768px) {
        .main .block-container {
            overflow: hidden; /* Prevent global scroll on desktop */
        }
        [data-testid="stHorizontalBlock"] {
            height: 98vh; /* Maximize height usage */
        }
        [data-testid="column"] {
            height: 100% !important;
            overflow-y: auto !important;
            padding-right: 10px;
            border: 1px solid #31333F;
            border-radius: 8px;
        }
    }

    /* MOBILE VIEW: Ensure scrollbars are visible */
    @media (max-width: 767px) {
        .main .block-container {
            overflow: auto !important; 
            height: auto !important;
        }
        [data-testid="column"] {
            height: 500px !important; /* Set a fixed height on mobile so they scroll individually */
            overflow-y: scroll !important;
            border: 1px solid #31333F;
            margin-bottom: 10px;
            -webkit-overflow-scrolling: touch;
        }
    }

    /* Global Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0e1117;
    }
    ::-webkit-scrollbar-thumb {
        background-color: #4b4b4b;
        border-radius: 10px;
        border: 2px solid #0e1117;
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
# Displaying title smaller to save space
st.markdown("### 🛡️ CyberDayZ Log Scanner")

# Column ratio updated for width
col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("##### 1. Filter Logs")
    uploaded_files = st.file_uploader("Upload .ADM Files", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Filter", [
            "Activity per Specific Player", 
            "All Death Locations", 
            "All Placements", 
            "Session Tracking (Global)", 
            "RAID WATCH (Global)"
        ])

        target_player = None
        sub_choice = None

        if mode == "Activity per Specific Player":
            temp_all = []
            for f in uploaded_files:
                temp_all.extend(f.getvalue().decode("utf-8", errors="ignore").splitlines())
            player_list = sorted(list(set(line.split('"')[1] for line in temp_all if 'Player "' in line)))
            target_player = st.selectbox("Player", player_list)
            sub_choice = st.radio("Detail", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process Logs"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice)

    if st.session_state.filtered_result:
        st.download_button(
            label="💾 Download Filtered ADM", 
            data=st.session_state.filtered_result, 
            file_name="FILTERED_LOGS.adm",
            mime="text/plain"
        )

# RIGHT COLUMN: iZurvive Map
with col2:
    col_map_h, col_map_b = st.columns([2, 1])
    with col_map_h:
        st.write("##### 2. iZurvive Map Viewer")
    with col_map_b:
        if st.button("🔄 Refresh Map"):
            st.session_state.map_version += 1
    
    # Dynamic URL query to force refresh
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1200, scrolling=True)
