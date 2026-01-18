import streamlit as st
import io
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. Custom CSS to fix the right column position (Zone 2)
st.markdown(
    """
    <style>
    /* Fix the right column (the map) so it stays pinned while left side scrolls */
    @media (min-width: 768px) {
        [data-testid="column"]:nth-child(2) {
            position: fixed;
            right: 20px;
            top: 50px;
            width: 55%;
            height: 90vh;
            z-index: 100;
        }
    }
    
    /* Give the overall page a cleaner look */
    .main {
        background-color: #0e1117;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Initialize Session State
if "filtered_result" not in st.session_state:
    st.session_state.filtered_result = None

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
                elif sub_choice == "Session Tracking" and any(k in low for k in session_keys):
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
st.title("🛡️ CyberDayZ Scanner")

# Create two columns
col1, col2 = st.columns([1, 1.4])

# LEFT COLUMN: Filter Logic
with col1:
    st.subheader("1. Filter Logs")
    uploaded_files = st.file_uploader("Upload .ADM Files", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Filter Mode", [
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
            sub_choice = st.radio("Detail", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch"])

        if st.button("🚀 Process Logs"):
            st.session_state.filtered_result = filter_logs(uploaded_files, mode, target_player, sub_choice)

    # Persistent Output (Doesn't disappear when you scroll or interact)
    if st.session_state.filtered_result:
        st.success("Filtered!")
        st.download_button(
            label="💾 Download Filtered ADM",
            data=st.session_state.filtered_result,
            file_name="FILTERED_LOGS.adm",
            mime="text/plain"
        )
        st.text_area("Filtered Logs Preview", st.session_state.filtered_result, height=600)

# RIGHT COLUMN: Floating Map Viewer
with col2:
    st.subheader("2. iZurvive Map")
    st.info("Download the file on the left, then upload it into 'Serverlogs' here.")
    
    # iframe without the 'key' argument to prevent the TypeError
    components.iframe("https://www.izurvive.com/serverlogs/", height=800, scrolling=True)
