import streamlit as st
import os
import io
import streamlit.components.v1 as components

# Setup Page Config - Set to "wide" to fit the map and scanner side-by-side
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# Custom CSS to make the right column (map) stay in place (floating)
st.markdown(
    """
    <style>
    [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlock"] {
        position: fixed;
        width: 58%;
        height: 100vh;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def filter_logs(files, main_choice, target_player=None, sub_choice=None):
    all_lines = []
    # iZurvive specifically looks for this header to recognize the file type
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
st.title("🛡️ CyberDayZ Log Scanner & Map Viewer")

# Create two columns: Left for Scanner, Right for iZurvive Map
col1, col2 = st.columns([1, 1.5])

with col1:
    st.header("1. Filter Logs")
    uploaded_files = st.file_uploader("Upload .ADM or .RPT", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Main Menu", [
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
            sub_choice = st.radio("Detail Level", [
                "Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch", "Session Tracking"
            ])

        if st.button("Process Logs"):
            result = filter_logs(uploaded_files, mode, target_player, sub_choice)
            
            st.success("Filtered!")
            
            # Updated Instructions
            st.warning("Next: Download the file below and upload the new filtered ADM file on the iZurvive map to the right.")
            
            st.download_button(
                label="💾 Download Filtered File",
                data=result,
                file_name="FILTERED_LOG.adm",
                mime="text/plain"
            )
            
            st.text_area("Filtered Preview", result, height=300)

with col2:
    st.header("2. iZurvive Map Viewer")
    st.info("Instructions: Download the file from the left, then click 'Filter' -> 'Serverlogs' on the map below and upload the file.")
    
    # This embeds the iZurvive serverlogs page directly in your app
    components.iframe("https://www.izurvive.com/serverlogs/", height=1000, scrolling=True)
