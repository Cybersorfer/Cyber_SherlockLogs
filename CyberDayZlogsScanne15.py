# ==============================================================================
# SECTION 5: 🛠️ ULTIMATE LOG PROCESSOR (EXACT SYNC LOGIC)
# ==============================================================================
def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
    grouped_report, player_positions, boosting_tracker = {}, {}, {}
    raw_filtered_lines = []
    # Dynamic header for the generated file
    header = f"******************************************************************************\nFiltered AdminLog | Mode: {mode} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    all_lines = []
    for uploaded_file in files:
        uploaded_file.seek(0)
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        all_lines.extend(content.splitlines())

    # Logic-defining Keywords
    building_keys = ["placed", "built", "built base", "built wall", "built gate", "built platform"]
    raid_keys = ["dismantled", "folded", "unmount", "unmounted", "packed"]
    session_keys = ["connected", "disconnected", "died", "killed"]
    boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]

    for line in all_lines:
        if "|" not in line: continue
        
        # Time and Player extraction
        time_part = line.split(" | ")[0]
        clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
        name, coords = extract_player_and_coords(line)
        
        if name != "System/Server" and coords: 
            player_positions[name] = coords
            
        low = line.lower()
        should_process = False

        # --- MATCHING UI LOGIC ---
        if mode == "Full Activity per Player":
            if target_player == name: 
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
                current_time = datetime.strptime(clean_time, "%H:%M:%S")
            except: 
                continue
            if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                if name not in boosting_tracker: 
                    boosting_tracker[name] = []
                boosting_tracker[name].append({"time": current_time, "pos": coords})
                
                # Check for 3+ items in the same spot within 5 minutes
                if len(boosting_tracker[name]) >= 3:
                    prev = boosting_tracker[name][-3]
                    time_diff = (current_time - prev["time"]).total_seconds()
                    dist_diff = calculate_distance(coords, prev["pos"])
                    if time_diff <= 300 and dist_diff < 15:
                        should_process = True

        # If line passed a filter, add to results
        if should_process:
            raw_filtered_lines.append(f"{line.strip()}\n") 
            link = make_izurvive_link(coords)
            
            # Determine UI color status
            status = "normal"
            if any(d in low for d in ["died", "killed"]): status = "death"
            elif "connect" in low: status = "connect"
            elif "disconnect" in low: status = "disconnect-log" # Matches your CSS

            event_entry = {"time": clean_time, "text": str(line.strip()), "link": link, "status": status}
            if name not in grouped_report: 
                grouped_report[name] = []
            grouped_report[name].append(event_entry)
    
    return grouped_report, header + "".join(raw_filtered_lines)
