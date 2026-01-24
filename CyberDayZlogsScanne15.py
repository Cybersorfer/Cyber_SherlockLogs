if selected_disp and st.button("📦 Prepare ZIP", use_container_width=True):
                buf = io.BytesIO()
                ftp_z = get_ftp_connection()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for disp in selected_disp:
                        real_name = next(f['real'] for f in st.session_state.all_logs if f['display'] == disp)
                        f_data = io.BytesIO(); ftp_z.retrbinary(f"RETR {real_name}", f_data.write)
                        zf.writestr(real_name, f_data.getvalue())
                ftp_z.quit()

                # --- DYNAMIC FILENAME LOGIC ---
                start_str = date_range[0].strftime("%m-%d")
                end_str = date_range[1].strftime("%m-%d")
                time_str = f"{start_t_obj.strftime('%H%M')}-{end_t_obj.strftime('%H%M')}"
                zip_filename = f"Logs_{start_str}_to_{end_str}_{time_str}.zip"
                
                st.download_button("💾 Download ZIP", buf.getvalue(), zip_filename, use_container_width=True)
