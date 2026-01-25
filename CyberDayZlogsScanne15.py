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

def get_file_list(path):
    """Lists contents of a directory via Nitrado API."""
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list?dir={path}"
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            data = res.json().get('data', {}).get('entries', [])
            # Sort: Folders first, then files
            data.sort(key=lambda x: (x['type'] != 'dir', x['name']))
            return data
        return []
    except:
        return []

# --- 3. APP UI ---
st.set_page_config(page_title="Deep Storage Explorer", layout="wide")

st.title("🕵️ DayZ Deep Storage Hunter")

# This path is derived directly from your log files
suspected_path = "/dayzps/mpmissions/dayzOffline.chernarusplus/storage_18159994/data"

st.info(f"Targeting confirmed storage path: `{suspected_path}`")

if st.button("🚀 Scan This Specific Folder"):
    with st.spinner("Accessing deep storage..."):
        files = get_file_list(suspected_path)
        
        if files:
            st.success(f"Connected! Found {len(files)} files.")
            
            # Separate important files
            vehicles = [f for f in files if "vehicles" in f['name'].lower()]
            players = [f for f in files if "players" in f['name'].lower()]
            others = [f for f in files if f not in vehicles and f not in players]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("🚗 Vehicles")
                for f in vehicles:
                    st.text(f"📄 {f['name']} ({f['size']} B)")
                    
            with col2:
                st.subheader("👤 Players")
                for f in players:
                    st.text(f"📄 {f['name']} ({f['size']} B)")
                    
            with col3:
                st.subheader("📂 Others")
                for f in others:
                    st.text(f"📄 {f['name']}")
        else:
            st.error("Could not access that specific folder. Trying parent folder...")
            # Fallback: try one level up
            parent_path = "/dayzps/mpmissions/dayzOffline.chernarusplus/storage_18159994"
            files_parent = get_file_list(parent_path)
            if files_parent:
                st.warning(f"Found parent folder instead: `{parent_path}`")
                st.write(files_parent)
            else:
                st.error("Even the parent folder is not accessible via API. Nitrado might block API access to 'storage' folders.")

st.markdown("---")
st.caption("If you see 'vehicles.bin', we know exactly where the data lives!")
