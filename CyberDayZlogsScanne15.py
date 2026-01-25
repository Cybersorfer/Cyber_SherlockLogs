import streamlit as st
import pandas as pd
import ftplib
import io
import re
import time
from datetime import datetime

# --- CONFIGURATION ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"
FTP_PATH = "/dayzps/config"

# --- CORE FUNCTIONS ---
def connect_ftp():
    """Establishes connection and forces BINARY mode."""
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        # FIX: Force Binary Mode immediately to fix '550 SIZE' error
        ftp.voidcmd("TYPE I") 
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_latest_files(ftp):
    """Finds the newest RPT (Live) and ADM (Building) files."""
    try:
        ftp.cwd(FTP_PATH)
        # Using nlst() which is safer than mlsd() on some servers
        files = ftp.nlst()
        
        # Sort by name (names contain timestamps: DayZServer...2026_01_25...)
        rpt_files = sorted([f for f in files if f.lower().endswith(".rpt")])
        adm_files = sorted([f for f in files if f.lower().endswith(".adm")])
        
        return {
            "RPT": rpt_files[-1] if rpt_files else None,
            "ADM": adm_files[-1] if adm_files else None
        }
    except Exception as e:
        st.warning(f"Listing Error: {e}")
        return {"RPT": None, "ADM": None}

def fetch_new_data(ftp, filename, last_size):
    """Smart Fetch: Checks size in BINARY mode and downloads if newer."""
    try:
        # This command (SIZE) caused the error before; it should work now in TYPE I
        current_size = ftp.size(filename)
        
        # If file hasn't grown, skip download
        if current_size <= last_size and last_size != 0:
            return None, current_size 
            
        # Download content
        r_buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", r_buffer.write)
        content = r_buffer.getvalue()
        
        return content, current_size
    except Exception as e:
        st.error(f"Read Error on {filename}: {e}")
        return None, last_size

def parse_live_events(content, file_type):
    """Extracts high-value events."""
    events = []
    # Decode with 'replace' to prevent crashing on weird characters
    decoded = content.decode('latin-1', errors='replace')
    lines = decoded.split('\n')
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        
        # Timestamp extraction (first 8 chars usually HH:MM:SS)
        ts = clean_line[:8] if len(clean_line) > 8 and ":" in clean_line[:8] else "Unknown"
        
        # --- RPT EVENTS (LIVE) ---
        if file_type == "RPT":
            if "Player" in line and "connected" in line:
                events.append({"Time": ts, "Type": "🟢 Connect", "Details": clean_line})
            elif "Player" in line and "disconnected" in line:
                events.append({"Time": ts, "Type": "🔴 Disconnect", "Details": clean_line})
            elif "hit by" in line or "killed by" in line or "died" in line:
                events.append({"Time": ts, "Type": "💀 KILLFEED", "Details": clean_line})
            elif "VehicleRespawner" in line and "Respawning" in line:
                events.append({"Time": ts, "Type": "🚗 Vehicle Spawn", "Details": clean_line})

        # --- ADM EVENTS (DELAYED/BUFFERED) ---
        elif file_type == "ADM":
            # Building/Dismantling
            if "placed" in line or "built" in line:
                events.append({"Time": ts, "Type": "🔨 Building", "Details": clean_line})
            elif "dismantled" in line:
                events.append({"Time": ts, "Type": "🪓 Dismantle", "Details": clean_line})
            
            # Movement/Position (Only capture if it has coordinates)
            elif "pos=<" in line:
                # We typically only care about movement related to other events, 
                # but if you want RAW movement, un-comment the next lines:
                # events.append({"Time": ts, "Type": "📍 Position", "Details": clean_line})
                pass

    return events

# --- STATE MANAGEMENT ---
if 'last_rpt_size' not in st.session_state:
    st.session_state.last_rpt_size = 0
if 'last_adm_size' not in st.session_state:
    st.session_state.last_adm_size = 0
if 'live_feed' not in st.session_state:
    st.session_state.live_feed = []

# --- UI ---
st.set_page_config(page_title="DayZ Live Bot", layout="wide")
st.title("🤖 Cyber DayZ Live Bot")
st.markdown("Polls server logs every time you click **'Check Now'** to find new events.")

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("🔄 CHECK FOR ACTIVITY", use_container_width=True):
        with st.spinner("Connecting to Nitrado..."):
            ftp = connect_ftp()
            if ftp:
                files = get_latest_files(ftp)
                new_events_found = 0
                
                # 1. Process RPT (Live Data)
                if files['RPT']:
                    content, new_size = fetch_new_data(ftp, files['RPT'], st.session_state.last_rpt_size)
                    if content:
                        batch = parse_live_events(content, "RPT")
                        
                        # Logic: If first run, show last 10. If update, show new ones.
                        # Simple logic: Just grab last 10 for display to avoid complexity
                        st.session_state.live_feed = batch[-20:] + st.session_state.live_feed
                        
                        st.session_state.last_rpt_size = new_size
                        new_events_found += len(batch)
                        st.success(f"RPT: Read {new_size} bytes")
                
                # 2. Process ADM (Building Data)
                if files['ADM']:
                    content, new_size = fetch_new_data(ftp, files['ADM'], st.session_state.last_adm_size)
                    if content:
                        batch = parse_live_events(content, "ADM")
                        
                        st.session_state.live_feed = batch[-20:] + st.session_state.live_feed
                        
                        st.session_state.last_adm_size = new_size
                        new_events_found += len(batch)
                        st.success(f"ADM: Read {new_size} bytes")

                ftp.quit()
                
                # Limit feed size
                st.session_state.live_feed = st.session_state.live_feed[:100]
                
                if new_events_found == 0:
                    st.info("No new activity detected.")

    # Status Display
    st.metric("Events in Feed", len(st.session_state.live_feed))
    st.caption(f"Tracking RPT Size: {st.session_state.last_rpt_size}")
    st.caption(f"Tracking ADM Size: {st.session_state.last_adm_size}")

with col2:
    st.subheader("📢 Activity Feed")
    
    if st.session_state.live_feed:
        # Sort feed by time descending (optional, depending on how you want to see it)
        # For now, we display the list as appended (Latest scans on top logic handled above)
        
        for event in st.session_state.live_feed:
            # Color coding
            color = "gray"
            if "Connect" in event['Type']: color = "green"
            if "Disconnect" in event['Type']: color = "red"
            if "KILL" in event['Type']: color = "orange"
            if "Building" in event['Type']: color = "blue"
            
            st.markdown(f":{color}[**{event['Time']}**] `{event['Type']}` : {event['Details']}")
            st.divider()
    else:
        st.write("Waiting for data... Click the button on the left.")
