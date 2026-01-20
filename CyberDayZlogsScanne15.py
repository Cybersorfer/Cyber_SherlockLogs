import streamlit as st
import requests
import re
import pandas as pd

# --- UPDATED CONFIGURATION ---
TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18197890"
REMOTE_PATH = "dayzps/config/"
BASE_URL = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- FUNCTIONS ---

def get_log_list():
    """Fetches .ADM and .RPT files using the hardcoded Token and Path."""
    headers = {'Authorization': f'Bearer {TOKEN}'}
    params = {'dir': REMOTE_PATH}
    try:
        response = requests.get(f"{BASE_URL}/list", headers=headers, params=params)
        response.raise_for_status()
        files = response.json().get('data', {}).get('entries', [])
        logs = [f for f in files if f['name'].endswith(('.ADM', '.RPT'))]
        return sorted(logs, key=lambda x: x['name'], reverse=True)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

def download_log_content(file_name):
    """Retrieves the text content of the log file using the hardcoded Token."""
    headers = {'Authorization': f'Bearer {TOKEN}'}
    params = {'file': f"{REMOTE_PATH}{file_name}"}
    
    res = requests.get(f"{BASE_URL}/download", headers=headers, params=params)
    if res.status_code == 200:
        download_url = res.json().get('data', {}).get('token', {}).get('url')
        file_res = requests.get(download_url)
        return file_res.text
    return None

def parse_adm_data(content):
    """Extracts player name, time, and coordinates."""
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    
    data = []
    for m in matches:
        data.append({
            "Time": m[0],
            "Player": m[1],
            "X": float(m[2]),
            "Z": float(m[3])
        })
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")

# Player Search Bar in Sidebar
st.sidebar.header("Filters")
search_query = st.sidebar.text_input("🔍 Search Player Name", "").strip()

st.sidebar.divider()
st.sidebar.success("✅ Connected to Nitrado")
st.markdown(f"**Target Path:** `{REMOTE_PATH}` | **Service ID:** `{SERVICE_ID}`")

# Auto-load logs
logs = get_log_list()

if logs:
    log_names = [f['name'] for f in logs]
    selected_log = st.selectbox("Select Log File to Analyze", log_names)
    
    if st.button("Run Scan"):
        with st.spinner("Analyzing log data..."):
            raw_text = download_log_content(selected_log)
            
            if raw_text:
                if selected_log.endswith(".ADM"):
                    df = parse_adm_data(raw_text)
                    
                    if not df.empty:
                        # Apply Search Filter
                        if search_query:
                            df = df[df['Player'].str.contains(search_query, case=False)]
                        
                        st.subheader(f"Player Activity: {selected_log}")
                        if search_query:
                            st.caption(f"Showing results for: **{search_query}**")
                            
                        st.dataframe(df, use_container_width=True)
                        
                        # Summary Metrics
                        col1, col2 = st.columns(2)
                        col1.metric("Total Logs Found", len(df))
                        col2.metric("Unique Players", df['Player'].nunique())
                        
                        # CSV Export for iZurvive
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("Download CSV for iZurvive", csv, f"dayz_coords_{selected_log}.csv", "text/csv")
                    else:
                        st.warning("No coordinate data found in this ADM file.")
                else:
                    st.text_area("RPT Log Content (Preview)", raw_text[:5000], height=400)
else:
    st.error("No logs found. Check your Token and Service ID.")
