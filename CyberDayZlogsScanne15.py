import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
import requests # Added for Nitrado API
from datetime import datetime
import streamlit.components.v1 as components

# ==============================================================================
# NITRADO API CONFIGURATION
# ==============================================================================
NITRADO_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
NITRADO_SERVICE = "18197890"

def run_manual_api_sync():
    """Fetches the live ADM file via Nitrado API."""
    try:
        # Request download URL from Nitrado
        url = f"https://api.nitrado.net/services/{NITRADO_SERVICE}/gameservers/file_server/download"
        params = {"file": "/dayzps/config/ADM/DayZServer.adm"} 
        headers = {"Authorization": f"Bearer {NITRADO_TOKEN}"}
        
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            dl_url = resp.json()['data']['token']['url']
            
            # Download actual content
            file_res = requests.get(dl_url)
            sync_time = datetime.now().strftime('%H_%M')
            filename = f"MANUAL_SYNC_{sync_time}.adm"
            
            # Save locally
            with open(filename, "wb") as f:
                f.write(file_res.content)
            
            st.sidebar.success(f"✅ Saved: {filename}")
            st.toast(f"New log ready: {filename}", icon="🚀")
            return filename
        else:
            st.sidebar.error(f"❌ API Error: {resp.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {str(e)}")
    return None

# ==============================================================================
# YOUR EXISTING ACCESS CONTROL (TEAM ACCOUNTS)
# ==============================================================================
# (I am assuming your check_password() and team_accounts functions are here)

if check_password():
    # --- NEW SIDEBAR FEATURE ADDED HERE ---
    with st.sidebar:
        st.divider()
        st.subheader("🚀 Live Admin Sync")
        if st.button("Download Latest ADM", help="Get live logs directly from Nitrado."):
            run_manual_api_sync()
        st.divider()

    # ==========================================================================
    # YOUR EXISTING "PERFECT" PARSER CODE STARTS HERE
    # ==========================================================================
    st.title("CyberDayZ Ultimate Scanner")
    
    # Rest of your original code (File uploaders, Activity Search, etc.)
    # ...
