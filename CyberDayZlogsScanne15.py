import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime

# --- 1. NITRADO API HELPERS (Defined first to avoid NameErrors) ---
# Your Long-Life Token
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

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

def filter_live_activity(file_content, mode):
    """Parses logs for Movement, Building, Combat, and Vehicles."""
    data = []
    content = file_content.decode('latin-1', errors='ignore')
    
    # Combined search patterns for ADM and RPT events
    patterns = {
        "Movement/Position": r"pos=<([\d\.]+, [\d\.]+, [\d\.]+)>",
        "Building/Placing": r"(built|placed|Placement|ITEM_PLACED|BASEBUILDING)",
        "Dismantling/Crafting": r"(dismantled|dismantling|mounting|unmounting|ITEM_DETACH)",
        "Combat/Deaths": r"(hit by|killed by|died|unconscious|PLAYER_DAMAGE|PLAYER_LETHAL_DAMAGE)",
        "Vehicles": r"(Transport|Vehicle|Car|Truck|PLAYER_VEHICLE)"
    }
    
    for line in content.split('\n'):
        if any(re.search(p, line, re.IGNORECASE) for p in patterns.values()):
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            data.append({"Timestamp": timestamp, "Event Details": line.strip()})
            
    return pd.DataFrame(data)

# --- 2. MAIN APP INTERFACE ---
st.set_page_config(page_title="Cyber DayZ Sherlock", layout="wide")

# Sidebar Structure
with st.sidebar:
    st.title("🛡️ Nitrado Manager")
    
    # Section A: Your existing FTP Manager logic would be here
    st.info("Traditional FTP Scanner Ready")
    
    # Section B: THE NEW LIVE API SCANNER FEATURE
    st.divider()
    st.header("⚡ Live API Scanner")
    st.caption("Access data instantly without waiting for 3hr restarts.")
    
    live_mode = st.radio("Intelligence Type:", ["ADM (Base/Movement)", "RPT (Combat/System)"], horizontal=True)
    
    if st.button("🔥 Request Last Hour Data", use_container_width=True):
        with st.spinner("Fetching live buffer from Nitrado..."):
            ext = ".adm" if "ADM" in live_mode else ".rpt"
            
            # List files in /config to find the absolute newest
            list_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=/dayzps/config"
            list_res = requests.get(list_url, headers=get_api_headers())
            
            if list_res.status_code == 200:
                files = list_res.json().get('data', {}).get('entries', [])
                # Case-insensitive check for .ADM and .RPT
                target_files = [f for f in files if f['name'].lower().endswith(ext)]
                
                if target_files:
                    latest = max(target_files, key=lambda x: x['mtime'])
                    st.write(f"📂 Analyzing: {latest['name']}")
                    
                    raw_log = fetch_live_log_via_api(latest['path'])
                    if raw_log:
                        results_df = filter_live_activity(raw_log, live_mode)
                        st.session_state['live_intel'] = results_df
                        st.success("Analysis Updated!")
                else:
                    st.error(f"No {ext.upper()} logs found in /dayzps/config. Verify your log path.")
            else:
                st.error(f"Nitrado API rejected request (Code: {list_res.status_code})")

# --- 3. MAIN DASHBOARD DISPLAY ---
st.title("Cyber DayZ - Live Intelligence Dashboard")

if 'live_intel' in st.session_state:
    st.subheader("Latest Recorded Activity")
    st.dataframe(st.session_state['live_intel'], use_container_width=True)
    
    # Download Button
    csv = st.session_state['live_intel'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Live Intel", csv, "live_dayz_intel.csv", "text/csv")
else:
    st.write("👈 Select **Live API Scanner** in the sidebar to begin real-time tracking.")
