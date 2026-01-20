import streamlit as st
import requests
import re
import pandas as pd

# --- CONFIGURATION ---
# Token verified from your message
TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"

# Service ID updated to match your browser screenshot (18159994)
SERVICE_ID = "18159994" 
REMOTE_PATH = "dayzps/config/"
BASE_URL = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- FUNCTIONS ---

def get_log_list():
    headers = {'Authorization': f'Bearer {TOKEN}'}
    # We use 'dir' to point to the folder where your .ADM files are
    params = {'dir': REMOTE_PATH}
    try:
        response = requests.get(f"{BASE_URL}/list", headers=headers, params=params)
        
        # If this fails, the Token or Service ID is likely the issue
        if response.status_code != 200:
            return None, f"Error {response.status_code}: {response.text}"
            
        files = response.json().get('data', {}).get('entries', [])
        logs = [f for f in files if f['name'].endswith(('.ADM', '.RPT'))]
        return sorted(logs, key=lambda x: x['name'], reverse=True), None
    except Exception as e:
        return None, str(e)

def download_log_content(file_name):
    headers = {'Authorization': f'Bearer {TOKEN}'}
    params = {'file': f"{REMOTE_PATH}{file_name}"}
    res = requests.get(f"{BASE_URL}/download", headers=headers, params=params)
    if res.status_code == 200:
        download_url = res.json().get('data', {}).get('token', {}).get('url')
        file_res = requests.get(download_url)
        return file_res.text
    return None

def parse_adm_data(content):
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    data = [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")

st.sidebar.header("Filters")
search_query = st.sidebar.text_input("🔍 Search Player Name", "").strip()
st.sidebar.divider()

# Attempt to load logs
logs, error_msg = get_log_list()

if logs:
    st.sidebar.success("✅ Connected to Nitrado")
    st.markdown(f"**Target Path:** `{REMOTE_PATH}` | **Service ID:** `{SERVICE_ID}`")
    
    log_names = [f['name'] for f in logs]
    selected_log = st.selectbox("Select Log File", log_names)
    
    if st.button("Run Scan"):
        raw_text = download_log_content(selected_log)
        if raw_text:
            if selected_log.endswith(".ADM"):
                df = parse_adm_data(raw_text)
                if not df.empty:
                    if search_query:
                        df = df[df['Player'].str.contains(search_query, case=False)]
                    
                    st.subheader(f"Results for {selected_log}")
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV for iZurvive", csv, f"{selected_log}.csv", "text/csv")
                else:
                    st.warning("No coordinates found in this file.")
            else:
                st.text_area("Log Preview", raw_text[:5000], height=400)
elif error_msg:
    st.error(f"Connection Failed: {error_msg}")
else:
    st.error("No logs found. Check if the 'dayzps/config/' folder is correct for Service ID 18159994.")
