import streamlit as st
import io
import os
import pandas as pd

# Setup Page Config
st.set_page_config(page_title="CyberDayZ Log Scanner", layout="wide", page_icon="🛡️")

# --- GEODATA ---
CHERNARUS_LOCATIONS = {
    "Chernogorsk (Черногорск)": (6700, 2500, 1200),
    "Elektrozavodsk (Электрозаводск)": (10300, 2300, 1000),
    "Berezino (Березино)": (12900, 9200, 1000),
    "Severograd (Североград)": (11000, 12400, 800),
    "Zelenogorsk (Зеленогорск)": (2700, 5200, 800),
    "Novodmitrovsk (Новодмитровск)": (11500, 14200, 1000),
    "Krasnostav (Красностав)": (11100, 13000, 600),
    "NW Airfield (NWAF)": (13470, 13075, 1000),
    "Tisy Military Base": (11500, 14200, 800),
    "Radio Zenit / Altar": (4200, 8600, 400),
    "Stary Sobor (Старый Собор)": (6100, 7600, 500),
    "Novy Sobor (Новый Собор)": (7000, 7600, 400),
    "Gorka (Горка)": (9500, 6500, 500),
}

def is_in_town(line, town_coords, radius):
    try:
        if "pos=<" not in line: return False
        coord_part = line.split("pos=<")[1].split(">")[0]
        x, z = map(float, coord_part.split(",")[:2])
        return abs(x - town_coords[0]) <= radius and abs(z - town_coords[1]) <= radius
    except: return False

def process_logs(uploaded_files):
    all_lines = []
    for f in uploaded_files:
        stringio = io.StringIO(f.getvalue().decode("utf-8", errors="ignore"))
        all_lines.extend([l for l in stringio if "|" in l and ":" in l])
    return all_lines

# --- WEB UI ---
st.title("🛡️ CyberDayZ Log Scanner & Analytics")
st.markdown("---")

uploaded_files = st.file_uploader("Upload your .ADM or .RPT files to begin", type=['adm', 'rpt'], accept_multiple_files=True)

if uploaded_files:
    all_lines = process_logs(uploaded_files)
    
    # Extract Data for Dashboard
    players = sorted(list(set(line.split('"')[1] for line in all_lines if 'Player "' in line)))
    deaths = [l for l in all_lines if any(x in l.lower() for x in ["killed", "died", "suicide", "bled out"])]
    placements = [l for l in all_lines if any(x in l.lower() for x in ["placed", "built", "mounted"])]
    raids = [l for l in all_lines if any(x in l.lower() for x in ["dismantled", "unmount", "packed", "barbedwirehit"])]

    # --- ROW 1: STATS DASHBOARD ---
    st.subheader("📊 Server Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unique Players", len(players))
    col2.metric("Total Kills/Deaths", len(deaths))
    col3.metric("Base Placements", len(placements))
    col4.metric("Raid Actions", len(raids))

    st.markdown("---")

    # --- ROW 2: FILTERS ---
    st.subheader("🎯 Extraction Tools")
    mode = st.selectbox("What data do you want to extract?", [
        "Select an option...",
        "Activity per Specific Player", 
        "All Death Locations (Killfeed)", 
        "All Placements (Base Building)", 
        "Session Tracking (Login/Logout)", 
        "RAID WATCH (Destructive Actions)",
        "TOWN / LANDMARK SEARCH"
    ])

    final_output = []
    header = "******************************************************************************\nAdminLog started on Merged_Web_Session\n"

    if mode == "Activity per Specific Player":
        search = st.text_input("Search Player Name:")
        suggestions = [p for p in players if search.lower() in p.lower()]
        target_player = st.selectbox("Select Player from Results", suggestions)
        
        sub = st.radio("Detail Level", ["Full History", "Movement Only", "Movement + Building", "Movement + Raid Watch", "Session Tracking"], horizontal=True)
        
        if st.button("Generate Player Log"):
            for line in all_lines:
                low = line.lower()
                if target_player in line:
                    if sub == "Full History": final_output.append(line)
                    elif sub == "Movement Only" and "pos=" in low: final_output.append(line)
                    elif sub == "Movement + Building" and ("pos=" in low or "placed" in low or "built" in low) and "hit" not in low: final_output.append(line)
                    elif sub == "Movement + Raid Watch" and ("pos=" in low or "dismantled" in low or "unmount" in low) and "built" not in low: final_output.append(line)
                    elif sub == "Session Tracking" and "connect" in low: final_output.append(line)

    elif mode == "TOWN / LANDMARK SEARCH":
        town = st.selectbox("Select Map Area", sorted(list(CHERNARUS_LOCATIONS.keys())))
        coords, radius = CHERNARUS_LOCATIONS[town]
        if st.button(f"Search {town}"):
            final_output = [l for l in all_lines if is_in_town(l, coords, radius)]
            found = set(l.split('"')[1] for l in final_output if 'Player "' in l)
            st.success(f"Found {len(found)} players in {town}: {', '.join(found)}")

    elif mode != "Select an option...":
        if st.button(f"Generate {mode}"):
            if "Death" in mode: final_output = deaths
            elif "Placements" in mode: final_output = placements
            elif "RAID" in mode: final_output = raids
            elif "Session" in mode: final_output = [l for l in all_lines if "connect" in l.lower()]

    if final_output:
        final_output.sort()
        result_text = header + "".join(final_output)
        st.download_button("📥 Download Filtered File", result_text, file_name="FILTERED_LOG.adm")
        st.text_area("Data Preview", result_text[:2000], height=300)
else:
    st.info("👋 Welcome! Please upload one or more .ADM files from your Nitrado server to start analyzing player activity.")
