if st.button("🔥 Request Last Hour Data", use_container_width=True):
        with st.spinner("Talking to Nitrado API..."):
            # Set extension based on selection
            ext = ".adm" if "ADM" in live_file_category else ".rpt"
            
            # 1. Fetch file list via API
            # Note: Using your Service ID 18159994
            list_url = f"https://api.nitrado.net/services/18159994/gameservers/file_server/list?dir=/dayzps/config"
            list_res = requests.get(list_url, headers=get_api_headers())
            
            if list_res.status_code == 200:
                files = list_res.json().get('data', {}).get('entries', [])
                
                # FIX: Use .lower() to ensure we find .ADM, .adm, .RPT, or .rpt
                target_files = [f for f in files if f['name'].lower().endswith(ext)]
                
                if target_files:
                    # Get the most recently modified file
                    latest_file = max(target_files, key=lambda x: x['mtime'])
                    st.write(f"🔍 Found: {latest_file['name']}") # Debug info
                    
                    raw_content = fetch_live_log_via_api(latest_file['path'])
                    
                    if raw_content:
                        df = filter_live_activity(raw_content, live_file_category)
                        st.session_state['live_results'] = df
                        st.success(f"Analysis Complete: {latest_file['name']}")
                else:
                    # If /config is empty, try the profiles subfolder as a backup
                    st.error(f"No {ext.upper()} files found in /dayzps/config. Check if your logs are in a subfolder like /profiles.")
            else:
                st.error(f"API Connection Failed: {list_res.status_code}")
