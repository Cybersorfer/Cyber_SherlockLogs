import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io

# --- FTP CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config/"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- FUNCTIONS ---

def get_ftp_connection():
    """Establishes connection to Nitrado FTP server."""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def fetch_logs():
    """Retrieves file list and stores it in session state."""
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst()
        valid_extensions = ('.ADM', '.RPT', '.log')
        logs = [f for f in files if f.upper().endswith(valid_extensions)]
        ftp.quit()
        st.session_state.all_logs = sorted(logs, reverse=True)
    else:
        st.session_state.all_logs = []

def download_file(file_name):
    """Downloads a single file's content into memory."""
    ftp = get_ftp_connection()
    if ftp:
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {file_name}", buffer.write)
        ftp.quit()
        return buffer.getvalue()
    return None

def parse_adm_data(content):
    """Extracts DayZ coordinates for iZurvive plotting."""
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    data = [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")

# Fixed CSS to ensure the multiselect scrolls correctly
st.markdown("""
    <style>
        .stMultiSelect div div div div {
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: LOG MANAGER ---
st.sidebar.header("Log File Manager")

# Initialize file list if not present
if 'all_logs' not in st.session_state:
    fetch_logs()

# Control Buttons
col1, col2 = st.sidebar.columns(2)
if col1.button("Select All"):
    st.session_state.selected_list = st.session_state.all_logs
if col2.button("Clear All"):
    st.session_state.selected_list = []

# Refresh Button
if st.sidebar.button("🔄 Refresh Files"):
    with st.sidebar.status("Checking for new logs..."):
        fetch_logs()
    st.rerun()

# Multiselect Menu
selected_files = st.sidebar.multiselect(
    "Files for Download:", 
    options=st.session_state.all_logs,
    default=st.session_state.get('selected_list', [])
)

# Individual Download Section
if selected_files:
    st.sidebar.subheader(f"Downloads ({len(selected_files)})")
    for file_name in selected_files:
        file_data = download_file(file_name)
        if file_data:
            st.sidebar.download_button(
                label=f"📥 {file_name}",
                data=file_data,
                file_name=file_name,
                key=f"btn_{file_name}"
            )

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Player Search", "cybersorfer").strip()

# --- MAIN PAGE: ACTIVE SCAN ---
if st.session_state.all_logs:
    active_file = st.selectbox("Select file to scan:", st.session_state.all_logs)
    
    if st.button("Run Scan"):
        raw_data = download_file(active_file)
        if raw_data:
            raw_text = raw_data.decode('utf-8', errors='ignore')
            
            if active_file.upper().endswith(".ADM"):
                df = parse_adm_data(raw_text)
                if not df.empty:
                    if search_query:
                        df = df[df['Player'].str.contains(search_query, case=False)]
                    
                    st.success(f"Scanning: {active_file}")
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV for iZurvive", csv, f"{active_file}.csv", "text/csv")
                else:
                    st.warning("No coordinates found in this file.")
            else:
                st.info(f"Viewing: {active_file}")
                st.text_area("Log Preview", raw_text, height=500)
else:
    st.error("No files found on server. Try clicking 'Refresh Files'.")
