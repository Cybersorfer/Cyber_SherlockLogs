import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile

# --- FTP CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config/"

st.set_page_config(page_title="CyberDayZ Scanner v27.9", layout="wide")

# --- FUNCTIONS ---

def get_ftp_connection():
    """Establishes a connection to the Nitrado FTP server."""
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_all_logs():
    """Lists .ADM, .RPT, and .log files from the FTP folder."""
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst()
        # Filter for all requested types
        valid_extensions = ('.ADM', '.RPT', '.log')
        logs = [f for f in files if f.upper().endswith(valid_extensions)]
        ftp.quit()
        return sorted(logs, reverse=True)
    return []

def download_multiple_files(file_list):
    """Downloads multiple files and wraps them into a single ZIP for the user."""
    ftp = get_ftp_connection()
    zip_buffer = io.BytesIO()
    
    if ftp:
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_name in file_list:
                file_buffer = io.BytesIO()
                ftp.retrbinary(f"RETR {file_name}", file_buffer.write)
                zip_file.writestr(file_name, file_buffer.getvalue())
        ftp.quit()
        return zip_buffer.getvalue()
    return None

def parse_adm_data(content):
    """Extracts player coordinates from .ADM content."""
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    data = [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")

# 1. Multi-Select in Sidebar
st.sidebar.header("Bulk Operations")
all_available_files = get_all_logs()

selected_for_bulk = st.sidebar.multiselect(
    "Select files to download (.ZIP)", 
    options=all_available_files,
    help="Select multiple files to download them all at once in a ZIP archive."
)

if selected_for_bulk:
    if st.sidebar.button("Prepare ZIP Download"):
        with st.spinner("Zipping files..."):
            zip_data = download_multiple_files(selected_for_bulk)
            if zip_data:
                st.sidebar.download_button(
                    label="💾 Download ZIP Archive",
                    data=zip_data,
                    file_name="dayz_logs_bundle.zip",
                    mime="application/zip"
                )

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Search Player (for Active Scan)", "").strip()

# 2. Single File Analysis
st.subheader("Single File Analysis & iZurvive Export")
if all_available_files:
    active_file = st.selectbox("Select a file to scan for coordinates or preview:", all_available_files)
    
    if st.button("Run Scan"):
        ftp = get_ftp_connection()
        if ftp:
            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {active_file}", buffer.write)
            raw_text = buffer.getvalue().decode('utf-8', errors='ignore')
            ftp.quit()
            
            # ADM Parsing logic
            if active_file.upper().endswith(".ADM"):
                df = parse_adm_data(raw_text)
                if not df.empty:
                    if search_query:
                        df = df[df['Player'].str.contains(search_query, case=False)]
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV for iZurvive", csv, f"{active_file}.csv", "text/csv")
                else:
                    st.warning("No coordinates found in this ADM file.")
            # RPT and Log Preview
            else:
                st.info(f"Previewing {active_file}")
                st.text_area("Log Content", raw_text, height=500)
else:
    st.error(f"No files found at {FTP_PATH}")
