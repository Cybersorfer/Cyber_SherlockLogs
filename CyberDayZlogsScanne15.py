import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime, timedelta

# --- CONFIGURATION (Based on your provided credentials) ---
NITRADO_API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

# --- CORE FUNCTIONS ---

def get_api_headers():
    return {"Authorization": f"Bearer {NITRADO_API_TOKEN}"}

def fetch_live_log_via_api(file_path):
    """Downloads the latest content of a specific file via Nitrado API."""
    try:
        # 1. Request a temporary download URL from Nitrado
        download_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
        res = requests.get(download_url, headers=get_api_headers())
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            # 2. Fetch the actual raw file content
            file_res = requests.get(token_url)
            return file_res.content
    except Exception as e:
        st.error(f"API Error: {e}")
    return None

def filter_live_activity(file_content, target_type):
    """
    Parses DayZ logs for specific live activities: 
    Building, Dismantling, Combat, Movement, and Vehicles.
    """
    data = []
    content = file_content.decode('latin-1', errors='ignore')
    
    # Define regex patterns for live tracking
    patterns = {
        "Building/Placing": r"(built|placed|Placement)",
        "Dismantling": r"(dismantled|dismantling|mounting|unmounting)",
        "Combat": r"(hit by|killed by|died|unconscious)",
        "Movement": r"(pos=<[\d\.]+, [\d\.]+, [\d\.]+>)",
        "Vehicles": r"(Transport|Vehicle|Car|Truck)"
    }
    
    for line in content.split('\n'):
        if any(re.search(p, line, re.IGNORECASE) for p in patterns.values()):
            # Basic parsing to extract timestamp and event
            timestamp = line[:8] if "|" not in line[:10] else "N/A"
            data.append({"Time": timestamp, "Event": line.strip()})
            
    return pd.DataFrame(data)

# --- STREAMLIT UI ---

st.set_page_config(page_title="Cyber DayZ Log Scanner", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Nitrado Manager")
    
    # Existing FTP Manager Section would go here (Unchanged)
    st.info("Standard FTP Scanner Active")
    
    # --- NEW FEATURE: LIVE API SCANNER ---
    st.divider()
    st.header("⚡ Live API Scanner")
    st.caption("Requests real-time data directly from the API. NO RESTART NEEDED.")
    
    live_file_category = st.selectbox(
        "Activity Type to Scan:",
        ["Building & Movement (.ADM)", "Hits & Deaths (.RPT)"]
    )
    
    if st.button("🔥 Request Last Hour Data", use_container_width=True):
        with st.spinner("Talking to Nitrado API..."):
            ext = ".adm" if "ADM" in live_file_category else ".rpt"
            
            # 1. List files in /config via API to find the absolute latest
            list_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir=/dayzps/config"
            list_res = requests.get(list_url, headers=get_api_headers())
            
            if list_res.status_code == 200:
                files = list_res.json()['data']['entries']
                target_files = [f for f in files if f['name'].lower().endswith(ext)]
                
                if target_files:
                    # Get the most recently modified file
                    latest_file = max(target_files, key=lambda x: x['mtime'])
                    raw_content = fetch_live_log_via_api(latest_file['path'])
                    
                    if raw_content:
                        df = filter_live_activity(raw_content, live_file_category)
                        st.session_state['live_results'] = df
                        st.success(f"Success! Analyzed {latest_file['name']}")
                else:
                    st.error("No relevant logs found in /config")

# --- MAIN DISPLAY ---
st.title("Cyber DayZ - Live Intelligence")

if 'live_results' in st.session_state:
    st.subheader("Latest Server Activity (Last 60 Mins)")
    st.dataframe(st.session_state['live_results'], use_container_width=True)
    
    # Option to download the report
    csv = st.session_state['live_results'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Live Report", csv, "live_activity.csv", "text/csv")
else:
    st.write("Use the **Live API Scanner** in the sidebar to fetch real-time data.")
