import streamlit as st
import io
import math
import streamlit.components.v1 as components

st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide")

# 1. CSS
st.markdown("<style>#MainMenu {visibility: hidden;} header {visibility: hidden;} .block-container { padding-top: 0rem !important; } [data-testid="stMarkdownContainer"] h4 { margin-top: -25px !important; }</style>", unsafe_allow_html=True)

# 2. Universal Coordinate Parser
def extract_coords(line):
    """Detects and extracts coordinates from the log line."""
    try:
        if "pos=<" in line:
            # Clean the string to get just the numbers
            raw = line.split("pos=<")[1].split(">")[0]
            parts = [p.strip() for p in raw.split(",")]
            
            # Logic: We need the two LARGEST numbers for X and Y mapping
            # (Height is almost always the smallest number)
            nums = [float(p) for p in parts]
            x = nums[0]
            y = nums[2] if len(nums) > 2 else nums[1]
            
            return [x, y]
    except:
        return None
    return None

def get_distance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# 3. Geodata
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": (13470, 13075, 1000),
    "Severograd": (11000, 12400, 800),
    "Tisy Military Base": (11500, 14200, 800),
    "Zelenogorsk": (2700, 5200, 800),
    "Chernogorsk": (6700, 2500, 1200),
}

# 4. Filter Logic
def filter_logs(files, town_choice, debug=False):
    final_output = []
    header = "AdminLog started on 00:00:00\n***********************\n"
    
    target_x, target_y, radius = CHERNARUS_LOCATIONS[town_choice]
    target_center = [target_x, target_y]
    
    debug_info = []

    for uploaded_file in files:
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        for line in content.splitlines():
            if "pos=<" in line:
                line_pos = extract_coords(line)
                if line_pos:
                    dist = get_distance(line_pos, target_center)
                    if dist <= radius:
                        final_output.append(line)
                    elif debug and len(debug_info) < 5:
                        debug_info.append(f"Line: {line_pos} is {int(dist)}m from {town_choice}")

    return header + "\n".join(final_output), debug_info

# --- UI ---
st.markdown("#### 🛡️ CyberDayZ Scanner")
col1, col2 = st.columns([1, 2.5])

with col1:
    st.write("**1. Filter Logs**")
    uploaded_files = st.file_uploader("Upload .ADM Files", accept_multiple_files=True)
    selected_town = st.selectbox("Select Town:", list(CHERNARUS_LOCATIONS.keys()))
    
    # Debugging Checkbox
    do_debug = st.checkbox("Show Debug Info (If 0 events found)")

    if st.button("🚀 Process Geodata"):
        if uploaded_files:
            res, debug_data = filter_logs(uploaded_files, selected_town, do_debug)
            st.session_state.filter_res = res
            
            count = len(res.splitlines()) - 2
            if count > 0:
                st.success(f"Found {count} events!")
            else:
                st.error("0 events found in this area.")
                if do_debug:
                    st.write("First 5 coords seen in your file:")
                    for d in debug_data: st.code(d)
        else:
            st.error("Upload files first.")

    if "filter_res" in st.session_state and st.session_state.filter_res:
        st.download_button("💾 Download ADM", st.session_state.filter_res, "FILTERED.adm")

with col2:
    if st.button("🔄 Refresh"): st.session_state.map_v = st.session_state.get('map_v', 0) + 1
    map_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('map_v', 0)}"
    components.iframe(map_url, height=1000, scrolling=True)
