import streamlit as st
import pandas as pd
import ftplib
import io
import re
from datetime import datetime, timedelta

# --- 1. CREDENTIALS ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config"

# --- 2. CORE FUNCTIONS ---
def connect_ftp():
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_recent_files(ftp):
    """Finds the most recently modified ADM and RPT files."""
    try:
        ftp.cwd(FTP_PATH)
        files = []
        
        # Get detailed list to check modification times (if server supports it)
        # Fallback: Sort by name since DayZ logs include timestamps in filenames
        # Format: DayZServer_PS4_x64_2026_01_21_15_23_02.ADM
        filenames = ftp.nlst()
        
        adm_files = [f for f in filenames if f.lower().endswith(".adm")]
        rpt_files = [f for f in filenames if f.lower().endswith(".rpt")]
        
        adm_files.sort()
        rpt_files.sort()
        
        return {
            "ADM": adm_files[-1] if adm_files else None,
            "RPT": rpt_files[-1] if rpt_files else None
        }
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return {"ADM": None, "RPT": None}

def download_file(ftp, filename):
    try:
        r_buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", r_buffer.write)
        r_buffer.seek(0)
        return r_buffer.read()
    except:
        return None

def parse_hybrid_data(adm_content, rpt_content):
    """Combines movement data (ADM) with live connection data (RPT)."""
    data = []
    
    # 1. Parse ADM (Positions/Building) - Often Stale
    if adm_content:
        decoded_adm = adm_content.decode('latin-1', errors='ignore')
        pos_pattern = re.compile(r"pos=<(\d+\.\d+),\s*\d+\.\d+,\s*(\d+\.\d+)>")
        
        for line in decoded_adm.split('\n'):
            if any(k in line for k in ["placed", "built", "dismantled", "killed", "died", "Transport"]):
                ts = line[:8] if "|" not in line[:10] else "Live"
                coords = "N/A"
                match = pos_pattern.search(line)
                if match: coords = f"{match.group(1)}, {match.group(2)}"
                
                cat = "🏗️ Base/Move"
                if "killed" in line or "died" in line: cat = "💀 Death"
                
                data.append({"Source": "ADM (Map)", "Time": ts, "Type": cat, "Info": line.strip()[:100], "Coords": coords})

    # 2. Parse RPT (Connections/System) - Often Fresher
    if rpt_content:
        decoded_rpt = rpt_content.decode('latin-1', errors='ignore')
        for line in decoded_rpt.split('\n'):
            # Filter for Login, Logout, Kick
            if any(k in line for k in ["Player", "connected", "disconnected", "kicked", "Login"]):
                # Clean up timestamp from RPT format usually "17:46:16.728"
                ts = line.split(" ")[0] if len(line) > 8 else "Unknown"
                
                if "connected" in line:
                    data.append({"Source": "RPT (Sys)", "Time": ts, "Type": "🟢 Connect", "Info": line.strip(), "Coords": "N/A"})
                elif "disconnected" in line or "kicked" in line:
                    data.append({"Source": "RPT (Sys)", "Time": ts, "Type": "🔴 Disconnect", "Info": line.strip(), "Coords": "N/A"})

    # Sort all events by Time (Text sort isn't perfect but works for HH:MM:SS)
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="Time", ascending=False)
        
    return df

# --- 3. APP UI ---
st.set_page_config(page_title="DayZ Live Hybrid Scanner", layout="wide")

st.title("📡 DayZ Live Monitor (Hybrid ADM/RPT)")
st.info("Because DayZ buffers map data (ADM) until restart, we also scan system logs (RPT) to see who is online right now.")

if st.button("🔥 SCAN FOR LATEST ACTIVITY", use_container_width=True):
    with st.spinner("Connecting to Server..."):
        ftp = connect_ftp()
        if ftp:
            # 1. Identify Files
            targets = get_recent_files(ftp)
            st.write(f"**Targeting Files:**")
            col1, col2 = st.columns(2)
            col1.success(f"🗺️ Map Log: `{targets['ADM']}`")
            col2.warning(f"⚙️ System Log: `{targets['RPT']}`")
            
            # 2. Download Content
            adm_data = download_file(ftp, targets['ADM']) if targets['ADM'] else None
            rpt_data = download_file(ftp, targets['RPT']) if targets['RPT'] else None
            
            ftp.quit()
            
            # 3. Parse & Merge
            if adm_data or rpt_data:
                df = parse_hybrid_data(adm_data, rpt_data)
                
                if not df.empty:
                    # Filter for activity "Near the end" (simple approach)
                    st.subheader("Combined Timeline (Newest First)")
                    st.dataframe(df, use_container_width=True)
                    
                    # CSV Export
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Combined Report", csv, "hybrid_report.csv", "text/csv")
                else:
                    st.warning("Files downloaded, but no relevant events found.")
            else:
                st.error("Failed to download logs.")
