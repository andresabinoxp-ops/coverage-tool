import streamlit as st

st.set_page_config(page_title="Admin — Coverage Tool", page_icon="🔐", layout="centered")
st.title("🔐 Admin Settings")

# ── Password gate ─────────────────────────────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown("### Enter admin password")
    st.caption("Contact your system administrator if you do not have the password.")

    pw = st.text_input("Password", type="password", placeholder="Type password and click Login")

    if st.button("🔓 Login", type="primary"):
        try:
            correct = st.secrets["ADMIN_PASSWORD"]
        except Exception:
            correct = ""

        if correct == "":
            st.error("❌ ADMIN_PASSWORD is not set in Streamlit Secrets yet.")
            st.info("Go to Streamlit Cloud → your app → ⋮ menu → Settings → Secrets → add ADMIN_PASSWORD = \"yourpassword\" → Save.")
        elif pw == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Wrong password. Try again.")

    st.stop()

# ── Authenticated ─────────────────────────────────────────────────────────────
st.success("✅ Authenticated as Admin")
st.markdown("---")

# ── API key status ────────────────────────────────────────────────────────────
st.subheader("🔑 API Key Status")

keys = {
    "GOOGLE_MAPS_API_KEY": "Google Maps API key (Geocoding + Places)",
    "ANTHROPIC_API_KEY":   "Anthropic API key (optional)",
    "ADMIN_PASSWORD":      "Admin password",
}

for key, label in keys.items():
    try:
        val = st.secrets[key]
        if len(val) > 8:
            masked = val[:4] + "•" * (len(val) - 8) + val[-4:]
        else:
            masked = "••••"
        st.success(f"✅ **{label}** — `{masked}`")
    except Exception:
        st.error(f"❌ **{label}** — NOT SET")

st.markdown("---")

# ── How to add secrets ────────────────────────────────────────────────────────
st.subheader("📋 How to add or update API keys")

tab1, tab2 = st.tabs(["☁️ Streamlit Cloud", "💻 Local development"])

with tab1:
    st.markdown("""
**Steps:**

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Find your app → click **⋮ (three dots menu)** → **Settings**
3. Click **Secrets** in the left panel
4. Paste this block with your real values:

```
ADMIN_PASSWORD      = "your-password-here"
GOOGLE_MAPS_API_KEY = "AIza..."
ANTHROPIC_API_KEY   = "sk-ant-..."
```

5. Click **Save** — app restarts automatically in ~30 seconds.

> ⚠️ Never put API keys in your GitHub code.
    """)

with tab2:
    st.markdown("""
**Steps:**

1. In your project root create: `.streamlit/secrets.toml`
2. Paste:

```
ADMIN_PASSWORD      = "your-password-here"
GOOGLE_MAPS_API_KEY = "AIza..."
ANTHROPIC_API_KEY   = "sk-ant-..."
```

3. This file is already in `.gitignore` — it will NOT be committed.
4. Run `streamlit run Home.py` as normal.
    """)

st.markdown("---")

# ── Google API setup ──────────────────────────────────────────────────────────
st.subheader("🌐 How to get a Google Maps API key")
st.markdown("""
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project called **Coverage Tool**
3. Go to **APIs & Services → Library**
4. Enable: **Geocoding API** and **Places API**
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key → paste into Streamlit Secrets as `GOOGLE_MAPS_API_KEY`
""")

st.markdown("---")

# ── Per-market keys ───────────────────────────────────────────────────────────
st.subheader("🌍 Per-market API keys (optional)")
st.markdown("""
If each market team has their own Google billing account, add separate keys:

```
GOOGLE_MAPS_API_KEY_UAE = "AIza..."
GOOGLE_MAPS_API_KEY_KSA = "AIza..."
GOOGLE_MAPS_API_KEY_UK  = "AIza..."
```

The pipeline will use the market-specific key if available, otherwise falls back to the global one.
""")

st.markdown("---")

if st.button("🔒 Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
