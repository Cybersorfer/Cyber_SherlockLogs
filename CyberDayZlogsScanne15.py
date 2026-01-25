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
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        return ftp
    except Exception as e:
        st.error(f"FTP Connection Failed: {e}")
        return None

def get_latest_files(ftp):
    """Finds the newest RPT (Live) and ADM (Building) files."""
    try:
        ftp.cwd(FTP_PATH)
        files = ftp.nlst()
        
        # Sort by name (which includes timestamp) to get newest
        rpt_files = sorted([f for f in files if f.lower().endswith(".rpt")])
        adm_files = sorted([f for f in files if f.lower().endswith(".adm")])
        
        return {
            "RPT": rpt_files[-1] if rpt_files else None,
            "ADM": adm_files[-1] if adm_files else None
        }
    except:
        return {"RPT": None, "ADM": None}

def fetch_new_data(ftp, filename, last_size):
    """Smart Fetch: Only downloads if the file has grown."""
    try:
        # Get current file size
        current_size = ftp.size(filename)
        
        if current_size == last_size:
            return None, current_size # No new data
            
        # Download usually grabs the whole file, but we process only new lines in memory
        # (FTP 'REST' command for partial download is flaky on some servers, so we grab full and slice)
        r_buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {filename}", r_buffer.write)
        content = r_buffer.getvalue()
        
        return content, current_size
    except Exception as e:
        st.error(f"Read Error: {e}")
        return None, last_size

def parse_live_events(content, file_type):
    """Extracts high-value events."""
    events = []
    decoded = content.decode('latin-1', errors='ignore')
    lines = decoded.split('\n')
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        
        # Timestamp extraction (HH:MM:SS)
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
            if "placed" in line or "built" in line:
                events.append({"Time": ts, "Type": "🔨 Building", "Details": clean_line})
            elif "dismantled" in line:
                events.append({"Time": ts, "Type": "🪓 Dismantle", "Details": clean_line})
            elif "pos=<" in line:
                # Only grab movement if it's associated with an action
                if any(x in line for x in ["placed", "Transport", "built"]):
                    events.append({"Time": ts, "Type": "📍 Position", "Details": clean_line})

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
st.markdown("Polls server logs every time you click **'Check Now'** to find new events since the last check.")

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("🔄 CHECK FOR ACTIVITY", use_container_width=True):
        with st.spinner("Connecting to Nitrado..."):
            ftp = connect_ftp()
            if ftp:
                files = get_latest_files(ftp)
                new_events = []
                
                # 1. Process RPT (Live Data)
                if files['RPT']:
                    content, new_size = fetch_new_data(ftp, files['RPT'], st.session_state.last_rpt_size)
                    if content:
                        # Only parse if size changed (or first run)
                        # Optimization: In a real bot, you'd calculate byte offset. 
                        # Here we re-parse and just take the bottom ones for simplicity in Streamlit.
                        batch = parse_live_events(content, "RPT")
                        
                        # Just grab the last few if it's the first load, or all if it's an update
                        if st.session_state.last_rpt_size == 0:
                            new_events.extend(batch[-10:]) # Show last 10 on startup
                        else:
                            # In a perfect world we slice the string, but for now we just show the fresh parse
                            # A simple dedup logic could go here
                            new_events.extend(batch[-5:]) 
                        
                        st.session_state.last_rpt_size = new_size
                        st.toast(f"RPT Updated: {len(batch)} events found")
                
                # 2. Process ADM (Building Data)
                if files['ADM']:
                    content, new_size = fetch_new_data(ftp, files['ADM'], st.session_state.last_adm_size)
                    if content:
                        batch = parse_live_events(content, "ADM")
                        if st.session_state.last_adm_size == 0:
                            new_events.extend(batch[-10:])
                        else:
                            new_events.extend(batch[-5:])
                        
                        st.session_state.last_adm_size = new_size
                        st.toast(f"ADM Updated: {len(batch)} events found")
                    else:
                        # If size didn't change
                        pass

                ftp.quit()
                
                if new_events:
                    # Add new events to the top of the feed
                    # Sort to ensure order
                    st.session_state.live_feed = new_events + st.session_state.live_feed
                else:
                    st.info("No new data written to disk yet.")

    # Status Display
    st.metric("Live Feed Count", len(st.session_state.live_feed))
    st.caption(f"Tracking RPT: {st.session_state.last_rpt_size} bytes")
    st.caption(f"Tracking ADM: {st.session_state.last_adm_size} bytes")

with col2:
    st.subheader("📢 Activity Feed")
    if st.session_state.live_feed:
        for event in st.session_state.live_feed:
            # Color coding
            icon = event['Type'][0] # Grab the emoji
            color = "gray"
            if "Connect" in event['Type']: color = "green"
            if "Disconnect" in event['Type']: color = "red"
            if "KILL" in event['Type']: color = "orange"
            if "Building" in event['Type']: color = "blue"
            
            st.markdown(f":{color}[**{event['Time']}**] `{event['Type']}` : {event['Details']}")
            st.divider()
    else:
        st.write("Waiting for data... Click the button on the left.")
