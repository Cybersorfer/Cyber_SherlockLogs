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
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def fetch_logs():
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
    ftp = get_ftp_connection()
    if ftp:
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {file_name}", buffer.write)
        ftp.quit()
        return buffer.getvalue()
    return None

def parse_adm_data(content):
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    data = [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]
    return pd.DataFrame(data)

# --- USER INTERFACE ---

st.title("🐺 CyberDayZ Log Scanner v27.9")

# --- SIDEBAR: LOG MANAGER ---
st.sidebar.header("Filter & Manage Logs")

if 'all_logs' not in st.session_state:
    fetch_logs()

# 1. FIXED LAYOUT: Horizontal Checkboxes
st.sidebar.subheader("Show File Types:")
check_cols = st.sidebar.columns(3)
with check_cols[0]: show_adm = st.checkbox("ADM", value=True)
with check_cols[1]: show_rpt = st.checkbox("RPT", value=True)
with check_cols[2]: show_log = st.checkbox("LOG", value=True)

# 2. Player Filter Scan
st.sidebar.divider()
st.sidebar.subheader("Content Filter")
player_to_find = st.sidebar.text_input("Only show files containing:", "cybersorfer").strip()
filter_by_content = st.sidebar.checkbox("Filter List by Player Presence")

selected_types = []
if show_adm: selected_types.append(".ADM")
if show_rpt: selected_types.append(".RPT")
if show_log: selected_types.append(".LOG")

# Apply Logic
display_logs = [f for f in st.session_state.all_logs if f.upper().endswith(tuple(selected_types))]

if filter_by_content and player_to_find:
    with st.sidebar.status("Scanning file contents..."):
        matched_logs = []
        for f in display_logs[:15]: # Scans top 15 for speed
            content = download_file(f)
            if content and player_to_find.lower() in content.decode('utf-8', errors='ignore').lower():
                matched_logs.append(f)
        display_logs = matched_logs

# 3. Control Buttons
col1, col2 = st.sidebar.columns(2)
if col1.button("Select All"):
    st.session_state.selected_list = display_logs
if col2.button("Clear All"):
    st.session_state.selected_list = []

# 4. Multiselect and BULK DOWNLOAD ZIP
selected_files = st.sidebar.multiselect(
    "Files for Download:", 
    options=display_logs,
    default=st.session_state.get('selected_list', [])
)

if selected_files:
    st.sidebar.subheader("Bulk Operations")
    # ZIP approach is the standard way to download multiple files at once in Streamlit
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for file_name in selected_files:
            data = download_file(file_name)
            if data:
                zip_file.writestr(file_name, data)
    
    st.sidebar.download_button(
        label=f"💾 Download {len(selected_files)} Files (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="dayz_logs_bundle.zip",
        mime="application/zip",
        use_container_width=True
    )

st.sidebar.divider()
search_query = st.sidebar.text_input("🔍 Table Search", "").strip()

# --- MAIN PAGE ---
if display_logs:
    active_file = st.selectbox("Select file to scan/view:", display_logs)
    
    if st.button("Run Scan"):
        raw_data = download_file(active_file)
        if raw_data:
            raw_text = raw_data.decode('utf-8', errors='ignore')
            
            if active_file.upper().endswith(".ADM"):
                df = parse_adm_data(raw_text)
                if not df.empty:
                    # Table Search applied here
                    if search_query:
                        df = df[df['Player'].str.contains(search_query, case=False)]
                    st.success(f"Scanning: {active_file}")
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV for iZurvive", csv, f"{active_file}.csv", "text/csv")
                else:
                    st.warning("No coordinates found.")
            else:
                st.text_area(f"Viewing: {active_file}", raw_text, height=500)
