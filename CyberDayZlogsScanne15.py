import streamlit as st
import pandas as pd
import re
from ftplib import FTP
import io
import zipfile
import math
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: AUTHENTICATION & SECURITY (TEAM ACCESS)
# ==============================================================================
team_accounts = {
    "cybersorfer": "cyber001",
    "Admin": "cyber001",
    "dirtmcgirrt": "dirt002",
    "TrapTyree": "trap003",
    "CAPTTipsyPants": "cap004"
}

def log_session(user, action):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = st.context.headers.get("X-Forwarded-For", "Local/Unknown")
    with open("login_history.txt", "a") as f:
        f.write(f"{now} | {user} | {action} | {ip}\n")

def check_password():
    if "password_correct" not in st.session_state:
        st.subheader("🛡️ Team Portal Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u in team_accounts and team_accounts[u] == p:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = u
                log_session(u, "LOGIN")
                st.rerun()
            else: st.error("Invalid Credentials")
        return False
    return True

if check_password():

    # ==============================================================================
    # SECTION 2: 🐺 NITRADO FTP MANAGER (RESTORED & LOCKED)
    # ==============================================================================
    FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH = "usla643.gamedata.io", "ni11109181_1", "343mhfxd", "/dayzps/config/"

    def get_ftp():
        ftp = FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        ftp.cwd(FTP_PATH)
        return ftp

    with st.sidebar:
        st.header("🐺 Nitrado FTP Manager")
        if st.button("🔄 Sync FTP Server"):
            try:
                ftp = get_ftp()
                lines = []
                ftp.retrlines('MLSD', lines.append)
                logs = []
                for line in lines:
                    p = {x.split('=')[0]: x.split('=')[1] for x in line.split(';') if '=' in x}
                    fname = line.split(';')[-1].strip()
                    if fname.upper().endswith(('.ADM', '.RPT', '.LOG')):
                        mtime = datetime.strptime(p['modify'], "%Y%m%d%H%M%S")
                        logs.append({"real": fname, "display": f"{fname} ({mtime.strftime('%m/%d %H:%M')})", "time": mtime})
                st.session_state.ftp_logs = sorted(logs, key=lambda x: x['time'], reverse=True)
                ftp.quit()
                st.success("Sync Complete")
            except Exception as e: st.error(f"FTP Error: {e}")

        if 'ftp_logs' in st.session_state:
            selected = st.multiselect("Select Files:", [f['display'] for f in st.session_state.ftp_logs])
            if selected and st.button("📦 Prepare ZIP"):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    ftp = get_ftp()
                    for s in selected:
                        real = next(f['real'] for f in st.session_state.ftp_logs if f['display'] == s)
                        fbuf = io.BytesIO()
                        ftp.retrbinary(f"RETR {real}", fbuf.write)
                        zf.writestr(real, fbuf.getvalue())
                    ftp.quit()
                st.download_button("💾 Download ZIP", buf.getvalue(), "logs.zip")

    # ==============================================================================
    # SECTION 3: 🛠️ ADVANCED LOG FILTERING (V14-11 EXACT LOGIC)
    # ==============================================================================
    def filter_logic(lines, mode, target_p=None, area_c=None, area_r=500):
        report, raw_out = {}, []
        # Chernarus Coordinate Parsing: X (index 0) and Z (index 2)
        for line in lines:
            if "|" not in line: continue
            name = line.split('Player "')[1].split('"')[0] if 'Player "' in line else "System"
            low = line.lower()
            match = False
            
            coords = None
            if "pos=<" in line:
                pts = line.split("pos=<")[1].split(">")[0].split(",")
                coords = [float(pts[0]), float(pts[2])]

            if mode == "Area Activity Search" and coords and area_c:
                dist = math.sqrt((coords[0]-area_c[0])**2 + (coords[1]-area_c[1])**2)
                if dist <= area_r: match = True
            elif mode == "Full Activity per Player": match = (name == target_p)
            elif mode == "Building Only (Global)": match = any(k in low for k in ["placed", "built"]) and "pos=" in low
            
            if match:
                raw_out.append(line.strip())
                status = "death" if "died" in low else "connect" if "connect" in low else "normal"
                if name not in report: report[name] = []
                report[name].append({"text": line.strip(), "status": status})
        return report, "\n".join(raw_out)

    st.markdown("### 🛠️ Advanced Log Filtering")
    uploaded = st.file_uploader("Upload Files", accept_multiple_files=True)
    if uploaded:
        presets = {"NWAF": [4530, 10245], "Tisy": [1542, 13915], "Zenit": [8355, 5978], "VMC": [3824, 8912]}
        mode = st.selectbox("Filter", ["Area Activity Search", "Full Activity per Player", "Building Only (Global)"])
        
        a_c, a_r, t_p = None, 500, None
        if mode == "Area Activity Search":
            choice = st.selectbox("Location", list(presets.keys()))
            a_c, a_r = presets[choice], st.slider("Radius", 50, 2000, 500)
        
        if st.button("🚀 Run Analysis"):
            all_lines = []
            for f in uploaded: all_lines.extend(f.read().decode("utf-8", errors="ignore").splitlines())
            rep, raw = filter_logic(all_lines, mode, t_p, a_c, a_r)
            st.session_state.results = (rep, raw)

    if "results" in st.session_state:
        st.download_button("💾 Download ADM", st.session_state.results[1], "filter.adm")
        for p, evs in st.session_state.results[0].items():
            with st.expander(f"👤 {p}"):
                for ev in evs: st.markdown(f"*{ev['text']}*")

    # ==============================================================================
    # SECTION 4: 📍 IZURVIVE MAP
    # ==============================================================================
    st.divider()
    if st.button("🔄 Refresh Map"): st.session_state.mv = st.session_state.get('mv', 0) + 1
    components.iframe(f"https://www.izurvive.com/serverlogs/?v={st.session_state.get('mv', 0)}", height=800)
