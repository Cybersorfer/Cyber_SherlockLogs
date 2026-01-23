# ==============================================================================
    # SECTION 6: UI LAYOUT & SIDEBAR
    # ==============================================================================
    with st.sidebar:
        st.title("🐺 Admin Console")
        st.write(f"Logged in: **{st.session_state['current_user']}**")
        if st.button("🔌 Log Out"):
            log_session(st.session_state['current_user'], "LOGOUT")
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()

        # --- UPDATED LIVE ACTIVITY HEADER WITH TIME CLOCKS ---
        st.subheader("🔥 Live activity (Past 1hr)")
        
        # Helper to get the actual server file time
        def get_server_now():
            ftp = get_ftp_connection()
            if ftp:
                files_data = []
                ftp.retrlines('MLSD', files_data.append)
                # Find the most recently modified ADM file
                adm_files = [line for line in files_data if line.split(';')[-1].strip().upper().endswith('.ADM')]
                if adm_files:
                    # Sort by modification time in MLSD data
                    latest = sorted(adm_files, key=lambda x: {p.split('=')[0]: p.split('=')[1] for p in x.split(';') if '=' in p}['modify'])[-1]
                    info = {p.split('=')[0]: p.split('=')[1] for p in latest.split(';') if '=' in p}
                    server_time = datetime.strptime(info['modify'], "%Y%m%d%H%M%S")
                    ftp.quit()
                    return server_time.strftime("%H:%M:%S")
            if ftp: ftp.quit()
            return "Syncing..."

        # Display Server Time (from FTP) and Local Time (from your PC)
        t_col1, t_col2 = st.columns(2)
        t_col1.metric("Server Time", get_server_now())
        t_col2.metric("My Time Zone", datetime.now().strftime("%H:%M:%S"))

        if st.button("📡 Scan Live Log"):
            with st.spinner("Reaching Nitrado..."):
                st.session_state.live_log_data = fetch_live_activity()
        
        if "live_log_data" in st.session_state:
            with st.container(height=300):
                for entry in st.session_state.live_log_data:
                    st.markdown(f<div class='live-log'>{entry}</div>", unsafe_allow_html=True)

        st.divider()
        # --- END OF UPDATED SECTION ---

        if st.session_state['current_user'] in ["cybersorfer", "Admin"]:
            with st.expander("🛡️ Security Audit"):
                try:
                    with open("login_history.txt", "r") as f: st.text_area("Audit Log", f.read(), height=200)
                except: st.write("No logs yet.")

        st.header("Nitrado FTP Manager")
        
        # ... [Rest of your sidebar code remains exactly as it was] ...
