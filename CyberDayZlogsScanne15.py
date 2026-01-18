import os

# --- UPDATED CHERNARUS GEODATA ---
# Categories: Major City (800-1200m), Strategic/Military (600-1000m), Village/Town (300-500m)
CHERNARUS_LOCATIONS = {
    # MAJOR CITIES
    "Chernogorsk (Черногорск)": (6700, 2500, 1200),
    "Elektrozavodsk (Электрозаводск)": (10300, 2300, 1000),
    "Berezino (Березино)": (12900, 9200, 1000),
    "Severograd (Североград)": (11000, 12400, 800),
    "Zelenogorsk (Зеленогорск)": (2700, 5200, 800),
    "Novodmitrovsk (Новодмитровск)": (11500, 14200, 1000),
    "Krasnostav (Красностав)": (11100, 13000, 600),

    # MILITARY & STRATEGIC LANDMARKS
    "NW Airfield (NWAF)": (13470, 13075, 1000),
    "Tisy Military Base": (11500, 14200, 800),
    "Vybor Military (VMC)": (3800, 6400, 500),
    "Radio Zenit / Altar": (4200, 8600, 400),
    "Green Mountain Tower": (3700, 5900, 400),
    "Rify Shipwreck": (13400, 9200, 500),
    "Prison Island": (2100, 1300, 600),
    "Balota Airfield": (5000, 2400, 600),

    # INLAND TOWNS & VILLAGES
    "Stary Sobor (Старый Собор)": (6100, 7600, 500),
    "Novy Sobor (Новый Собор)": (7000, 7600, 400),
    "Gorka (Горка)": (9500, 6500, 500),
    "Vybor (Выбор)": (3800, 8900, 400),
    "Grishino (Гришино)": (5900, 5000, 400),
    "Kabanino (Кабанино)": (5300, 6700, 400),
    "Mogilevka (Могилевка)": (7500, 10200, 400),
    "Staroye (Старое)": (10100, 9900, 400),
    "Guglovo (Гуглово)": (8400, 8600, 300),
    "Topolka Dam": (10300, 8000, 300),
}

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_unique_filename(base_path):
    if not os.path.exists(base_path): return base_path
    fn, ext = os.path.splitext(base_path)
    counter = 1
    while os.path.exists(f"{fn}_{counter}{ext}"): counter += 1
    return f"{fn}_{counter}{ext}"

def is_in_town(line, town_coords, radius):
    try:
        if "pos=<" not in line: return False
        coord_part = line.split("pos=<")[1].split(">")[0]
        x, z = map(float, coord_part.split(",")[:2])
        return abs(x - town_coords[0]) <= radius and abs(z - town_coords[1]) <= radius
    except: return False

def filter_adm_files(file_paths):
    all_lines = []
    header = "******************************************************************************\n"
    header += "AdminLog started on Location_Search_Session\n"

    for path in file_paths:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines.extend([l for l in f if "|" in l and ":" in l])

    print("\n--- MAIN MENU ---")
    print("[1] Activity per Player")
    print("[2] Killfeed")
    print("[3] Placements")
    print("[4] Session Tracking")
    print("[5] RAID WATCH")
    print("[6] TOWN / LANDMARK SEARCH")
    
    choice = input("\nSelect: ")
    final_output = []

    if choice == '6':
        locs = sorted(list(CHERNARUS_LOCATIONS.keys()))
        for i, name in enumerate(locs):
            print(f"[{i}] {name}")
        
        l_idx = int(input("\nSelect location number: "))
        town_name = locs[l_idx]
        coords, radius = CHERNARUS_LOCATIONS[town_name]
        
        print(f"Searching for activity in {town_name}...")
        for line in all_lines:
            if is_in_town(line, coords, radius):
                final_output.append(line)
        
        players = set(l.split('"')[1] for l in final_output if 'Player "' in l)
        print(f"\nPlayers found in {town_name}: {', '.join(players) if players else 'None'}")

    # Standard filtering logic for other options...
    # (Simplified for briefness, keep your previous full logic for options 1-5)

    final_output.sort()
    ref_path = file_paths[0] if isinstance(file_paths, list) else file_paths
    save_path = os.path.join(get_script_dir(), f"FILTERED_{os.path.basename(ref_path)}")
    final_path = get_unique_filename(save_path)
    with open(final_path, 'w', encoding='utf-8') as f:
        f.write(header)
        f.writelines(final_output)
    print(f"SUCCESS! File saved at: {final_path}")

def main():
    selected_files = []
    while True:
        if not selected_files:
            current_dir = get_script_dir()
            files = [f for f in os.listdir(current_dir) if f.upper().endswith(('.ADM', '.RPT'))]
            if not files: break
            for idx, f in enumerate(files): print(f"[{idx}] {f}")
            selection = input("\nEnter file numbers: ")
            try:
                indices = [int(x.strip()) for x in selection.split(',')]
                selected_files = [os.path.join(current_dir, files[i]) for i in indices]
            except: continue
        filter_adm_files(selected_files)
        rep = input("\n[1] Same Files | [2] Different Files | [3] Exit: ")
        if rep == '2': selected_files = []
        elif rep == '3': break

if __name__ == "__main__":
    main()
