import streamlit as st
import io
import math
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. CSS for Layout
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 100%; }
    [data-testid='stMarkdownContainer'] h4 { margin-top: -15px !important; margin-bottom: 10px !important; }
    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid='stHorizontalBlock'] { height: 98vh; margin-top: -20px; }
        [data-testid='column'] { height: 100% !important; overflow-y: auto !important; padding-top: 15px; border: 1px solid #31333F; border-radius: 8px; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Helper Functions
def make_izurvive_link(coords):
    if coords:
        # DayZ Map coordinates for Chernarus (X and Y)
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return None

def extract_player_and_coords(line):
    """Safely extracts Player Name and [X, Y] coordinates."""
    name = "System/Server"
    coords = None
    try:
        if 'Player "' in line:
            name = line.split('Player "')[1].split('"')[0]
        
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            
            # DayZ logs use X, Z(Altitude), Y format. 
            # X = index 0, Y = index 2.
            # We ignore index 1 because it's the height above sea level.
            coords = [float(parts[0]), float(parts[2])]
    except Exception:
        pass 
    return name, coords

# 4. Filter Logic
def filter_logs(files, main_choice):
    final_output = []
    session_report = []
    player_positions = {} 

    all_lines = []
    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    session_keys = ["is connected", "has been disconnected", "is connecting", "connected"]

    for line in all_lines:
        if "|" not in line: continue
        
        # Memory tracking: capture positions from any line to keep the 'memory' updated
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords:
            player_positions[name] = coords

        if main_choice == "Session Tracking (Global)":
            low = line.lower()
            if any(k in low for k in session_keys):
                current_name, _ = extract_player_and_coords(line)
                last_pos = player_positions.get(current_name)
                
                session_report.append({
                    "text": line.strip(),
                    "link": make_izurvive_link(last_pos),
                    "player": current_name
                })
                final_output.append(line)
    
    return "\n".join(final_output), session_report

# --- WEB UI ---
if "filtered_result" not in st.session_state: st.session_state.filtered_result = None
if "session_report" not in st.session_state: st.session_state.session_report = []
if "map_version" not in st.session_state: st.session_state.map_version = 0

st.markdown("#### 🛡️ CyberDayZ Scanner")
col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Select Filter", ["Session Tracking (Global)", "Everything with Coordinates"])

        if st.button("🚀 Process"):
            res, report = filter_logs(uploaded_files, mode)
            st.session_state.filtered_result = res
            st.session_state.session_report = report

    if st.session_state.filtered_result:
        if mode == "Session Tracking (Global)":
            st.info("💡 Map links generated from last known player positions.")
            for item in st.session_state.session_report:
                display_name = item.get('player', 'Unknown Player')
                with st.expander(f"👤 {display_name} - {item['text'][:30]}..."):
                    st.code(item['text'])
                    if item.get('link'):
                        st.link_button(f"📍 View {display_name} on Map", item['link'])
                    else:
                        st.caption("No coordinates found for this player.")
        else:
            st.download_button("💾 Download for iZurvive", st.session_state.filtered_result, "MAP_READY.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"): st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
