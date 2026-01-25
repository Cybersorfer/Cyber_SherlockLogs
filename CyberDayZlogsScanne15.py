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
        # Request download URL
        download_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={file_path}"
        res = requests.get(download_url, headers=get_api_headers())
        
        if res.status_code == 200:
            token_url = res.json()['data']['token']['url']
            # Download actual content
            file_res = requests.get(token_url)
            return file_res.content
        else:
            st.warning(f"Download failed for {file_path} (Status: {res.status_code})")
    except Exception as e:
        st.error(f"API Error during download: {e}")
    return None

def smart_list_files(base_path):
    """
    Tries multiple path variations to handle API quirks.
    Returns the file list and the path that actually worked.
    """
    # Variations to try: exact, no leading slash, trailing slash
    variations = [base_path, base_path.lstrip("/"), f"{base_path}/"]
    
    for path in variations:
        list_url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={path}"
        res = requests.get(list_url, headers=get_api_headers())
        
        if res.status_code == 200:
            entries = res.json().get('data', {}).get('entries', [])
            if entries:
                return entries, path # Found it!
                
    return [], base_path # Failed to find anything

def filter_live_activity(file_content, mode):
    """Parses logs for specific game events based on User Requirements."""
    data = []
    # Decode with error ignoring to handle special characters
    content = file_content.decode('latin-1', errors='ignore')
    
    # Regex patterns for the specific activities you requested
    patterns = {
        "Movement": r"pos=<([\d\.]+, [\d\.]+, [\d\.]+)>",
        "Building": r"(built|placed|Placement|ITEM_PLACED|BASEBUILDING)",
        "Dismantling": r"(dismantled|dismantling|mounting|unmounting)",
        "Combat": r"(hit by|killed by|died|unconscious|PLAYER_DAMAGE)",
        "Vehicles": r"(Transport|Vehicle|Car|Truck|respawn)"
    }
    
    for line in content.split('\n'):
        # Check if line matches any pattern
        if any(re.search(p, line, re.IGNORECASE) for p in patterns.values()):
            # Extract timestamp (first 8 chars usually HH:MM:SS)
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            
            # Clean up the event text
            clean_event = line.strip()
            
            data.append({
                "Timestamp": timestamp, 
                "Event Type": "General", # You can refine this logic later
                "Details": clean_event
            })
            
    return pd.DataFrame(data)

# --- 3. MAIN APP INTERFACE ---
st.set_page_config(page_title="Cyber DayZ Live Intelligence", layout="wide")

# SIDEBAR
with st.sidebar:
    st.title("🛡️ Nitrado Live Manager")
    st.info(f"Connected to Service ID: {SERVICE_ID}")
    
    st.divider()
    st.header("⚡ Live API Scanner")
    st.caption("Access data instantly. No restarts needed.")
    
    # Toggle for log type
    log_type = st.radio("Target Intelligence:", ["ADM (Base/Move)", "RPT (System/Eco)"], horizontal=True)
    
    # Path Configuration (Defaulted to the path found in your logs)
    target_path = st.text_input("Server Path:", value="/dayzps/config")
    
    if st.button("🔥 Request Last Hour Data", use_container_width=True):
        with st.spinner("Triangulating log files via API..."):
            
            # 1. Smart List Files (Tries multiple path variations)
            files, used_path = smart_list_files(target_path)
            
            if files:
                # 2. Filter for the correct extension
                ext = ".adm" if "ADM" in log_type else ".rpt"
                target_files = [f for f in files if f['name'].lower().endswith(ext)]
                
                if target_files:
                    # 3. Find the newest file
                    latest = max(target_files, key=lambda x: x['mtime'])
                    st.success(f"Locked on target: `{latest['name']}`")
                    st.caption(f"Path used: `{used_path}`")
                    
                    # 4. Download content
                    raw_log = fetch_live_log_via_api(latest['path'])
                    
                    if raw_log:
                        # 5. Process Data
                        results_df = filter_live_activity(raw_log, log_type)
                        st.session_state['live_intel'] = results_df
                        st.session_state['current_file'] = latest['name']
                    else:
                        st.error("Failed to download file content.")
                else:
                    st.warning(f"Directory found, but no {ext.upper()} files inside.")
                    st.write("Files found:", [f['name'] for f in files])
            else:
                st.error(f"Could not find folder: {target_path}")
                st.info("Tip: Check 'File Browser' in Nitrado to confirm folder name.")

# MAIN DASHBOARD
st.title("Cyber DayZ - Live Intelligence")

if 'live_intel' in st.session_state:
    df = st.session_state['live_intel']
    file_name = st.session_state.get('current_file', 'Unknown')
    
    # Metrics
    col1, col2 = st.columns(2)
    col1.metric("Events Found", len(df))
    col2.metric("Source File", file_name)
    
    st.subheader("Latest Server Activity (Live Buffer)")
    st.dataframe(df, use_container_width=True)
    
    # Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Live Intel to CSV",
        data=csv,
        file_name="live_dayz_intel.csv",
        mime="text/csv"
    )
else:
    st.markdown("""
    ### 👈 Instructions
    1. Look at the Sidebar on the left.
    2. Select **ADM** for Base Building/Movement or **RPT** for Economy/System.
    3. Click **Request Last Hour Data**.
    
    The app will automatically try to find your logs in `/dayzps/config`.
    """)
