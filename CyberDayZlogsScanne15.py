# ==============================================================================
    # SECTION 5: MAIN DASHBOARD (UPDATED WITH IZURVIVE PASTE)
    # ==============================================================================
    col1, col2 = st.columns([1, 2.5])
    with col1:
        st.markdown("### 🛠️ Ultimate Log Processor")
        uploaded_files = st.file_uploader("Upload Logs", accept_multiple_files=True)
        if uploaded_files:
            mode = st.selectbox("Mode", ["Full Activity per Player", "Session Tracking (Global)", "Building Only (Global)", "Raid Watch (Global)", "Suspicious Boosting Activity", "Area Activity Search"])
            t_p, area_coords, area_radius = None, None, 500
            
            if mode == "Full Activity per Player":
                names = set()
                for f in uploaded_files:
                    f.seek(0)
                    names.update(re.findall(r'Player "([^"]+)"', f.read().decode("utf-8", errors="ignore")))
                t_p = st.selectbox("Player", sorted(list(names)))
            
            elif mode == "Area Activity Search":
                presets = {
                    "Custom / Paste": None, 
                    "Tisy Military": [1542, 13915], 
                    "NWAF": [4530, 10245],
                    "VMC": [3824, 8912],
                    "Zelenogorsk": [2540, 5085],
                    "Radio Zenit": [8355, 5978]
                }
                loc = st.selectbox("Locations", list(presets.keys()))
                
                if loc == "Custom / Paste":
                    # Feature: Paste "10146.06 / 3953.27" directly
                    raw_paste = st.text_input("Paste from iZurvive (X / Y)", placeholder="10146.06 / 3953.27")
                    
                    # Logic to parse the paste or use manual numbers
                    if raw_paste and "/" in raw_paste:
                        try:
                            parts = raw_paste.split("/")
                            val_x = float(parts[0].strip())
                            val_z = float(parts[1].strip())
                        except:
                            val_x, val_z = 0.0, 0.0
                            st.error("Invalid format. Use: 0000.00 / 0000.00")
                    else:
                        c_col1, c_col2 = st.columns(2)
                        val_x = c_col1.number_input("Manual X", value=0.0)
                        val_z = c_col2.number_input("Manual Z", value=0.0)
                    
                    area_coords = [val_x, val_z]
                else:
                    area_coords = presets[loc]
                    st.info(f"Target: {area_coords}")
                
                area_radius = st.slider("Radius (Meters)", 50, 5000, 500)

            if st.button("🚀 Process Logs", use_container_width=True):
                report, raw = filter_logs(uploaded_files, mode, t_p, area_coords, area_radius)
                st.session_state.track_data = report
                st.session_state.raw_download = raw
