import streamlit as st
import io
import math
import hashlib
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. CSS for Independent Scrolling & Layout
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
        return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
    return None

def extract_player_and_coords(line):
    name = "System/Server"
    coords = None
    try:
        if 'Player "' in line:
            name = line.split('Player "')[1].split('"')[0]
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            # X=0, Y=1 (as requested for inland positioning)
            coords = [float(parts[0]), float(parts[1])]
    except:
        pass 
    return name, coords

# 4. Filter Logic with Grouping
def filter_logs(files, main_choice):
    final_output = []
    grouped_report = {} 
    player_positions = {} 

    all_lines = []
    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    session_keys = ["is connected", "has been disconnected", "is connecting", "connected", "died", "killed"]

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
                
                event_entry = {
                    "time": line.split(" | ")[0] if " | " in line else "00:00:00",
                    "text": line.strip(),
                    "link": make_izurvive_link(last_pos)
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
            # --- NEW SEARCH FEATURE ---
            search_query = st.text_input("🔍 Search Player Name", "").lower()
            
            st.info(f"📊 {len(st.session_state.grouped_report)} Players Found")
            
            sorted_players = sorted(st.session_state.grouped_report.keys())
            
            for player in sorted_players:
                if search_query and search_query not in player.lower():
                    continue
                    
                events = st.session_state.grouped_report[player]
                with st.expander(f"👤 {player} ({len(events)} events)"):
                    for ev in events:
                        st.caption(f"🕒 {ev['time']}")
                        st.code(ev['text'])
                        if ev['link']:
                            # Using MD5 hash to create a unique, safe key for the button
                            btn_id = hashlib.md5(f"{player}{ev['time']}{ev['text']}".encode()).hexdigest()
                            st.link_button(f"📍 View Location", ev['link'], key=f"link_{btn_id}")
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
