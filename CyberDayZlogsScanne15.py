import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Advanced CSS for Independent Scrolling and Layout Tuning
st.markdown(
    """
    <style>
    /* Force the main container to fill the screen and disable global scroll */
    .main .block-container {
        max-width: 100%;
        padding-top: 2rem;
        padding-bottom: 0rem;
        height: 100vh;
        overflow: hidden;
    }

    /* Target the column container */
    [data-testid="stHorizontalBlock"] {
        height: 90vh;
    }

    /* Independent scrollable boxes for each column */
    [data-testid="column"] {
        height: 100% !important;
        overflow-y: auto !important;
        padding-right: 15px;
        border: 1px solid #31333F;
        border-radius: 8px;
        padding: 10px;
    }

    /* Set the specific width for the right column to be much wider */
    [data-testid="column"]:nth-child(2) {
        flex: 2.5 1 0% !important;
        width: 70% !important;
    }

    /* Style scrollbars */
    [data-testid="column"]::-webkit-scrollbar {
        width: 6px;
    }
    [data-testid="column"]::-webkit-scrollbar-thumb {
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
st.title("🛡️ CyberDayZ Log Scanner")

# Column ratio set to make the map viewer much wider [1, 2.5]
col1, col2 = st.columns([1, 2.5])

# LEFT COLUMN: Filter Logic
with col1:
    st.subheader("1. Filter Logs")
    uploaded_files = st.file_uploader("Upload .ADM Files", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Select Filter", [
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
            target_player = st.selectbox("Select Player", player_list)
            sub_choice = st.radio("Detail Level", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process Logs"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice)
            st.success("Filtered! Ready to download.")

    if st.session_state.filtered_result:
        # Download button remains so you can get the file for iZurvive
        st.download_button(
            label="💾 Download for iZurvive", 
            data=st.session_state.filtered_result, 
            file_name="FOR_MAP.adm",
            mime="text/plain"
        )
        st.info("Download the file above and upload it to the iZurvive map on the right.")

# RIGHT COLUMN: iZurvive Map
with col2:
    st.subheader("2. iZurvive Map Viewer")
    
    if st.button("🔄 Refresh Map Window"):
        st.session_state.map_version += 1
    
    # Dynamic URL query to force refresh
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1200, scrolling=True)
