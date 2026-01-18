import streamlit as st
import os
import io
import streamlit.components.v1 as components

# Setup Page Config - Set to "wide" to fit the map and scanner side-by-side
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# Custom CSS to fix the position of the map column (Zone 2)
st.markdown(
    """
    <style>
    /* This targets the second column specifically */
    [data-testid="column"]:nth-child(2) {
        position: fixed;
        right: 2%;
        top: 80px;
        width: 55%;
        height: 90vh;
        overflow: hidden;
    }
    
    /* Adjusts the main container to ensure the left side scrolls freely */
    .main .block-container {
        padding-top: 2rem;
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

# Create two columns: Left for Scanner (1), Right for iZurvive Map (2)
col1, col2 = st.columns([1, 1.3])

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
            
            st.success("Log Filtering Complete!")
            
            # Updated Instructions per your request
            st.info("💡 **Next Step:** Download the file below and upload the new filtered ADM file on the iZurvive map to the right.")
            
            st.download_button(
                label="💾 Download Filtered File",
                data=result,
                file_name="FILTERED_LOG.adm",
                mime="text/plain"
            )
            
            st.text_area("Filtered Text Preview", result, height=500)

with col2:
    st.header("2. iZurvive Map Viewer")
    st.warning("Upload the new filtered ADM file on the iZurvive section below.")
    
    # This embeds iZurvive. The CSS above makes this container stay static while scrolling.
    components.iframe("https://www.izurvive.com/serverlogs/", height=900, scrolling=True)
