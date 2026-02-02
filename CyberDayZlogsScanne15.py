def run_loot_analyzer(api_key, server_id):
    st.header("🎯 Loot Economy & Rarity Tracker")
    
    # Nitrado API endpoint for file download
    # We target the 'types.xml' located in your missions folder
    # Note: Adjust the path if your mission folder has a different name
    file_path = "/games/ni1234567_1/no_ip_1/mpmissions/dayz_auto.chernarusplus/db/types.xml" 
    
    url = f"https://api.nitrado.net/services/{server_id}/gameservers/file_server/download?file={file_path}"
    headers = {'Authorization': f'Bearer {api_key}'}
    
    try:
        # 1. Get the download URL from Nitrado
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            download_url = response.json().get('data', {}).get('url')
            
            # 2. Download the actual XML content
            xml_response = requests.get(download_url)
            xml_content = xml_response.text
            
            # 3. Parse the XML
            root = ET.fromstring(xml_content)
            data = []
            
            for item in root.findall('type'):
                name = item.get('name', 'Unknown')
                
                # Filters for Weapons and Mags
                is_weapon = any(x in name for x in ["Weapon", "Rifle", "Pistol", "Shotgun", "Gun"])
                is_mag = "Mag_" in name
                
                if is_weapon or is_mag:
                    nominal = int(item.find('nominal').text) if item.find('nominal') is not None else 0
                    min_val = int(item.find('min').text) if item.find('min') is not None else 0
                    category = "Magazine" if is_mag else "Weapon"
                    
                    # Rarity Logic
                    if nominal <= 3: rarity = "💎 Ultra Rare"
                    elif nominal <= 10: rarity = "🔴 Hard"
                    elif nominal <= 25: rarity = "🟡 Medium"
                    else: rarity = "🟢 Common"
                    
                    data.append({
                        "Item Name": name,
                        "Type": category,
                        "Nominal": nominal,
                        "Min": min_val,
                        "Rarity": rarity
                    })

            df = pd.DataFrame(data)

            # --- UI Controls ---
            col1, col2 = st.columns([2, 1])
            with col1:
                search = st.text_input("🔍 Search Item Name", placeholder="e.g. M4A1")
            with col2:
                sort_option = st.selectbox("Sort By", ["Item Name", "Nominal", "Rarity"])

            # Filter Logic
            if search:
                df = df[df['Item Name'].str.contains(search, case=False)]
            
            df = df.sort_values(by=sort_option)

            # Display Dataframe
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Stats Summary
            st.success(f"Successfully synced: {len(df)} items found in types.xml")
            
        else:
            st.error("Could not fetch types.xml. Check your file path in the script.")
            
    except Exception as e:
        st.error(f"Error connecting to Nitrado: {e}")
