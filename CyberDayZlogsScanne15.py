# ==============================================================================
    # SECTION 4: SIDEBAR & FTP (UPDATED WITH COUNT & SELECT ALL)
    # ==============================================================================
    with st.sidebar:
        st.markdown("### 🐺 Admin Portal")
        st.divider()
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
            else:
                st.error("Select both start and end dates.")

        # --- NEW FEATURES BELOW ---
        if st.session_state.all_logs:
            # Display Number of Files Found
            st.success(f"✅ Found {len(st.session_state.all_logs)} files")
            
            # Select All Feature
            all_options = [f['display'] for f in st.session_state.all_logs]
            select_all = st.checkbox("Select All Files")
            
            selected_disp = st.multiselect(
                "Select Logs:", 
                options=all_options,
                default=all_options if select_all else []
            )
            
            if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp_z = get_ftp_connection()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                        f_data = io.BytesIO(); ftp_z.retrbinary(f"RETR {real_name}", f_data.write)
                        zf.writestr(real_name, f_data.getvalue())
                ftp_z.quit()
                st.download_button("💾 Download ZIP", buf.getvalue(), "dayz_logs.zip", use_container_width=True)
