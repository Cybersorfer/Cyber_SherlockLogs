import streamlit as st
import io
import math
import hashlib
import streamlit.components.v1 as components

# 1. Setup Page Config & Force Dark Mode
st.set_page_config(
    page_title="CyberDayZ Log Scanner", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. Comprehensive CSS: Dark Mode, Button Colors, and Layout
st.markdown(
    """
    <style>
    /* Force Dark Theme */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Fix Button Visibility in Dark Mode */
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
    }
    div.stButton > button:hover, div.stLinkButton > a:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }

    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 100%; }
    
    /* Event Colors */
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    .disconnect-log { color: #ffc107; border-left: 3px solid #ffc107; padding-left: 10px; }

    [data-testid='stMarkdownContainer'] h4 { margin-top: -15px !important; margin-bottom: 10px !important; }
    
    @media (min-width: 768px) {
        .main { overflow: hidden; }
        [data-testid='stHorizontalBlock'] { height: 98vh; margin-top: -20px; }
        [data-testid='column'] { 
            height: 100% !important; 
            overflow-y: auto !important; 
            padding-top: 15px; 
            border: 1px solid #4b4b4b; 
            border-radius: 8px;
            background-color: #161b22;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Helper Functions
def make_izurvive_link(coords):
    if coords and isinstance(coords, list) and len(coords) >= 2:
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return ""

def extract_player_and_coords(line):
    name = "System/Server"
    coords = None
    try:
        if 'Player "' in line:
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            # X=0, Y=1 (Correct Engine Coords)
            coords = [float(parts[0]), float(parts[1])]
    except:
        pass 
    return str(name), coords

# 4. Filter Logic
def filter_logs(files, main_choice):
    final_output = []
    grouped_report = {} 
    player_positions = {} 

    all_lines = []
    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    session_keys = ["is connected", "has been disconnected", "is connecting", "connected", "died", "killed", "bled out", "suicide"]

    for line in all_lines:
        if "|" not in line: continue
        
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords:
            player_positions[name] = coords

        if main_choice == "Session Tracking (Global)":
            low = line.lower()
            if any(k in low for k in session_keys):
                current_name, _ = extract_player_and_coords(line)
                last_pos = player_positions.get(current_name)
                
                # Tagging event type for colors
                status = "normal"
                if any(d in low for d in ["died", "killed", "suicide", "bled out"]): status = "death"
                elif "is connected" in low or "is connecting" in low: status = "connect"
                elif "disconnected" in low: status = "disconnect"
                
                event_entry = {
                    "time": str(line.split(" | ")[0]) if " | " in line else "00:00:00",
                    "text": str(line.strip()),
                    "link": make_izurvive_link(last_pos),
                    "status": status
                }
                
                if current_name not in grouped_report:
                    grouped_report[current_name] = []
                grouped_report[current_name].append(event_entry)
                final_output.append(line)
    
    return "\n".join(final_output), grouped_report

# --- WEB UI ---
if "filtered_result" not in st.session_state: st.session_state.filtered_result = None
if "grouped_report" not in st.session_state: st.session_state.grouped_report = {}
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
            st.session_state.grouped_report = report

    if st.session_state.filtered_result:
        if mode == "Session Tracking (Global)":
            search_query = st.text_input("🔍 Search Player Name", "").lower()
            sorted_players = sorted(st.session_state.grouped_report.keys())
            
            for player in sorted_players:
                if search_query and search_query not in str(player).lower():
                    continue
                    
                events = st.session_state.grouped_report[player]
                with st.expander(f"👤 {player} ({len(events)} events)"):
                    for i, ev in enumerate(events):
                        st.caption(f"🕒 {ev['time']}")
                        
                        # Style based on status
                        if ev['status'] == "death":
                            st.markdown(f"<div class='death-log'>{ev['text']}</div>", unsafe_allow_html=True)
                        elif ev['status'] == "connect":
                            st.markdown(f"<div class='connect-log'>{ev['text']}</div>", unsafe_allow_html=True)
                        elif ev['status'] == "disconnect":
                            st.markdown(f"<div class='disconnect-log'>{ev['text']}</div>", unsafe_allow_html=True)
                        else:
                            st.code(ev['text'])
                        
                        # THE FIX: Validate string and force non-empty
                        url_to_use = str(ev.get('link', ""))
                        if url_to_use.startswith("http"):
                            safe_key = hashlib.md5(f"{player}{i}{ev['time']}".encode()).hexdigest()
                            st.link_button("📍 View Location", url_to_use, key=f"btn_{safe_key}")
                        st.divider()
        else:
            st.download_button("💾 Download for iZurvive", st.session_state.filtered_result, "MAP_READY.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"): st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
