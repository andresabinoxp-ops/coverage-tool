import streamlit as st

st.set_page_config(page_title="Admin - Coverage Tool", page_icon="🔐", layout="centered")
st.title("Admin Settings")

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown("### Enter admin password")
    pw = st.text_input("Password", type="password", placeholder="Type your password here")
    if st.button("Login", type="primary"):
        try:
            correct = st.secrets["ADMIN_PASSWORD"]
        except Exception:
            correct = ""
        if correct == "":
            st.error("ADMIN_PASSWORD is not set in Streamlit Secrets yet.")
            st.info("Go to Streamlit Cloud → your app → three dots menu → Settings → Secrets → add ADMIN_PASSWORD = your password → Save.")
        elif pw == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong password. Try again.")
    st.stop()

st.success("Authenticated as Admin")
st.markdown("---")

st.subheader("API Key Status")
keys = {
    "GOOGLE_MAPS_API_KEY": "Google Maps API key (Geocoding + Places)",
    "ANTHROPIC_API_KEY":   "Anthropic API key (optional)",
    "ADMIN_PASSWORD":      "Admin password",
}
for key, label in keys.items():
    try:
        val = st.secrets[key]
        masked = val[:4] + "..." + val[-4:] if len(val) > 8 else "****"
        st.success(f"{label} — {masked}")
    except Exception:
        st.error(f"{label} — NOT SET")

st.markdown("---")
st.subheader("How to add or update API keys")
st.markdown("""
1. Go to share.streamlit.io
2. Find your app and click the three dots menu
3. Click Settings then Secrets
4. Paste this block with your real values:

```
ADMIN_PASSWORD      = "your-password-here"
GOOGLE_MAPS_API_KEY = "AIza..."
ANTHROPIC_API_KEY   = "sk-ant-..."
```

5. Click Save. The app restarts automatically in about 30 seconds.
""")

st.markdown("---")
st.subheader("How to get a Google Maps API key")
st.markdown("""
1. Go to console.cloud.google.com
2. Create a new project called Coverage Tool
3. Go to APIs and Services then Library
4. Enable the Geocoding API and the Places API
5. Go to Credentials then Create Credentials then API Key
6. Copy the key and paste it into Streamlit Secrets as GOOGLE_MAPS_API_KEY
""")

st.markdown("---")
st.subheader("Per-market API keys (optional)")
st.markdown("""
If different markets use different Google billing accounts add separate keys like this:

```
GOOGLE_MAPS_API_KEY_UAE = "AIza..."
GOOGLE_MAPS_API_KEY_KSA = "AIza..."
GOOGLE_MAPS_API_KEY_UK  = "AIza..."
```

The pipeline will use the market key if available, otherwise falls back to the global key.
""")

st.markdown("---")
if st.button("Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
