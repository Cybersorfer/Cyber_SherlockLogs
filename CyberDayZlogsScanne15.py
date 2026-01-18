import streamlit as st
import io
import math
import hashlib
import streamlit.components.v1 as components

# 1. Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 2. CSS: Forced Dark Mode, Rounded UI, and Custom Button Styles
st.markdown(
    """
    <style>
    /* Force Dark Theme */
    .stApp { background-color: #0e1117; color: #fafafa; }
    #MainMenu, header, footer { visibility: hidden; }

    /* Rounded File Uploader */
    [data-testid="stFileUploader"] {
        background-color: #161b22;
        border: 1px solid #31333F;
        border-radius: 15px;
        padding: 20px;
    }
    
    /* Dark Mode Buttons Styling */
    div.stButton > button, div.stLinkButton > a {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4b4b4b !important;
        border-radius: 8px !important;
        text-decoration: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0.5rem 1rem !important;
    }
    div.stButton > button:hover, div.stLinkButton > a:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }

    /* Event Category Colors */
    .death-log { color: #ff4b4b; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; }
    .connect-log { color: #28a745; border-left: 3px solid #28a745; padding-left: 10px; }
    .disconnect-log { color: #ffc107; border-left: 3px solid #ffc107; padding-left: 10px; }

    .block-container { padding-top: 0rem !important; max-width: 100%; }
    
    @media (min-width: 768px) {
        [data-testid='column'] { 
            height: 90vh !important; 
            overflow-y: auto !important; 
            padding: 15px;
            border: 1px solid #31333F;
            border-radius: 12px;
            background-color: #0d1117;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Helper Functions
def make_izurvive_link(coords):
    if coords and isinstance(coords, list) and len(coords) >= 2:
        # X and Y raw engine coordinates for inland plotting
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
            # FIXED: Using index 0 (X) and index 1 (Y) for inland positioning
            coords = [float(parts[0]), float(parts[1])]
    except:
        pass 
    return str(name), coords

# 4. Filter Logic: DISCARD events without coordinates to prevent errors
def filter_logs(files, mode):
    grouped_report = {} 
    player_positions = {} 

    all_lines = []
    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    session_keys = ["is connected", "disconnected", "connecting", "connected", "died", "killed", "bled out"]

    for line in all_lines:
        if "|" not in line: continue
        
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords:
            player_positions[name] = coords

        if mode == "Session Tracking (Global)":
            low = line.lower()
            if any(k in low for k in session_keys):
                current_name, _ = extract_player_and_coords(line)
                last_pos = player_positions.get(current_name)
                link = make_izurvive_link(last_pos)
                
                # Only save if we have a valid link
                if link.startswith("http"):
                    status = "normal"
                    if any(d in low for d in ["died", "killed", "bled out"]): status = "death"
                    elif "connect" in low: status = "connect"
                    elif "disconnect" in low: status = "disconnect"

                    event_entry = {
                        "time": str(line.split(" | ")[0]),
                        "text": str(line.strip()),
                        "link": link,
                        "status": status
                    }

                    if current_name not in grouped_report:
                        grouped_report[current_name] = []
                    grouped_report[current_name].append(event_entry)
    
    return grouped_report

# --- WEB UI ---
st.markdown("#### 🛡️ CyberDayZ Scanner")
col1, col2 = st.columns([1, 2.3])

with col1:
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM", type=['adm', 'rpt'], accept_multiple_files=True)

    if uploaded_files:
        mode = st.selectbox("Select Filter", ["Session Tracking (Global)", "All Map Positions"])
        if st.button("🚀 Process"):
            st.session_state.track_data = filter_logs(uploaded_files, mode)

    if "track_data" in st.session_state:
        query = st.text_input("🔍 Search Player", "").lower()
        
        sorted_players = sorted(st.session_state.track_data.keys())
        for p in sorted_players:
            if query and query not in p.lower(): continue
            
            events = st.session_state.track_data[p]
            with st.expander(f"👤 {p} ({len(events)} events)"):
                for ev in events:
                    st.caption(f"🕒 {ev['time']}")
                    st.markdown(f"<div class='{ev['status']}-log'>{ev['text']}</div>", unsafe_allow_html=True)
                    
                    # FIXED: Removed the 'key' argument which caused the TypeError
                    st.link_button("📍 View on Map", ev['link'])
                    st.divider()

with col2:
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=1000, scrolling=True)
