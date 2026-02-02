import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
import pytz 
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: TEAM ACCESS CONTROL
# ==============================================================================
team_accounts = {
    "cybersorfer": "cyber001",
    "Admin": "cyber001",
    "dirtmcgirrt": "dirt002",
    "TrapTyree": "trap003",
    "CAPTTipsyPants": "cap004"
}

# --- GLOBAL CREDENTIALS ---
FTP_HOST = "usla643.gamedata.io"
FTP_USER = "ni11109181_1"
FTP_PASS = "343mhfxd"

# --- TRANSLATION DICTIONARY (FROM YOUR DATA) ---
ITEM_TRANSLATIONS = {
    # Magazines
    "Mag_1911_7Rnd": "7rd 1911 Mag",
    "Mag_AK101_30Rnd": "30rd KA-101 Mag",
    "Mag_AK101_30Rnd_Green": "30rd KA-101 Mag (Green)",
    "Mag_AK74_30Rnd": "30rd KA-74 Mag",
    "Mag_AK74_45Rnd": "45rd KA-74 Mag",
    "Mag_AKM_30Rnd": "30rd KA-M Mag",
    "Mag_AKM_Drum75Rnd": "75rd KA-M Drum Mag",
    "Mag_AKM_Palm30Rnd": "30rd KA-M Polymer Mag",
    "Mag_Aug_30Rnd": "30rd Aur Mag",
    "Mag_CMAG_10Rnd": "10rd C-Mag (M4)",
    "Mag_CMAG_20Rnd": "20rd C-Mag (M4)",
    "Mag_CMAG_30Rnd": "30rd C-Mag (M4)",
    "Mag_CMAG_40Rnd": "40rd C-Mag (M4)",
    "Mag_CMAG_Green": "30rd C-Mag (Green)",
    "Mag_CZ527_5rnd": "5rd CR-527 Mag",
    "Mag_CZ550_10Rnd": "10rd Internal Mag (CZ550)",
    "Mag_CZ61_20Rnd": "20rd Skorpion Mag",
    "Mag_CZ75_15Rnd": "15rd CR-75 Mag",
    "Mag_Deagle_9rnd": "9rd Deagle Mag",
    "Mag_FAL_20Rnd": "20rd LAR Mag",
    "Mag_FAMAS_25Rnd": "25rd LE-MAS Mag",
    "Mag_FNX45_15Rnd": "15rd FX-45 Mag",
    "Mag_Glock_15Rnd": "15rd Mlock-91 Mag",
    "Mag_IJ70_8Rnd": "8rd IJ-70 Mag",
    "Mag_M14_10Rnd": "10rd DMR Mag",
    "Mag_M14_20Rnd": "20rd DMR Mag",
    "Mag_MKII_10Rnd": "10rd MK II Mag",
    "Mag_MP5_15Rnd": "15rd SG5-K Mag",
    "Mag_MP5_30Rnd": "30rd SG5-K Mag",
    "Mag_P1_8Rnd": "8rd P1 Mag",
    "Mag_PM73_15Rnd": "15rd PM73 Rak Mag",
    "Mag_PM73_25Rnd": "25rd PM73 Rak Mag",
    "Mag_PP19_64Rnd": "64rd Bizon Mag",
    "Mag_Ruger1022_15Rnd": "15rd Sporter Mag",
    "Mag_Ruger1022_30Rnd": "30rd Sporter Mag",
    "Mag_SSG82_5rnd": "5rd SSG 82 Mag",
    "Mag_STANAG_30Rnd": "30rd Standard Mag",
    "Mag_STANAG_30Rnd_Coupled": "60rd Coupled Mag",
    "Mag_STANAG_60Rnd": "60rd Standard Mag (M4)",
    "Mag_SV98_10Rnd": "10rd VS-98 Mag",
    "Mag_SVD_10Rnd": "10rd VSD Mag",
    "Mag_Saiga_5Rnd": "5rd Vaiga Mag",
    "Mag_Saiga_8Rnd": "8rd Vaiga Mag",
    "Mag_Saiga_Drum20Rnd": "20rd Vaiga Drum Mag",
    "Mag_Scout_5Rnd": "5rd Pioneer Mag",
    "Mag_UMP_25Rnd": "25rd USG-45 Mag",
    "Mag_VAL_20Rnd": "20rd SVAL Mag",
    "Mag_VSS_10Rnd": "10rd VSS Mag",
    "Mag_Vikhr_30Rnd": "30rd Vikhr Mag",
    
    # Pistols
    "CZ75": "CR-75",
    "Colt1911": "Kolt 1911",
    "Deagle": "Deagle",
    "Deagle_Gold": "Deagle (Gold)",
    "Derringer_Black": "Derringer (Black)",
    "Derringer_Grey": "Derringer (Grey)",
    "Derringer_Pink": "Derringer (Pink)",
    "Engraved1911": "Kolt 1911 (Engraved)",
    "FNX45": "FX-45",
    "Flaregun": "Flaregun",
    "Glock19": "Mlock-91",
    "Longhorn": "Longhorn",
    "MKII": "MK II",
    "Magnum": "Revolver",
    "MakarovIJ70": "IJ-70",
    "P1": "P1",

    # Rifles & Weapons
    "AK101": "KA-101",
    "AK101_Black": "KA-101 (Black)",
    "AK101_Green": "KA-101 (Green)",
    "AK74": "KA-74",
    "AK74_Black": "KA-74 (Black)",
    "AK74_Green": "KA-74 (Green)",
    "AKM": "KA-M",
    "AKS74U": "KAS-74U",
    "AKS74U_Black": "KAS-74U (Black)",
    "AKS74U_Green": "KAS-74U (Green)",
    "ASVAL": "SVAL",
    "Aug": "Aur A1",
    "AugShort": "Aur AX",
    "B95": "Blaze",
    "CZ527": "CR-527",
    "CZ527_Black": "CR-527 (Black)",
    "CZ527_Camo": "CR-527 (Camo)",
    "CZ527_Green": "CR-527 (Green)",
    "CZ550": "CZ 550",
    "CZ61": "Skorpion",
    "Crossbow_Autumn": "Crossbow (Autumn)",
    "Crossbow_Black": "Crossbow (Black)",
    "Crossbow_Summer": "Crossbow (Summer)",
    "Crossbow_Wood": "Crossbow (Wood)",
    "FAL": "LAR",
    "FAMAS": "LE-MAS",
    "Izh18": "BK-18",
    "Izh18Shotgun": "BK-133 (Single Shot)",
    "Izh43Shotgun": "BK-43",
    "M14": "DMR",
    "M16A2": "M16-A2",
    "M4A1": "M4-A1",
    "M4A1_Black": "M4-A1 (Black)",
    "M4A1_Green": "M4-A1 (Green)",
    "M79": "M79 Grenade Launcher",
    "MP5K": "SG5-K",
    "Mosin9130": "Mosin 91/30",
    "Mosin9130_Black": "Mosin 91/30 (Black)",
    "Mosin9130_Camo": "Mosin 91/30 (Camo)",
    "Mosin9130_Green": "Mosin 91/30 (Green)",
    "Mp133Shotgun": "BK-133",
    "PM73Rak": "PM-73 Rak",
    "PP19": "Bizon",
    "R12": "Sawed-off BK-43",
    "Repeater": "Repeater Carbine",
    "Ruger1022": "Sporter 22",
    "SKS": "SK 59/66",
    "SSG82": "SSG 82",
    "SV98": "VS-98",
    "SVD": "VSD",
    "SVD_Wooden": "VSD (Wood)",
    "Saiga": "Vaiga",
    "SawedoffB95": "Sawed-off Blaze",
    "SawedoffFAMAS": "Sawed-off LE-MAS",
    "SawedoffIzh18": "Sawed-off BK-18",
    "SawedoffIzh18Shotgun": "Sawed-off Izh 18 Shotgun",
    "SawedoffIzh43Shotgun": "Sawed-off BK-43",
    "SawedoffMagnum": "Sawed-off Revolver",
    "SawedoffMosin9130": "Sawed-off Mosin",
    "SawedoffMosin9130_Black": "Sawed-off Mosin (Black)",
    "SawedoffMosin9130_Camo": "Sawed-off Mosin (Camo)",
    "SawedoffMosin9130_Green": "Sawed-off Mosin (Green)",
    "Scout": "Pioneer",
    "Scout_Chernarus": "Pioneer (Chernarus)",
    "Scout_Livonia": "Pioneer (Livonia)",
    "UMP45": "USG-45",
    "VSS": "VSS",
    "Vikhr": "Vikhr",
    "Winchester70": "M70 Tundra"
}

def log_session(user, action):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headers = getattr(st.context, "headers", {})
    ip = headers.get("X-Forwarded-For", "Unknown/Local")
    entry = f"{now} | User: {user} | Action: {action} | IP: {ip}\n"
    try:
        with open("login_history.txt", "a") as f:
            f.write(entry)
    except: pass

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.subheader("🛡️ CyberDayZ Team Portal")
    u_in = st.text_input("Username", key="login_user")
    p_in = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        if u_in in team_accounts and team_accounts[u_in] == p_in:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = u_in
            log_session(u_in, "LOGIN")
            st.rerun()
        else:
            st.error("❌ Invalid Credentials")
    return False

# ==============================================================================
# SECTION 2: LOOT ANALYZER (FTP VERSION)
# ==============================================================================
def get_friendly_name(code_name):
    """
    Returns the In-Game name if found in dictionary.
    Otherwise, cleans up the code name.
    """
    if code_name in ITEM_TRANSLATIONS:
        return ITEM_TRANSLATIONS[code_name]
    
    # Fallback: Replace underscores and capitalization
    clean = code_name.replace("_", " ")
    return clean

def categorize_item(code_name):
    """Assigns category based on the known list or string pattern"""
    if "Mag_" in code_name: return "Magazine"
    
    # Check if it's in our pistols list (rough check using known pistol codes)
    pistols_set = ["Colt1911", "CZ75", "Deagle", "FNX45", "Glock19", "Magnum", "MKII", "P1", "MakarovIJ70", "Longhorn", "Derringer"]
    if any(p in code_name for p in pistols_set):
        return "Pistol"
    
    # Default to Rifle/Weapon for others
    return "Rifle/Weapon"

def run_loot_analyzer():
    st.header("🎯 Loot Economy & Rarity Tracker")

    # 1. Connect via FTP
    xml_content = None
    loaded_path = ""
    
    possible_paths = [
        "/dayzps_missions/dayzOffline.chernarusplus/db/types.xml", 
        "/dayzps/mpmissions/dayzOffline.chernarusplus/db/types.xml",
        "/dayzps/mpmissions/dayz_auto.chernarusplus/db/types.xml",
        "/dayzps/mpmissions/dayz_auto.enoch/db/types.xml",
        "/mpmissions/dayz_auto.chernarusplus/db/types.xml"
    ]

    with st.spinner(f"🔌 Connecting to FTP ({FTP_HOST})..."):
        try:
            ftp = FTP(FTP_HOST, timeout=30)
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            for path in possible_paths:
                try:
                    buf = io.BytesIO()
                    ftp.retrbinary(f"RETR {path}", buf.write)
                    xml_content = buf.getvalue().decode("utf-8", errors="ignore")
                    loaded_path = path
                    break 
                except Exception: continue
            ftp.quit()
        except Exception as e:
            st.error(f"FTP Connection Failed: {e}")
            return

    # 2. Parse Data
    if xml_content:
        try:
            root = ET.fromstring(xml_content)
            data = []
            
            for item in root.findall('type'):
                name = item.get('name', 'Unknown')
                
                # Filter: Only process items in our Translation List OR known patterns
                # This ensures we mostly get the Guns and Mags we care about
                is_weapon = any(x in name for x in ["Weapon", "Rifle", "Pistol", "Shotgun", "Gun", "Mag_"])
                in_dict = name in ITEM_TRANSLATIONS
                
                if is_weapon or in_dict:
                    nominal = int(item.find('nominal').text) if item.find('nominal') is not None else 0
                    min_val = int(item.find('min').text) if item.find('min') is not None else 0
                    
                    category = "Magazine" if "Mag_" in name else categorize_item(name)
                    
                    # Rarity Logic
                    if nominal <= 3: rarity = "💎 Ultra Rare"
                    elif nominal <= 10: rarity = "🔴 Hard"
                    elif nominal <= 25: rarity = "🟡 Medium"
                    else: rarity = "🟢 Common"
                    
                    data.append({
                        "Item Name": get_friendly_name(name),
                        "Category": category,
                        "Nominal": nominal,
                        "Min": min_val,
                        "Rarity": rarity,
                        "_code": name # Hidden column for sorting/debugging
                    })

            df = pd.DataFrame(data)

            # --- Controls ---
            st.success(f"✅ Loaded {len(df)} items from `{loaded_path}`")
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search = st.text_input("🔍 Search Item", placeholder="e.g. AKM")
            with col2:
                cat_filter = st.multiselect("Filter Category", ["Rifle/Weapon", "Pistol", "Magazine"], default=["Rifle/Weapon", "Pistol", "Magazine"])
            with col3:
                sort_option = st.selectbox("Sort By", ["Item Name", "Nominal", "Rarity"])

            # Apply Filters
            if search:
                df = df[df['Item Name'].str.contains(search, case=False)]
            
            df = df[df['Category'].isin(cat_filter)]
            
            # Apply Sort
            if sort_option == "Nominal":
                df = df.sort_values(by="Nominal", ascending=True)
            elif sort_option == "Rarity":
                df = df.sort_values(by="Nominal", ascending=True) 
            else:
                df = df.sort_values(by="Item Name")

            # Display Table (HEIGHT INCREASED to 1200)
            st.dataframe(
                df, 
                height=1200, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Item Name": st.column_config.TextColumn("In-Game Name", width="large"),
                    "Category": st.column_config.TextColumn("Category", width="small"),
                    "Nominal": st.column_config.NumberColumn("Max", width="small"),
                    "Min": st.column_config.NumberColumn("Min", width="small"),
                    "Rarity": st.column_config.TextColumn("Rarity Tier", width="medium"),
                    "_code": None # Hide this column
                }
            )

        except Exception as e:
            st.error(f"Error parsing XML file: {e}")
    else:
        st.error(f"❌ Could not find 'types.xml'. Tried these paths: {possible_paths}")

# ==============================================================================
# MAIN APPLICATION BLOCK
# ==============================================================================
if check_password():
    if 'page_configured' not in st.session_state:
        st.set_page_config(page_title="CyberDayZ Ultimate Scanner", layout="wide", initial_sidebar_state="expanded")
        st.session_state.page_configured = True

    # Session State
    if 'mv' not in st.session_state: st.session_state.mv = 0
    if 'all_logs' not in st.session_state: st.session_state.all_logs = []
    if 'track_data' not in st.session_state: st.session_state.track_data = {}
    if 'raw_download' not in st.session_state: st.session_state.raw_download = ""
    if 'current_mode' not in st.session_state: st.session_state.current_mode = "Filter"
    
    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #8b949e !important; }
        section[data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
        .stMarkdown, p, label, .stSubheader, .stHeader, h1, h2, h3, h4, span { color: #8b949e !important; }
        div.stButton > button { color: #c9d1d9 !important; background-color: #21262d !important; border: 1px solid #30363d !important; font-weight: bold !important; border-radius: 6px; }
        .death-log { color: #ff4b4b !important; font-weight: bold; border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 5px; background: #2a1212; }
        .connect-log { color: #28a745 !important; border-left: 3px solid #28a745; padding-left: 10px; margin-bottom: 5px; background: #122a16; }
        .disconnect-log { color: #ffc107 !important; border-left: 3px solid #ffc107; padding-left: 10px; margin-bottom: 5px; background: #2a2612; }
        </style>
        """, unsafe_allow_html=True)

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("🧭 Navigation")
        app_mode = st.radio("Select Tool", ["Log Scanner", "Loot Economy"])
        st.divider()

    # ==============================================================================
    # MODE 1: LOG SCANNER
    # ==============================================================================
    if app_mode == "Log Scanner":
        
        def get_ftp_connection():
            try:
                ftp = FTP(FTP_HOST, timeout=20)
                ftp.login(user=FTP_USER, passwd=FTP_PASS)
                ftp.cwd("/dayzps/config")
                return ftp
            except: return None

        # Logic Helpers
        def make_izurvive_link(coords):
            if coords: return f"https://www.izurvive.com/chernarusplus/#location={coords[0]};{coords[1]}"
            return ""

        def extract_player_and_coords(line):
            name, coords = "System/Server", None
            try:
                if 'Player "' in line: name = line.split('Player "')[1].split('"')[0]
                if "pos=<" in line:
                    raw = line.split("pos=<")[1].split(">")[0]
                    parts = [p.strip() for p in raw.split(",")]
                    coords = [float(parts[0]), float(parts[1])] 
            except: pass 
            return str(name), coords

        def calculate_distance(p1, p2):
            if not p1 or not p2: return 999999
            return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

        def filter_logs(files, mode, target_player=None, area_coords=None, area_radius=500):
            grouped_report, boosting_tracker = {}, {}
            raw_filtered_lines = []
            
            now_str = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
            header = f"******************************************************************************\nAdminLog started on {now_str}\n\n"

            building_keys = ["placed", "built", "constructed", "base", "wall", "gate", "platform", "watchtower"]
            raid_keys = ["dismantled", "folded", "unmount", "destroyed", "packed", "cut"]
            session_keys = ["connected", "disconnected", "died", "killed", "suicide"]
            boosting_objects = ["fence kit", "nameless object", "fireplace", "garden plot", "barrel"]

            for uploaded_file in files:
                uploaded_file.seek(0)
                lines = uploaded_file.read().decode("utf-8", errors="ignore").splitlines()
                for line in lines:
                    if "|" not in line: continue
                    try:
                        time_part = line.split(" | ")[0]
                        clean_time = time_part.split("]")[-1].strip() if "]" in time_part else time_part.strip()
                    except: clean_time = "00:00:00"

                    name, coords = extract_player_and_coords(line)
                    low = line.lower()
                    should_process = False

                    if mode == "Full Activity per Player":
                        if target_player and target_player == name: should_process = True
                    elif mode == "Building Only (Global)":
                        if any(k in low for k in building_keys) and "pos=" in low: should_process = True
                    elif mode == "Raid Watch (Global)":
                        if any(k in low for k in raid_keys) and "pos=" in low: should_process = True
                    elif mode == "Session Tracking (Global)":
                        if any(k in low for k in session_keys): should_process = True
                    elif mode == "Area Activity Search":
                        if coords and area_coords:
                            if calculate_distance(coords, area_coords) <= area_radius: should_process = True
                    elif mode == "Suspicious Boosting Activity":
                        try: 
                            curr_t = datetime.strptime(clean_time, "%H:%M:%S")
                            if any(k in low for k in ["placed", "built"]) and any(obj in low for obj in boosting_objects):
                                if name not in boosting_tracker: boosting_tracker[name] = []
                                boosting_tracker[name].append({"time": curr_t, "pos": coords})
                                if len(boosting_tracker[name]) >= 3:
                                    prev = boosting_tracker[name][-3]
                                    if (curr_t - prev["time"]).total_seconds() <= 300 and calculate_distance(coords, prev["pos"]) < 15:
                                        should_process = True
                        except: continue

                    if should_process:
                        raw_filtered_lines.append(f"{line.strip()}\n")
                        status = "normal"
                        if any(d in low for d in ["died", "killed"]): status = "death"
                        elif "connected" in low: status = "connect"
                        elif "disconnected" in low: status = "disconnect"
                        entry = {"time": clean_time, "text": line.strip(), "link": make_izurvive_link(coords), "status": status}
                        if name not in grouped_report: grouped_report[name] = []
                        grouped_report[name].append(entry)
                        
            return grouped_report, header + "".join(raw_filtered_lines)

        # --- SIDEBAR & FTP (Original) ---
        with st.sidebar:
            st.markdown("### 🐺 Admin Portal")
            debug_mode = st.toggle("🐞 Debug Mode")
            st.header("Nitrado FTP Manager")
            date_range = st.date_input("Select Date Range:", value=(datetime.now() - timedelta(days=1), datetime.now()))
            hours_list = [time(h, 0) for h in range(24)]
            t_cols = st.columns(2)
            start_t_obj = t_cols[0].selectbox("From:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=0)
            end_t_obj = t_cols[1].selectbox("To:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=23)
            cb_cols = st.columns(3)
            show_adm = cb_cols[0].checkbox("ADM", True); show_rpt = cb_cols[1].checkbox("RPT", True); show_log = cb_cols[2].checkbox("LOG", True)
            
            if st.button("🔄 Sync FTP List", use_container_width=True):
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    ftp = get_ftp_connection()
                    if ftp:
                        files_raw = []
                        ftp.retrlines('MLSD', files_raw.append)
                        processed = []
                        start_dt = datetime.combine(start_date, start_t_obj).replace(tzinfo=pytz.UTC)
                        end_dt = datetime.combine(end_date, end_t_obj).replace(hour=end_t_obj.hour, minute=59, second=59, tzinfo=pytz.UTC)
                        for line in files_raw:
                            filename = line.split(';')[-1].strip()
                            exts = ([".ADM"] if show_adm else []) + ([".RPT"] if show_rpt else []) + ([".LOG"] if show_log else [])
                            if any(filename.upper().endswith(e) for e in exts):
                                if 'modify=' in line:
                                    m_str = next(p for p in line.split(';') if 'modify=' in p).split('=')[1]
                                    try:
                                        dt = datetime.strptime(m_str, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                                        if start_dt <= dt <= end_dt:
                                            processed.append({"real": filename, "dt": dt, "display": f"{filename} ({dt.strftime('%m/%d %I:%M%p')})"})
                                    except: continue
                        st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                        ftp.quit()

            if st.session_state.all_logs:
                st.success(f"✅ Found {len(st.session_state.all_logs)} files")
                all_opts = [f['display'] for f in st.session_state.all_logs]
                select_all = st.checkbox("Select All Files")
                selected_disp = st.multiselect("Select Logs:", options=all_opts, default=all_opts if select_all else [])
                if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                    buf = io.BytesIO()
                    ftp_z = get_ftp_connection()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for disp in selected_disp:
                            real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                            f_data = io.BytesIO(); ftp_z.retrbinary(f"RETR {real_name}", f_data.write)
                            zf.writestr(real_name, f_data.getvalue())
                    ftp_z.quit()
                    st.download_button("💾 Download ZIP", buf.getvalue(), "cyber_logs.zip", use_container_width=True)

        # --- MAIN DASHBOARD (Original) ---
        col1, col2 = st.columns([1, 2.5])
        with col1:
            st.markdown("### 🛠️ Ultimate Log Processor")
            uploaded_files = st.file_uploader("Upload Logs", accept_multiple_files=True)
            if uploaded_files:
                mode = st.selectbox("Mode", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
                st.session_state.current_mode = mode 
                
                t_p, area_coords, area_radius = None, None, 500
                if mode == "Full Activity per Player":
                    names = set()
                    for f in uploaded_files:
                        f.seek(0)
                        names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
                    t_p = st.selectbox("Player", sorted(list(names)))
                
                elif mode == "Area Activity Search":
                    presets = {"Custom / Paste": None, "Tisy": [1542, 13915], "NWAF": [4530, 10245], "VMC": [3824, 8912]}
                    loc = st.selectbox("Locations", list(presets.keys()))
                    if loc == "Custom / Paste":
                        raw_paste = st.text_input("Paste iZurvive Coords (X / Y)", placeholder="10146.06 / 3953.27")
                        if raw_paste and "/" in raw_paste:
                            try:
                                parts = raw_paste.split("/")
                                val_x, val_z = float(parts[0].strip()), float(parts[1].strip())
                            except: val_x, val_z = 0.0, 0.0
                        else:
                            c1, c2 = st.columns(2)
                            val_x, val_z = c1.number_input("X", value=0.0), c2.number_input("Z", value=0.0)
                        area_coords = [val_x, val_z]
                    else:
                        area_coords = presets[loc]
                    area_radius = st.slider("Radius (Meters)", 50, 5000, 500)
                
                if st.button("🚀 Process Logs", use_container_width=True):
                    with st.spinner("Analyzing..."):
                        report, raw = filter_logs(uploaded_files, mode, t_p, area_coords, area_radius)
                        st.session_state.track_data, st.session_state.raw_download = report, raw

            if st.session_state.get("track_data"):
                clean_mode = st.session_state.current_mode.replace(" ", "_").replace("(", "").replace(")", "")
                file_name = f"{clean_mode}.adm"
                st.download_button(f"💾 Save {file_name}", st.session_state.raw_download, file_name)
                
                for player, events in st.session_state.track_data.items():
                    with st.expander(f"👤 {player} ({len(events)} events)"):
                        for ev in events:
                            st.markdown(f"<div class='{ev['status']}-log'>[{ev['time']}] {ev['text']}</div>", unsafe_allow_html=True)
                            if ev['link']: st.link_button("📍 Map", ev['link'])

        with col2:
            if st.button("🔄 Refresh Map"): st.session_state.mv += 1
            components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.mv}", height=850, scrolling=True)

    # ==============================================================================
    # MODE 2: LOOT ECONOMY (New Feature)
    # ==============================================================================
    elif app_mode == "Loot Economy":
        run_loot_analyzer()
