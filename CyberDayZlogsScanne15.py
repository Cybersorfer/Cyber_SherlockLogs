import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime

# --- 1. CONFIGURATION ---
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

# --- 2. CORE FUNCTIONS ---
def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def get_file_list(path):
    """Lists contents of a directory via Nitrado API."""
    # Ensure path starts with / but doesn't end with / (unless root)
    clean_path = path if path.startswith("/") else f"/{path}"
    if clean_path != "/" and clean_path.endswith("/"):
        clean_path = clean_path[:-1]
        
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={clean_path}"
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            data = res.json().get('data', {}).get('entries', [])
            # Sort: Folders first, then files
            data.sort(key=lambda x: (x['type'] != 'dir', x['name']))
            return data
        else:
            st.error(f"API Error ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

def download_file(file_path):
    """Downloads a file content."""
    try:
        url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            return requests.get(token_url).content
    except Exception as e:
        st.error(f"Download Error: {e}")
    return None

def parse_log_activity(content):
    """Extracts activity from the raw log content."""
    lines = []
    decoded = content.decode('latin-1', errors='ignore')
    
    # Regex for coordinates
    coord_pattern = re.compile(r"pos=<([\d\.]+, [\d\.]+, [\d\.]+)>")
    
    for line in decoded.split('\n'):
        if coord_pattern.search(line) or any(k in line for k in ["built", "placed", "killed", "died"]):
            # Get timestamp if present (first 8 chars)
            ts = line[:8] if ":" in line[:8] else "Unknown"
            lines.append({"Time": ts, "Event": line.strip()})
            
    return pd.DataFrame(lines)

# --- 3. APP UI ---
st.set_page_config(page_title="Nitrado File Explorer", layout="wide")

# Initialize Session State for Navigation
if 'current_path' not in st.session_state:
    st.session_state.current_path = "/"

# --- SIDEBAR: NAVIGATION ---
with st.sidebar:
    st.title("📂 Server Explorer")
    st.write(f"**Current Path:** `{st.session_state.current_path}`")
    
    # "Up" Button
    if st.session_state.current_path != "/":
        if st.button("⬅️ Go Up Level"):
            # Logic to strip the last folder from path
            parts = st.session_state.current_path.strip("/").split("/")
            if len(parts) > 1:
                st.session_state.current_path = "/" + "/".join(parts[:-1])
            else:
                st.session_state.current_path = "/"
            st.rerun()

    st.divider()
    
    # List Files & Folders
    items = get_file_list(st.session_state.current_path)
    
    if items:
        st.caption("Folders (Click to Open):")
        for item in items:
            if item['type'] == 'dir':
                # Determine new path
                new_path = f"{st.session_state.current_path.rstrip('/')}/{item['name']}"
                if st.button(f"📁 {item['name']}", key=item['path']):
                    st.session_state.current_path = new_path
                    st.rerun()
        
        st.divider()
        st.caption("Log Files (Click to Scan):")
        for item in items:
            if item['type'] == 'file':
                # Only show relevant files to reduce clutter
                if any(x in item['name'].lower() for x in ['.adm', '.rpt', '.log']):
                    if st.button(f"📄 {item['name']}", key=f"file_{item['path']}"):
                        st.session_state.target_file = item['path']
                        st.session_state.target_name = item['name']
    else:
        st.warning("Folder is empty or inaccessible.")

# --- MAIN PANEL ---
st.title("Cyber DayZ - Log Analyzer")

if 'target_file' in st.session_state:
    st.subheader(f"Scanning: {st.session_state.target_name}")
    
    with st.spinner("Downloading and analyzing..."):
        raw_data = download_file(st.session_state.target_file)
        
        if raw_data:
            df = parse_log_activity(raw_data)
            
            if not df.empty:
                st.success(f"Found {len(df)} events!")
                st.dataframe(df, use_container_width=True)
                
                # Download Result
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Analysis CSV", csv, "log_analysis.csv", "text/csv")
            else:
                st.warning("File downloaded, but no relevant events (built, placed, killed, pos=<>) were found.")
                with st.expander("View Raw File Content (First 1000 chars)"):
                    st.text(raw_data.decode('latin-1')[:1000])
else:
    st.info("👈 Use the sidebar to navigate folders. Find your .ADM file and click it.")
