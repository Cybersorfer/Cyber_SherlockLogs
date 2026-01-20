import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")

# --- 2. PROFESSIONAL DARK UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    .stMultiSelect div div div div { max-height: 300px; overflow-y: auto; }
    iframe { border-radius: 10px; border: 1px solid #4b4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FTP CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config/"

# --- 4. CORE FUNCTIONS (Integrated Logic) ---
def get_ftp_connection():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def fetch_ftp_logs():
    ftp = get_ftp_connection()
    if ftp:
        files = ftp.nlst()
        valid = ('.ADM', '.RPT', '.log')
        st.session_state.all_logs = sorted([f for f in files if f.upper().endswith(valid)], reverse=True)
        ftp.quit()

# NEW: Function to extract and read files from uploaded ZIPs
def process_uploaded_input(uploaded_files):
    all_content = []
    for uploaded_file in uploaded_files:
        # Check if the uploaded file is a ZIP
        if uploaded_file.name.endswith('.zip'):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for file_info in z.infolist():
                    # Only read relevant log types
                    if file_info.filename.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        with z.open(file_info) as f:
                            all_content.append({
                                "name": file_info.filename,
                                "text": f.read().decode('utf-8', errors='ignore')
                            })
        else:
            # Handle regular .ADM or .RPT files
            all_content.append({
                "name": uploaded_file.name,
                "text": uploaded_file.read().decode('utf-8', errors='ignore')
            })
    return all_content

def parse_adm_data(content):
    pattern = r'(\d{2}:\d{2}:\d{2}).*?player\s"(.*?)"\s.*?pos=<([\d\.-]+),\s[\d\.-]+,\s([\d\.-]+)>'
    matches = re.findall(pattern, content)
    return [{"Time": m[0], "Player": m[1], "X": float(m[2]), "Z": float(m[3])} for m in matches]

# --- 5. UI LAYOUT ---

# --- SIDEBAR: NITRADO LOG MANAGER ---
with st.sidebar:
    st.header("🐺 CyberDayZ Manager")
    if 'all_logs' not in st.session_state: fetch_ftp_logs()
    
    st.subheader("Show File Types:")
    c1, c2, c3 = st.columns(3)
    s_adm = c1.checkbox("ADM", value=True)
    s_rpt = c2.checkbox("RPT", value=True)
    s_log = c3.checkbox("LOG", value=True)
    
    v_ext = []
    if s_adm: v_ext.append(".ADM")
    if s_rpt: v_ext.append(".RPT")
    if s_log: v_ext.append(".LOG")
    f_logs = [f for f in st.session_state.get('all_logs', []) if f.upper().endswith(tuple(v_ext))]
    
    col_a, col_b = st.columns(2)
    if col_a.button("Select All"): st.session_state.sel_list = f_logs
    if col_b.button("Clear All"): st.session_state.sel_list = []
    
    if st.button("🔄 Refresh FTP List"): fetch_ftp_logs(); st.rerun()

    sel_files = st.multiselect("Files for Download:", options=f_logs, default=st.session_state.get('sel_list', []))

    if sel_files:
        if st.button("📦 Bundle & Download (ZIP)"):
            zip_buf = io.BytesIO()
            ftp = get_ftp_connection()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for fn in sel_files:
                    buf = io.BytesIO()
                    ftp.retrbinary(f"RETR {fn}", buf.write)
                    zf.writestr(fn, buf.getvalue())
            ftp.quit()
            st.download_button("💾 Download ZIP Archive", zip_buf.getvalue(), "cyber_logs.zip")

# --- MAIN DASHBOARD ---
col_left, col_right = st.columns([1, 1.8])

with col_left:
    st.markdown("### 🛠️ Advanced Log Filtering")
    # UPDATED: File uploader now highlights ZIP support
    uploaded = st.file_uploader("Upload .ADM, .RPT or .ZIP logs", accept_multiple_files=True)
    
    if uploaded:
        mode = st.selectbox("Analysis Mode", ["Full Activity per Player", "Area Activity Search", "Raid Watch", "Boosting Check"])
        search_filter = st.text_input("Player Search (Inside File Content)", "")
        
        if st.button("🚀 Process & Search"):
            with st.spinner("Extracting and scanning logs..."):
                extracted_data = process_uploaded_input(uploaded)
                
                final_results = []
                for entry in extracted_data:
                    # Filter based on player name if provided
                    if not search_filter or search_filter.lower() in entry['text'].lower():
                        if entry['name'].upper().endswith('.ADM'):
                            coords = parse_adm_data(entry['text'])
                            for c in coords:
                                c['Source File'] = entry['name']
                                final_results.append(c)
                
                if final_results:
                    df = pd.DataFrame(final_results)
                    st.success(f"Found {len(df)} matches in {len(extracted_data)} files.")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("Download CSV for iZurvive", df.to_csv(index=False), "scan_results.csv")
                else:
                    st.warning("No matches found for your search criteria.")

with col_right:
    st.markdown("### 📍 iZurvive Map")
    if st.button("🔄 Refresh Map Overlay"):
        st.session_state.mv = st.session_state.get('mv', 0) + 1
    
    m_url = f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}"
    components.iframe(m_url, height=850, scrolling=True)
