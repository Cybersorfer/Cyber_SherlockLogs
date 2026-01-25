import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime

# --- 1. NITRADO API CONFIGURATION ---
# Your Long-Life Token
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

# --- 2. HELPER FUNCTIONS ---
def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def fetch_live_log_via_api(file_path):
    """Downloads active log content directly via Nitrado API."""
    try:
        download_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
        res = requests.get(download_url, headers=get_api_headers())
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            return requests.get(token_url).content
    except Exception as e:
        st.error(f"API Error: {e}")
    return None

def list_files(directory):
    """Helper to list all files in a directory to find the right path."""
    list_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={directory}"
    res = requests.get(list_url, headers=get_api_headers())
    if res.status_code == 200:
        return res.json().get('data', {}).get('entries', [])
    return []

def filter_live_activity(file_content, mode):
    """Parses logs for specific game events."""
    data = []
    content = file_content.decode('latin-1', errors='ignore')
    
    # Regex patterns for tracking
    patterns = {
        "Movement": r"pos=<([\d\.]+, [\d\.]+, [\d\.]+)>",
        "Building": r"(built|placed|Placement|ITEM_PLACED|BASEBUILDING)",
        "Dismantling": r"(dismantled|dismantling|mounting|unmounting)",
        "Combat": r"(hit by|killed by|died|unconscious|PLAYER_DAMAGE)",
        "Vehicles": r"(Transport|Vehicle|Car|Truck)"
    }
    
    for line in content.split('\n'):
        if any(re.search(p, line, re.IGNORECASE) for p in patterns.values()):
            # Simple timestamp extraction
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            data.append({"Timestamp": timestamp, "Event Details": line.strip()})
            
    return pd.DataFrame(data)

# --- 3. MAIN APP INTERFACE ---
st.set_page_config(page_title="Cyber DayZ Sherlock", layout="wide")

# SIDEBAR
with st.sidebar:
    st.title("🛡️ Nitrado Manager")
    st.info("Status: FTP & API Ready")
    
    # --- LIVE API SCANNER SECTION ---
    st.divider()
    st.header("⚡ Live API Scanner")
    
    live_mode = st.radio("Target Log:", ["ADM (Events)", "RPT (System)"], horizontal=True)
    
    # Allow user to manually fix the path if default fails
    custom_path = st.text_input("Log Path:", value="/dayzps/config")
    
    if st.button("🔥 Request Last Hour Data", use_container_width=True):
        with st.spinner("Talking to Nitrado API..."):
            ext = ".adm" if "ADM" in live_mode else ".rpt"
            
            # 1. Try to list files in the chosen path
            files = list_files(custom_path)
            
            # 2. Filter for specific extension (Case Insensitive)
            target_files = [f for f in files if f['name'].lower().endswith(ext)]
            
            if target_files:
                # Find the newest file
                latest = max(target_files, key=lambda x: x['mtime'])
                st.write(f"📂 **Analyzing:** `{latest['name']}`")
                
                # 3. Download and Process
                raw_log = fetch_live_log_via_api(latest['path'])
                if raw_log:
                    results_df = filter_live_activity(raw_log, live_mode)
                    st.session_state['live_intel'] = results_df
                    st.success("Data Updated!")
            else:
                st.error(f"No {ext.upper()} files found in `{custom_path}`")
                st.warning("Tip: Use the 'Path Finder' below to see what folders exist.")

    # --- DEBUG: PATH FINDER TOOL ---
    with st.expander("🕵️ Debug: Path Finder"):
        st.caption("If you can't find logs, check what folders the API sees.")
        test_path = st.text_input("Check Directory:", value="/dayzps")
        if st.button("List Files"):
            found = list_files(test_path)
            if found:
                st.write(f"Found {len(found)} items in `{test_path}`:")
                for f in found:
                    icon = "Qw" if f['type'] == 'dir' else "Aq" 
                    st.text(f"- {f['name']} ({f['type']})")
            else:
                st.error("Directory not found or empty.")

# MAIN DASHBOARD
st.title("Cyber DayZ - Live Intelligence")

if 'live_intel' in st.session_state:
    st.subheader("Latest Recorded Activity (Live Buffer)")
    st.dataframe(st.session_state['live_intel'], use_container_width=True)
    
    csv = st.session_state['live_intel'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Report", csv, "live_intel.csv", "text/csv")
else:
    st.write("👈 Use the **Live API Scanner** to fetch data.")
