import streamlit as st
import pandas as pd
import ftplib
import io
import re
from datetime import datetime

# --- 1. CREDENTIALS (FROM YOUR ORIGINAL SCRIPT) ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
# We confirmed this path via your logs earlier
FTP_PATH = "/dayzps/config"

# --- 2. CORE FUNCTIONS ---
def connect_ftp():
    """Establishes connection to Nitrado FTP."""
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_latest_log(ftp, file_extension=".ADM"):
    """Finds the most recent log file in the config folder."""
    try:
        ftp.cwd(FTP_PATH)
        files = []
        
        # Get list of files with details to sort by date
        # Note: FTP listing can be tricky, we'll try a simple nlst and sort by name first
        # since DayZ logs usually contain timestamps in the name.
        filenames = ftp.nlst()
        
        # Filter for ADM logs
        targets = [f for f in filenames if f.lower().endswith(file_extension.lower())]
        
        if not targets:
            return None
            
        # Sort files (assuming standard naming allows sort by name, otherwise we'd need MDTM)
        targets.sort()
        latest_file = targets[-1] # The last one is usually the newest
        return latest_file
    except Exception as e:
        st.error(f"Error finding logs: {e}")
        return None

def download_log_content(ftp, filename):
    """Downloads the specific file into memory."""
    try:
        # Buffer to hold file in RAM
        r_buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", r_buffer.write)
        r_buffer.seek(0)
        return r_buffer.read()
    except Exception as e:
        st.error(f"Download Error: {e}")
        return None

def parse_activity(content):
    """Parses the log for Player and Base activity."""
    data = []
    # Decode latin-1 to handle special characters
    decoded = content.decode('latin-1', errors='ignore')
    
    # Regex for coordinates (X, Z)
    pos_pattern = re.compile(r"pos=<(\d+\.\d+),\s*\d+\.\d+,\s*(\d+\.\d+)>")
    
    for line in decoded.split('\n'):
        # Keywords we care about
        if any(k in line for k in ["placed", "built", "dismantled", "Transport", "killed", "died", "hit by"]):
            timestamp = line[:8] if "|" not in line[:10] else "Live"
            
            # Extract Coordinates
            coords = "N/A"
            match = pos_pattern.search(line)
            if match:
                coords = f"{match.group(1)}, {match.group(2)}"
            
            # Categorize
            category = "General"
            if "Transport" in line: category = "🚗 Vehicle"
            elif "placed" in line or "built" in line: category = "🔨 Base Building"
            elif "killed" in line or "hit by" in line: category = "💀 PvP/Death"
            
            data.append({
                "Time": timestamp,
                "Category": category,
                "Coords": coords,
                "Event": line.strip()
            })
            
    return pd.DataFrame(data)

# --- 3. APP UI ---
st.set_page_config(page_title="DayZ FTP Live Scanner", layout="wide")

with st.sidebar:
    st.title("📡 FTP Live Scanner")
    st.info(f"Host: {FTP_HOST}\nPath: {FTP_PATH}")
    
    scan_mode = st.radio("Scan Target:", [".ADM (Activity)", ".RPT (System)"])
    ext = ".ADM" if "ADM" in scan_mode else ".RPT"
    
    if st.button("🔥 SCAN NOW", use_container_width=True):
        with st.spinner("Connecting to FTP..."):
            ftp = connect_ftp()
            if ftp:
                st.session_state.ftp_status = "Connected"
                
                # Find Latest
                target_file = get_latest_log(ftp, ext)
                if target_file:
                    st.success(f"Found: {target_file}")
                    
                    # Download
                    content = download_log_content(ftp, target_file)
                    if content:
                        # Parse
                        df = parse_activity(content)
                        st.session_state.ftp_data = df
                        st.session_state.current_file = target_file
                    
                else:
                    st.warning(f"No {ext} files found in {FTP_PATH}")
                
                ftp.quit()

# --- MAIN DISPLAY ---
st.title("Cyber DayZ - Live Intelligence (FTP Mode)")

if 'ftp_data' in st.session_state:
    df = st.session_state.ftp_data
    
    col1, col2 = st.columns(2)
    col1.metric("Events Detected", len(df))
    col2.metric("Source Log", st.session_state.current_file)
    
    st.dataframe(df, use_container_width=True)
    
    # Export
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report", csv, "ftp_live_report.csv", "text/csv")

else:
    st.write("👈 Click **SCAN NOW** to pull live data directly via FTP.")
