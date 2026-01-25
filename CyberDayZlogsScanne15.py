import streamlit as st
import pandas as pd
import requests
import re

# --- 1. CONFIGURATION ---
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

# --- 2. CORE FUNCTIONS ---
def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def probe_folder(path):
    """Tries to list a folder and returns (Success_Bool, File_Count, Content_List)."""
    # Fix: Ensure no leading slash to avoid 500 Errors
    clean_path = path.lstrip("/")
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={clean_path}"
    
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            entries = res.json().get('data', {}).get('entries', [])
            return True, len(entries), entries
        return False, 0, []
    except:
        return False, 0, []

def download_log(file_path):
    """Downloads file content using relative path."""
    clean_path = file_path.lstrip("/")
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={clean_path}"
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            return requests.get(token_url).content
    except:
        return None

def parse_adm_data(content):
    """Parses .ADM content for player/building activity."""
    data = []
    decoded = content.decode('latin-1', errors='ignore')
    
    # Pattern to find coordinates
    pos_pattern = re.compile(r"pos=<(\d+\.\d+),\s*\d+\.\d+,\s*(\d+\.\d+)>")
    
    for line in decoded.split('\n'):
        # We only care about lines with coordinates OR key events
        if "pos=<" in line or any(k in line for k in ["placed", "built", "dismantled", "killed", "died"]):
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            
            # Extract clean coords
            coords = "N/A"
            match = pos_pattern.search(line)
            if match:
                coords = f"{match.group(1)}, {match.group(2)}"
            
            data.append({
                "Time": timestamp, 
                "Coords": coords,
                "Event": line.strip()[:150] # Trim long lines
            })
    return pd.DataFrame(data)

# --- 3. APP UI ---
st.set_page_config(page_title="DayZ Path Finder", layout="wide")

st.title("🕵️ DayZ Path Finder")
st.markdown("This tool automatically tests common paths to find where your files are hidden.")

# --- AUTOMATIC PROBE SECTION ---
if 'valid_path' not in st.session_state:
    st.session_state.valid_path = None

with st.expander("🔍 Connection Diagnostics (Click to view)", expanded=True):
    col1, col2 = st.columns(2)
    
    # Test paths likely to work based on your logs
    candidates = [
        "",              # Try Empty String (Relative Root)
        ".",             # Try Dot (Current Dir)
        "config",        # Try config directly (If already in dayzps)
        "dayzps",        # Try dayzps (If at server root)
        "dayzps/config", # The path from the log file
        "mpmissions"     # The mission folder from the log file
    ]
    
    found_any = False
    
    for path in candidates:
        success, count, items = probe_folder(path)
        label = "ROOT (Empty)" if path == "" else path
        
        if success:
            st.success(f"✅ **FOUND:** `{label}` contains {count} files/folders!")
            # Save the first working path that looks promising
            if not st.session_state.valid_path and count > 0:
                st.session_state.valid_path = path
                st.session_state.file_list = items
            found_any = True
        else:
            st.error(f"❌ **Failed:** `{label}` (Not accessible)")

    if not found_any:
        st.error("CRITICAL: Nitrado API rejected ALL paths. Check your Token permissions.")

# --- FILE BROWSER ---
st.divider()

if st.session_state.valid_path is not None:
    current_path = st.session_state.valid_path
    files = st.session_state.file_list
    
    st.subheader(f"📂 Browsing: `{current_path if current_path else 'ROOT'}`")
    
    # 1. Show Folders (Navigation)
    folders = [f for f in files if f['type'] == 'dir']
    if folders:
        st.markdown("**Subfolders:**")
        cols = st.columns(4)
        for i, folder in enumerate(folders):
            if cols[i % 4].button(f"📁 {folder['name']}", key=folder['path']):
                # Drill down
                new_path = f"{current_path}/{folder['name']}".strip("/")
                success, count, new_items = probe_folder(new_path)
                if success:
                    st.session_state.valid_path = new_path
                    st.session_state.file_list = new_items
                    st.rerun()

    # 2. Show Files (Analysis)
    st.markdown("---")
    st.markdown("**Files:**")
    
    target_files = [f for f in files if f['type'] == 'file' and any(x in f['name'].lower() for x in ['.adm', '.rpt'])]
    
    if target_files:
        # Sort by newest
        target_files.sort(key=lambda x: x['mtime'], reverse=True)
        
        file_map = {f"{f['name']} ({f['size']}b)": f['path'] for f in target_files}
        selection = st.selectbox("Select Log File:", list(file_map.keys()))
        
        if st.button("🔥 ANALYZE THIS FILE"):
            selected_path = file_map[selection]
            st.info(f"Downloading `{selected_path}`...")
            
            raw_content = download_log(selected_path)
            if raw_content:
                if ".adm" in selection.lower():
                    df = parse_adm_data(raw_content)
                    st.success(f"Success! Extracted {len(df)} events.")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("This is a System Log (.RPT), not an Admin Log. It mostly contains server errors.")
                    st.text(raw_content.decode('latin-1')[:1000])
            else:
                st.error("Download failed.")
    else:
        st.info("No .ADM or .RPT logs found in this specific folder. Try opening a subfolder above.")
        
        # Fallback: List ALL files if no logs found
        all_files = [f['name'] for f in files if f['type'] == 'file']
        if all_files:
            st.caption(f"Other files here: {', '.join(all_files)}")

    # 3. Go Back Button
    st.markdown("---")
    if st.button("⬅️ Reset to Start"):
        st.session_state.valid_path = None
        st.rerun()

else:
    st.warning("Waiting for successful connection probe...")
