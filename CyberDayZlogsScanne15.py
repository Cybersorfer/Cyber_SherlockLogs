import streamlit as st
import pandas as pd
import requests
import io
import re

# --- 1. CONFIGURATION ---
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

# --- 2. CORE FUNCTIONS ---
def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def fetch_file_content(file_path):
    """Downloads a file content via Nitrado API."""
    # Ensure NO leading slash to avoid "Wrong Owner" 500 Error
    clean_path = file_path.lstrip("/")
    
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={clean_path}"
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            return requests.get(token_url).content
    except Exception as e:
        st.error(f"Download Error: {e}")
    return None

def scan_directory(path):
    """Safely lists files by removing leading slashes."""
    # CRITICAL FIX: Remove leading slash to prevent accessing System Root
    clean_path = path.lstrip("/") 
    
    # If path is empty, try to list the root
    if not clean_path:
        clean_path = "."

    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={clean_path}"
    
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            return res.json().get('data', {}).get('entries', [])
        elif res.status_code == 500:
            st.warning(f"⚠️ API Permission Error on '{clean_path}'. (Try a different folder level)")
            return []
        else:
            st.error(f"API Error ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

def parse_log_activity(content, log_type):
    """Extracts relevant events from the log."""
    data = []
    decoded = content.decode('latin-1', errors='ignore')
    
    # regex for coordinates
    pos_pattern = re.compile(r"pos=<(\d+\.\d+),\s*\d+\.\d+,\s*(\d+\.\d+)>")
    
    for line in decoded.split('\n'):
        # Filter based on user selection
        relevant = False
        event_type = "Info"
        
        if "ADM" in log_type:
            if any(x in line for x in ["Transport", "placed", "built", "dismantled"]):
                relevant = True
                event_type = "Build/Move"
        else: # RPT Mode
            if any(x in line for x in ["killed", "died", "hit by", "VehicleRespawner"]):
                relevant = True
                event_type = "Combat/Eco"

        if relevant:
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            
            # Extract coords if present
            coords = "N/A"
            match = pos_pattern.search(line)
            if match:
                coords = f"{match.group(1)}, {match.group(2)}"
            
            data.append({
                "Time": timestamp, 
                "Type": event_type, 
                "Coords": coords,
                "Event": line.strip()
            })
            
    return pd.DataFrame(data)

# --- 3. APP UI ---
st.set_page_config(page_title="DayZ Smart Scanner", layout="wide")

with st.sidebar:
    st.title("🛡️ Nitrado Smart Scanner")
    st.info("Fix applied: Relative Paths Only")
    
    st.divider()
    
    # 1. Path Selector (The "Smart" part)
    st.header("1. Target Location")
    path_option = st.selectbox(
        "Where should we look?",
        [
            "dayzps/config",       # Standard Config
            "dayzps/config/profiles", # Common for Community Tools
            "dayzps/mpmissions/dayzOffline.chernarusplus/storage_18159994", # Deep Storage
            "dayzps",              # Game Root
            ""                     # Server Root (Empty string)
        ]
    )
    
    # 2. File Type Selector
    st.header("2. File Type")
    target_ext = st.radio("Look for:", [".ADM (Logs)", ".bin (Data)", ".RPT (System)"], horizontal=True)
    
    # 3. Scan Button
    if st.button("🚀 Scan Directory"):
        with st.spinner(f"Scanning '{path_option}'..."):
            files = scan_directory(path_option)
            
            # Filter specifically for the extension we want
            if files:
                # Case insensitive search
                matching_files = [f for f in files if f['name'].lower().endswith(target_ext.lower())]
                st.session_state.found_files = matching_files
                st.session_state.scan_path = path_option
                if not matching_files:
                    st.warning(f"Connected to folder, but no {target_ext} files found.")
            else:
                st.error("Could not list files. The path might be invalid.")

# --- MAIN DASHBOARD ---
st.title("Cyber DayZ - Live Intelligence")

if 'found_files' in st.session_state and st.session_state.found_files:
    st.success(f"📂 Found {len(st.session_state.found_files)} files in `{st.session_state.scan_path}`")
    
    # Sort files by newest first
    sorted_files = sorted(st.session_state.found_files, key=lambda x: x['mtime'], reverse=True)
    
    # File Selector
    options = {f"{f['name']} (Size: {f['size']}b)": f['path'] for f in sorted_files}
    selected_name = st.selectbox("Select a file to analyze:", list(options.keys()))
    
    if st.button("🔥 Process This File"):
        target_path = options[selected_name]
        with st.spinner("Downloading & Parsing..."):
            raw_content = fetch_file_content(target_path)
            
            if raw_content:
                # Determine mode for parser
                mode = "ADM" if ".adm" in target_path.lower() else "RPT"
                df = parse_log_activity(raw_content, mode)
                
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Data", csv, "dayz_data.csv", "text/csv")
                else:
                    st.warning("File is empty or contains no tracked events.")
                    with st.expander("See Raw Content"):
                        st.text(raw_content.decode('latin-1')[:2000])
else:
    st.write("👈 Select a target folder on the left to begin.")
