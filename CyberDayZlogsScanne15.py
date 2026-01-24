# ==============================================================================
    # SECTION 4: SIDEBAR & FTP (UPDATED FOR DATE RANGE)
    # ==============================================================================
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        st.divider()
        st.header("Nitrado FTP Manager")
        
        # FIX: Changed to allow date range selection
        date_range = st.date_input(
            "Select Date Range:",
            value=(datetime.now() - timedelta(days=1), datetime.now()),
            help="Select the start and end date. If you only want one day, click it twice."
        )
        
        hours_list = [time(h, 0) for h in range(24)]
        t_cols = st.columns(2)
        start_t_obj = t_cols[0].selectbox("From Hour:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=0)
        end_t_obj = t_cols[1].selectbox("To Hour:", options=hours_list, format_func=lambda t: t.strftime("%I:00%p").lower(), index=23)
        
        cb_cols = st.columns(3)
        show_adm = cb_cols[0].checkbox("ADM", True); show_rpt = cb_cols[1].checkbox("RPT", True); show_log = cb_cols[2].checkbox("LOG", True)
        
        if st.button("🔄 Sync FTP List", use_container_width=True):
            # Ensure the user has selected both a start and end date
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                ftp = get_ftp_connection()
                if ftp:
                    files_raw = []
                    with st.spinner(f"Scanning from {start_date} to {end_date}..."):
                        ftp.retrlines('MLSD', files_raw.append)
                    
                    processed = []
                    # Create precise UTC timestamps for the full range
                    start_dt = datetime.combine(start_date, start_t_obj).replace(tzinfo=pytz.UTC)
                    end_dt = datetime.combine(end_date, end_t_obj).replace(hour=end_t_obj.hour, minute=59, second=59, tzinfo=pytz.UTC)
                    
                    for line in files_raw:
                        filename = line.split(';')[-1].strip()
                        # Extension Filter
                        valid_exts = []
                        if show_adm: valid_exts.append(".ADM")
                        if show_rpt: valid_exts.append(".RPT")
                        if show_log: valid_exts.append(".LOG")
                        
                        if any(filename.upper().endswith(ext) for ext in valid_exts):
                            if 'modify=' in line:
                                m_str = next(p for p in line.split(';') if 'modify=' in p).split('=')[1]
                                try:
                                    dt = datetime.strptime(m_str, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                                    # Date Range Check
                                    if start_dt <= dt <= end_dt:
                                        processed.append({
                                            "real": filename, 
                                            "dt": dt, 
                                            "display": f"{filename} ({dt.strftime('%m/%d %I:%M %p')})"
                                        })
                                except: continue
                                
                    st.session_state.all_logs = sorted(processed, key=lambda x: x['dt'], reverse=True)
                    ftp.quit()
                    
                    if not st.session_state.all_logs:
                        st.sidebar.warning("No logs found in that range.")
                    else:
                        st.sidebar.success(f"Found {len(st.session_state.all_logs)} logs.")
            else:
                st.sidebar.error("Please select both a Start and End date on the calendar.")
