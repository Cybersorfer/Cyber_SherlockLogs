import streamlit as st
import requests

# --- CONFIGURATION ---
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def try_download(path_guess):
    """Attempts to download a specific file without listing directory first."""
    # Ensure no leading slash for relative path
    clean_path = path_guess.lstrip("/")
    
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={clean_path}"
    try:
        res = requests.get(url, headers=get_api_headers())
        
        # DEBUG: Print status to help troubleshoot
        st.write(f"Testing `{clean_path}` -> Status: {res.status_code}")
        
        if res.status_code == 200:
            return True, res.json()['data']['token']['url']
        return False, None
    except Exception as e:
        st.error(f"Error: {e}")
        return False, None

st.set_page_config(page_title="DayZ Anchor Test")
st.title("⚓ Path Triangulation (Blind Grab)")
st.info("Since 'List Files' is blocked, we will try to grab known files directly.")

if st.button("🚀 Run Connection Test"):
    
    st.subheader("Testing Theory 1: API is at Server Root")
    # Path taken directly from your RPT logs
    path1 = "dayzps/config/Users/Survivor/Server.core.xml"
    found1, url1 = try_download(path1)
    
    if found1:
        st.success("✅ **SUCCESS!** We downloaded `Server.core.xml`")
        st.markdown(f"**CONCLUSION:** Your correct log path is: `dayzps/config`")
        st.markdown("**Next Step:** We will build the scanner to blindly grab `.ADM` files from this path.")
        st.stop()
    
    st.subheader("Testing Theory 2: API is already inside 'dayzps'")
    # Try the same file, but assuming we are already in the dayzps folder
    path2 = "config/Users/Survivor/Server.core.xml"
    found2, url2 = try_download(path2)
    
    if found2:
        st.success("✅ **SUCCESS!** We downloaded `Server.core.xml`")
        st.markdown(f"**CONCLUSION:** Your correct log path is: `config`")
        st.stop()

    st.error("❌ Both attempts failed.")
    st.warning("""
    **Diagnosis:** Your Nitrado Token likely has 'Gameserver' permissions but is missing **'File Server'** permissions.
    
    **Fix:**
    1. Go to Nitrado > Developer Portal.
    2. Create a NEW Token.
    3. CHECK the box that says **"Files" (Download/List/Upload)**.
    4. Replace the token in this script.
    """)
