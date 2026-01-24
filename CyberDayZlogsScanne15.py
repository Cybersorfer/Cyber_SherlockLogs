# ==============================================================================
# SECTION 5: 🛠️ ULTIMATE LOG PROCESSOR (FIXED & SYNCED)
# ==============================================================================
def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, player_positions, boosting_tracker = {}, {}, {}
    raw_filtered_lines = []
    header = f"******************************************************************************\nFiltered AdminLog | Mode: {mode} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    all_lines = []
    for uploaded_file in files:
        uploaded_file.seek(0)
        # Ensure we decode properly to avoid silent failures
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    session_keys = ["connected", "disconnected", "died", "killed"]
    boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]

    for line in all_lines:
        if "|" not in line: continue
        
        name, coords = extract_player_and_coords(line)
        if name != "System/Server" and coords: 
            player_positions[name] = coords
            
        low = line.lower()
        should_process = False

        # --- FIX: Time extraction must be robust to avoid UnboundLocalErrors ---
        try:
            time_part = line.split(" | ")[0]
            clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
        except:
            clean_time = "00:00:00"

        # --- CORE FILTERING LOGIC ---
        if mode == "Full Activity per Player":
            if target_player and target_player == name: 
                should_process = True
        
        elif mode == "Building Only (Global)":
            if any(k in low for k in building_keys) and "pos=" in low: 
                should_process = True
        
        elif mode == "Raid Watch (Global)":
            if any(k in low for k in raid_keys) and "pos=" in low: 
                should_process = True
        
        elif mode == "Session Tracking (Global)":
            if any(k in low for k in session_keys): 
                should_process = True
        
        elif mode == "Area Activity Search":
            if coords and area_coords:
                if calculate_distance(coords, area_coords) <= area_radius: 
                    should_process = True
        
        elif mode == "Suspicious Boosting Activity":
            try: 
                current_t_obj = datetime.strptime(clean_time, "%H:%M:%S")
                if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                    if name not in boosting_tracker: boosting_tracker[name] = []
                    boosting_tracker[name].append({"time": current_t_obj, "pos": coords})
                    
                    if len(boosting_tracker[name]) >= 3:
                        prev = boosting_tracker[name][-3]
                        if (current_t_obj - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                            should_process = True
            except: continue

        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            link = make_izurvive_link(coords)
            
            # CSS Class mapping
            status = "normal"
            if any(d in low for d in ["died", "killed"]): status = "death"
            elif "connected" in low: status = "connect"
            elif "disconnected" in low: status = "disconnect"

            event_entry = {"time": clean_time, "text": str(line.strip()), "link": link, "status": status}
            if name not in grouped_report: grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "".join(raw_filtered_lines)
