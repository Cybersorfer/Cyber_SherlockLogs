import streamlit as st
import io

# --- VERIFIED CHERNARUS GEODATA ---
# Format: "Location Name": (X_coord, Z_coord, Radius_in_meters)
CHERNARUS_LOCATIONS = {
    "NW Airfield (NWAF)": (13470, 13075, 1000),
    "Severograd (Североград)": (11000, 12400, 800),
    "Zelenogorsk (Зеленогорск)": (2700, 5200, 800),
    "Stary Sobor (Старый Собор)": (6100, 7600, 500),
    "Novy Sobor (Новый Собор)": (7000, 7600, 400),
    "Gorka (Горка)": (9500, 6500, 500),
    "Vybor (Выбор)": (3800, 8900, 400),
    "Radio Zenit / Altar": (4200, 8600, 400),
    "Krasnostav (Красностав)": (11100, 13000, 600),
    "Tisy Military Base": (11500, 14200, 800),
    "Rify Shipwreck": (13400, 9200, 500),
    "Prison Island": (2100, 1300, 600),
    "Berezino (Березино)": (12900, 9200, 1000),
    "Chernogorsk (Черногорск)": (6700, 2500, 1200),
    "Elektrozavodsk (Электрозаводск)": (10300, 2300, 1000),
}

def is_in_requested_area(line, target_coords, radius):
    """Parses pos=<X, Z, Y> and compares to geodata."""
    try:
        if "pos=<" not in line: return False
        coord_part = line.split("pos=<")[1].split(">")[0]
        x, z = map(float, coord_part.split(",")[:2])
        # Simple distance check for fast processing
        return abs(x - target_coords[0]) <= radius and abs(z - target_coords[1]) <= radius
    except:
        return False

# --- WEB UI FOR LOCATION FILTERING ---
st.subheader("📍 Location-Based Activity Filter")
selected_area = st.selectbox("Select Location to Analyze", sorted(CHERNARUS_LOCATIONS.keys()))

if st.button(f"Extract Activity for {selected_area}"):
    if 'all_lines' in locals() or 'all_lines' in st.session_state:
        target_coords, radius = CHERNARUS_LOCATIONS[selected_area]
        
        # Filter lines based on geofence
        area_activity = [l for l in all_lines if is_in_requested_area(l, target_coords, radius)]
        
        if area_activity:
            # Identify players who were in the area
            found_players = set(l.split('"')[1] for l in area_activity if 'Player "' in l)
            st.success(f"Found {len(area_activity)} events involving: {', '.join(found_players)}")
            
            # Prepare for download
            header = "******************************************************************************\n"
            header += f"AdminLog - Activity Filtered for: {selected_area}\n"
            final_file = header + "".join(area_activity)
            
            st.download_button(
                label=f"📥 Download {selected_area} Log",
                data=final_file,
                file_name=f"ACTIVITY_{selected_area.replace(' ', '_')}.adm",
                mime="text/plain"
            )
            st.text_area("Area Preview", final_file[:2000], height=300)
        else:
            st.warning(f"No player activity recorded in {selected_area} for these logs.")
