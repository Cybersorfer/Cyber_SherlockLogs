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
    """Establishes connection."""
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
        # Listing files often forces the server into ASCII mode
        files = ftp.nlst()
        
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
    """Smart Fetch: Checks size and downloads if newer."""
    try:
        # CRITICAL FIX: Force Binary Mode before checking size
        # This fixes the "550 SIZE not allowed in ASCII mode" error
        ftp.voidcmd("TYPE I")
        
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
    decoded = content.decode('latin-1', errors='replace')
    lines = decoded.split('\n')
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line: continue
        
        ts = clean_line[:8] if len(clean_line) > 8 and ":" in clean_line[:8] else "Unknown"
        
        if file_type == "RPT":
            if "Player" in line and "connected" in line:
                events.append({"Time": ts, "Type": "🟢 Connect", "Details": clean_line})
            elif "Player" in line and "disconnected" in line:
                events.append({"Time": ts, "Type": "🔴 Disconnect", "Details": clean_line})
            elif any(k in line for k in ["hit by", "killed by", "died"]):
                events.append({"Time": ts, "Type": "💀 KILLFEED", "Details": clean_line})
            elif "VehicleRespawner" in line and "Respawning" in line:
                events.append({"Time": ts, "Type": "🚗 Vehicle Spawn", "Details": clean_line})

        elif file_type == "ADM":
            if "placed" in line or "built" in line:
                events.append({"Time": ts, "Type": "🔨 Building", "Details": clean_line})
            elif "dismantled" in line:
                events.append({"Time": ts, "Type": "🪓 Dismantle", "Details": clean_line})
            elif "pos=<" in line:
                # To reduce spam, we only log pos if it's explicitly about building/transport
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
                        # Logic to only show latest lines on update
                        show_count = 10 if st.session_state.last_rpt_size == 0 else 5
                        st.session_state.live_feed = batch[-show_count:] + st.session_state.live_feed
                        
                        st.session_state.last_rpt_size = new_size
                        new_events_found += len(batch)
                        st.toast(f"RPT Updated: {files['RPT']}")
                
                # 2. Process ADM (Building Data)
                if files['ADM']:
                    content, new_size = fetch_new_data(ftp, files['ADM'], st.session_state.last_adm_size)
                    if content:
                        batch = parse_live_events(content, "ADM")
                        show_count = 10 if st.session_state.last_adm_size == 0 else 5
                        st.session_state.live_feed = batch[-show_count:] + st.session_state.live_feed
                        
                        st.session_state.last_adm_size = new_size
                        new_events_found += len(batch)
                        st.toast(f"ADM Updated: {files['ADM']}")

                ftp.quit()
                
                # Keep feed manageable (last 100 events)
                st.session_state.live_feed = st.session_state.live_feed[:100]
                
                if new_events_found == 0:
                    st.info("No new activity since last check.")

    # Status Display
    st.metric("Events in Feed", len(st.session_state.live_feed))
    st.caption(f"Tracking RPT Size: {st.session_state.last_rpt_size}")
    st.caption(f"Tracking ADM Size: {st.session_state.last_adm_size}")

with col2:
    st.subheader("📢 Activity Feed")
    if st.session_state.live_feed:
        for event in st.session_state.live_feed:
            color = "gray"
            if "Connect" in event['Type']: color = "green"
            if "Disconnect" in event['Type']: color = "red"
            if "KILL" in event['Type']: color = "orange"
            if "Building" in event['Type']: color = "blue"
            
            st.markdown(f":{color}[**{event['Time']}**] `{event['Type']}` : {event['Details']}")
            st.divider()
    else:
        st.write("Waiting for data... Click the button on the left.")
