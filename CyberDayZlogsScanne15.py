def run_loot_analyzer(api_key, server_id):
    st.header("🕵️ Debugging Connection")
    
    # 1. Try to list the root directory to find your user folder name
    # We look at the root "/games/" folder first
    url = f"https://api.nitrado.net/services/{server_id}/gameservers/file_server/list?path=/games/"
    headers = {'Authorization': f'Bearer {api_key}'}
    
    st.info("Attempting to find your server files...")
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if response.status_code == 200 and 'data' in data:
            st.success("Connected! Here are the folders found in '/games/':")
            
            # Display the folders found
            entries = data['data']['entries']
            for entry in entries:
                st.write(f"📁 **Found Folder:** `{entry['name']}`")
                
                # If we find a folder that looks like a username (starts with ni...), let's look inside
                if entry['name'].startswith("ni"):
                    user_folder = entry['name']
                    st.write(f"--- Drilling down into `{user_folder}` ---")
                    
                    # Construct the probable path to types.xml
                    # Most DayZ servers follow: /games/[user_id]/no_ip_1/mpmissions/dayz_auto.chernarusplus/db/types.xml
                    probable_path = f"/games/{user_folder}/no_ip_1/mpmissions/dayz_auto.chernarusplus/db/types.xml"
                    st.code(probable_path, language="text")
                    st.warning(f"👆 Copy the path above and paste it into your code variable 'file_path'")
                    
        else:
            st.error(f"API Error: {data.get('message', 'Unknown Error')}")
            st.write("Full Response:", data)
            
    except Exception as e:
        st.error(f"Critical Code Error: {e}")
