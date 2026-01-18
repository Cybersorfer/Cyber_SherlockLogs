import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Advanced CSS for Independent Scrolling Columns
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
        height: 85vh;
    }

    /* Make each column an independent scrollable box */
    [data-testid="column"] {
        height: 100% !important;
        overflow-y: auto !important;
        padding-right: 15px;
    }

    /* Style the scrollbar for a cleaner look */
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
st.title("🛡️ CyberDayZ Log Scanner V3")

# Create two columns
col1, col2 = st.columns([1, 1.3])

# LEFT COLUMN: Filter Logic (Independent Scroll)
with col1:
    st.subheader("1. Filter Settings")
    uploaded_files = st.file_uploader("Upload .ADM or .RPT Files", type=['adm', 'rpt'], accept_multiple_files=True)

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
            target_player = st.selectbox("Target Player", player_list)
            sub_choice = st.radio("Detail", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process Logs"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice)

    if st.session_state.filtered_result:
        st.success("Filtered Logs Ready!")
        st.download_button(label="💾 Download for iZurvive", data=st.session_state.filtered_result, file_name="FOR_MAP.adm")
        st.text_area("Preview (Scrollable)", st.session_state.filtered_result, height=800)

# RIGHT COLUMN: iZurvive Map (Independent Scroll + Refresh)
with col2:
    st.subheader("2. iZurvive Map")
    
    # Independent Refresh Button
    if st.button("🔄 Refresh Map Window"):
        st.session_state.map_version += 1
    
    st.info("Download file from left, then click 'Filter' -> 'Serverlogs' here.")
    
    # Map component with versioning key to allow refresh
    components.iframe(
        f"https://www.izurvive.com/serverlogs/", 
        height=1200, 
        scrolling=True,
        key=f"map_v_{st.session_state.map_version}"
    )
