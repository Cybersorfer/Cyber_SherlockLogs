import streamlit as st
import requests

# --- CONFIGURATION ---
API_TOKEN = "CWBuIFx8j-KkbXDO0r6WGiBAtP_KSUiz11iQFxuB4jkU6r0wm9E9G1rcr23GuSfI8k6ldPOWseNuieSUnuV6UXPSSGzMWxzat73F"
SERVICE_ID = "18159994"

def get_api_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}

def try_download(path_guess):
    """Attempts to download a specific file without listing directory first."""
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/download?file={path_guess}"
    try:
        res = requests.get(url, headers=get_api_headers())
        if res.status_code == 200:
            return True, res.json()['data']['token']['url']
        return False, None
    except:
        return False, None

st.set_page_config(page_title="DayZ Anchor Test")
st.title("⚓ Path Triangulation")
st.write("We are testing 3 theories to find where your files live.")

if st.button("🚀 Run Connection Test"):
    
    # THEORY 1: Root is inside 'dayzps' folder
    # We look for the config file directly
    path1 = "serverDZ_Private.cfg" 
    found1, url1 = try_download(path1)
    
    # THEORY 2: Root is the User folder
    # We look for 'dayzps/config file'
    path2 = "dayzps/serverDZ_Private.cfg"
    found2, url2 = try_download(path2)
    
    # THEORY 3: Logs are in the Profiles folder (Common for Console)
    # We try to grab a generic profile file
    path3 = "dayzps/config/Users/Survivor/Server.core.xml"
    found3, url3 = try_download(path3)

    st.divider()
    
    if found1:
        st.success(f"✅ **THEORY 1 PASSED!**")
        st.write("Your API Root is ALREADY inside the `dayzps` folder.")
        st.info("**CORRECT PATH TO USE:** `config` (NOT `dayzps/config`)")
        
    elif found2:
        st.success(f"✅ **THEORY 2 PASSED!**")
        st.write("Your API Root is the server base.")
        st.info("**CORRECT PATH TO USE:** `dayzps/config`")
        
    elif found3:
        st.success(f"✅ **THEORY 3 PASSED!**")
        st.write("Found deeply nested config.")
        st.info("**CORRECT PATH TO USE:** `dayzps/config`")
        
    else:
        st.error("❌ All download attempts failed.")
        st.write("This likely means the 'File Server' feature is disabled for your Token.")
        st.caption("Double check that your Nitrado Token has 'Files > Download' permissions checked.")
