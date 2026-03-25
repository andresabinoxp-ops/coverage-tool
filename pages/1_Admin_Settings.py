import streamlit as st

st.set_page_config(page_title="Admin - Coverage Tool", page_icon="🔐", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1B4F9B; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.page-header {
    background: linear-gradient(135deg, #1B4F9B 0%, #2563C0 100%);
    padding: 28px 36px; border-radius: 12px; margin-bottom: 28px;
}
.page-header h1 { color: white !important; font-size: 1.8rem !important; font-weight: 700 !important; margin: 0 0 4px 0 !important; }
.page-header p  { color: rgba(255,255,255,0.85) !important; font-size: 0.95rem !important; margin: 0 !important; }
.section-card {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 24px 28px; margin-bottom: 20px;
}
.section-card h3 { color: #1B4F9B; font-size: 1rem; font-weight: 700; margin: 0 0 16px 0; text-transform: uppercase; letter-spacing: 0.05em; }
.key-status-ok  { background: #F0FFF4; border: 1px solid #9AE6B4; color: #276749; padding: 10px 16px; border-radius: 6px; margin-bottom: 8px; font-size: 0.9rem; }
.key-status-err { background: #FFF5F5; border: 1px solid #FC8181; color: #C53030; padding: 10px 16px; border-radius: 6px; margin-bottom: 8px; font-size: 0.9rem; }
hr { border: none; border-top: 1px solid #E2E8F0; margin: 20px 0; }
div.stButton > button {
    border-radius: 6px; font-weight: 600; font-size: 0.9rem;
    border: 2px solid #1B4F9B; background: #1B4F9B; color: white;
    padding: 8px 24px; transition: all 0.2s;
}
div.stButton > button:hover { background: #2563C0; border-color: #2563C0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>🔐 Admin Settings</h1>
    <p>Manage API keys and global configuration</p>
</div>
""", unsafe_allow_html=True)

# ── Password gate ─────────────────────────────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown('<div class="section-card"><h3>Admin Login</h3>', unsafe_allow_html=True)
    pw = st.text_input("Admin password", type="password", placeholder="Enter admin password")
    if st.button("Login"):
        try:
            correct = st.secrets["ADMIN_PASSWORD"]
        except Exception:
            correct = ""
        if correct == "":
            st.error("ADMIN_PASSWORD not set in Streamlit Secrets yet.")
            st.info("Go to Streamlit Cloud → your app → ⋮ menu → Settings → Secrets → add ADMIN_PASSWORD = your password → Save.")
        elif pw == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong password. Try again.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.success("✅ Authenticated as Admin")
st.markdown("---")

# ── SECTION 1: API KEY STATUS ─────────────────────────────────────────────────
st.markdown('<div class="section-card"><h3>🔑 API Key Status</h3>', unsafe_allow_html=True)

keys = {
    "GOOGLE_MAPS_API_KEY": "Google Maps API key (Geocoding + Places)",
    "ANTHROPIC_API_KEY":   "Anthropic API key (optional)",
    "ADMIN_PASSWORD":      "Admin password",
}
for key, label in keys.items():
    try:
        val = st.secrets[key]
        masked = val[:4] + "•" * max(0, len(val)-8) + val[-4:] if len(val) > 8 else "••••"
        st.markdown(f'<div class="key-status-ok">✅ <strong>{label}</strong> — <code>{masked}</code></div>', unsafe_allow_html=True)
    except Exception:
        st.markdown(f'<div class="key-status-err">❌ <strong>{label}</strong> — NOT SET</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── SECTION 2: PASTE API KEY IN FRONTEND ─────────────────────────────────────
st.markdown('<div class="section-card"><h3>🔧 Update Global Google API Key</h3>', unsafe_allow_html=True)

st.markdown("""
You can paste a new Google Maps API key here. This saves it to your **browser session** for immediate use.
To make it permanent for all users, copy it into **Streamlit Cloud Secrets** using the instructions below.
""")

new_api_key = st.text_input(
    "Paste new Google Maps API key",
    type="password",
    placeholder="AIza...",
    key="admin_new_api_key"
)

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("Apply key for this session"):
        if new_api_key.strip():
            st.session_state["session_api_key"] = new_api_key.strip()
            st.success("Key applied for this session. Market users can now run the pipeline.")
        else:
            st.warning("Paste a valid API key first.")

with col2:
    if st.session_state.get("session_api_key"):
        k = st.session_state["session_api_key"]
        masked = k[:4] + "•" * max(0, len(k)-8) + k[-4:]
        st.info(f"Session key active: `{masked}`")

st.markdown('</div>', unsafe_allow_html=True)

# ── SECTION 3: HOW TO SET PERMANENT SECRETS ──────────────────────────────────
st.markdown('<div class="section-card"><h3>📋 How to Set Permanent API Keys</h3>', unsafe_allow_html=True)

st.markdown("""
To make API keys permanent for all users (recommended):

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Find your app → click **⋮ three dots** → **Settings**
3. Click **Secrets** in the left panel
4. Paste this block with your real values:

```
ADMIN_PASSWORD      = "your-password-here"
GOOGLE_MAPS_API_KEY = "AIza..."
ANTHROPIC_API_KEY   = "sk-ant-..."
```

5. Click **Save** — app restarts in about 30 seconds

Once saved, the key works for everyone automatically. No one sees the actual key value.
""")

st.markdown('</div>', unsafe_allow_html=True)

# ── SECTION 4: GOOGLE API SETUP ───────────────────────────────────────────────
st.markdown('<div class="section-card"><h3>🌐 How to Get a Google Maps API Key</h3>', unsafe_allow_html=True)

st.markdown("""
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create or select a project
3. Go to **APIs and Services → Library**
4. Enable the **Geocoding API** — used for country and city search
5. Enable the **Places API** — used for scraping the store universe
6. Go to **Credentials → Create Credentials → API Key**
7. Copy the key and paste it above or into Streamlit Secrets

Both APIs must be enabled on the same key. Billing must be attached to the project.
""")

st.markdown('</div>', unsafe_allow_html=True)

# ── SECTION 5: MARKET API KEYS ────────────────────────────────────────────────
st.markdown('<div class="section-card"><h3>🌍 Market-Level API Keys</h3>', unsafe_allow_html=True)

st.markdown("""
Each market can use their own Google API key instead of the global one.

**Two ways a market can provide their own key:**

**Option 1 — In the Configure page:** Market users see an optional field to paste their own key.
It stays in their browser session only and is used just for their pipeline run.

**Option 2 — In Streamlit Secrets:** You can add market-specific keys permanently:

```
GOOGLE_MAPS_API_KEY_OMAN   = "AIza..."
GOOGLE_MAPS_API_KEY_KSA    = "AIza..."
GOOGLE_MAPS_API_KEY_NIGERIA = "AIza..."
```

The pipeline checks for a market-specific key first, then falls back to the global key.

**Priority order:**
1. Market user's own key (pasted in Configure)
2. Market-specific key in Secrets
3. Global key in Secrets
""")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
if st.button("🔒 Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
