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

# 3. Helper: Generate iZurvive Link from DayZ Coords
def make_izurvive_link(line):
    try:
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            x, y = parts[0], parts[2]
            # iZurvive URL format for Chernarus coordinates
            return f"https://www.izurvive.com/chernarusplus/#location={x};{y}"
    except:
        return None
    return None

def extract_coords(line):
    try:
        if "pos=<" in line:
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [float(p.strip()) for p in raw.split(",")]
            return [parts[0], parts[2]]
    except:
        return None
    return None

# 4. Main Filter Logic
def filter_logs(files, main_choice, target_player=None, sub_choice=None, town_choice=None, radius=1000):
    final_output = []
    session_data = [] # Used for the live UI report
    
    all_lines = []
    for uploaded_file in files:
        stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
        all_lines.extend(stringio.readlines())

    session_keys = ["connected", "disconnected", "lost connection", "choosing to respawn"]

    for line in all_lines:
        if "|" not in line or ":" not in line:
            continue
        
        low = line.lower()

        if main_choice == "Session Tracking (Global)":
            if any(k in low for k in session_keys):
                link = make_izurvive_link(line)
                session_data.append({"text": line.strip(), "link": link})
                final_output.append(line)
        
        # ... Other filter modes remain the same ...
        elif main_choice == "All Death Locations":
            if any(x in low for x in ["killed", "died", "suicide"]): final_output.append(line)
        # (Simplified for brevity, keep your existing town/player logic here)

    return "".join(final_output), session_data

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
        mode = st.selectbox("Select Filter", ["Session Tracking (Global)", "All Death Locations", "Activity Near Specific Town"])

        if st.button("🚀 Process"):
            res, report = filter_logs(uploaded_files, mode)
            st.session_state.filtered_result = res
            st.session_state.session_report = report

    # SESSION TRACKING REPORT VIEW
    if st.session_state.filtered_result and mode == "Session Tracking (Global)":
        st.success(f"Tracked {len(st.session_state.session_report)} Session Events")
        
        for item in st.session_state.session_report:
            with st.expander(item['text'][:60] + "..."):
                st.write(f"**Full Log:** `{item['text']}`")
                if item['link']:
                    st.link_button("📍 View on iZurvive Map", item['link'])
                else:
                    st.caption("No coordinates found for this event.")
    
    # Standard Download for other modes
    elif st.session_state.filtered_result:
        st.download_button("💾 Download for iZurvive", st.session_state.filtered_result, "MAP_READY.adm")

with col2:
    c1, c2 = st.columns([3, 1])
    with c1: st.write("**2. iZurvive Map**")
    with c2: 
        if st.button("🔄 Refresh"): st.session_state.map_version += 1
    
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.map_version}"
    components.iframe(map_url, height=1100, scrolling=True)
