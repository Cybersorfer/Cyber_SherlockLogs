import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io

# --- FTP CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
# Based on your URLs, the files live here:
FTP_PATH = "/dayzps/config/"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- FUNCTIONS ---

def get_ftp_connection():
    """Establishes a connection to your Nitrado FTP server."""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_log_list():
    """Lists .ADM and .RPT files directly from the FTP folder."""
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst() # Get file names
        logs = [f for f in files if f.endswith(('.ADM', '.RPT'))]
        ftp.quit()
        return sorted(logs, reverse=True)
    return []

def download_log_content(file_name):
    """Downloads the file content into memory."""
    ftp = get_ftp_connection()
    if ftp:
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {file_name}", buffer.write)
        ftp.quit()
        return buffer.getvalue().decode('utf-8', errors='ignore')
    return None

def parse_adm_data(content):
    """Extracts player name, time, and coordinates."""
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    data = [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")
st.sidebar.header("Filters")
search_query = st.sidebar.text_input("🔍 Search Player Name", "").strip()

# Attempt to load logs via FTP
with st.spinner("Connecting to FTP..."):
    logs = get_log_list()

if logs:
    st.sidebar.success(f"✅ Connected to {FTP_HOST}")
    selected_log = st.selectbox("Select Log File", logs)
    
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
                    
                    # Metrics
                    col1, col2 = st.columns(2)
                    col1.metric("Total Entries", len(df))
                    col2.metric("Unique Players", df['Player'].nunique())
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV for iZurvive", csv, f"{selected_log}.csv", "text/csv")
                else:
                    st.warning("No coordinates found in this file.")
            else:
                st.text_area("Log Preview", raw_text[:5000], height=400)
else:
    st.error(f"No logs found at {FTP_PATH}. Ensure the path is correct in the FTP client.")
