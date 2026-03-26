import streamlit as st
import requests

st.set_page_config(page_title="Admin - Coverage Tool", page_icon="🔐", layout="centered")

st.markdown("""
<style>
.page-header {
    background: linear-gradient(135deg, #1A2B4A 0%, #1565C0 100%);
    padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; color: white;
}
.page-header h2 { color: white !important; margin: 0 !important; font-size: 1.6rem !important; }
.page-header p  { color: rgba(255,255,255,0.75); margin: 0.3rem 0 0; font-size: 0.9rem; }
.section-title {
    font-size: 1rem; font-weight: 700; color: #1A2B4A;
    border-bottom: 2px solid #1565C0; padding-bottom: 0.4rem; margin: 1.5rem 0 1rem;
}
.api-check-ok {
    background: #E8F5E9; border: 1px solid #A5D6A7; border-left: 4px solid #2E7D32;
    border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 0.6rem;
}
.api-check-err {
    background: #FFF5F5; border: 1px solid #FFCDD2; border-left: 4px solid #C62828;
    border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 0.6rem;
}
.api-check-warn {
    background: #FFF8E1; border: 1px solid #FFE082; border-left: 4px solid #F57F17;
    border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 0.6rem;
}
.api-name  { font-weight: 700; font-size: 0.9rem; }
.api-ok    { color: #1B5E20; }
.api-err   { color: #B71C1C; }
.api-warn  { color: #E65100; }
.api-detail { font-size: 0.82rem; margin-top: 4px; }
.api-ok .api-detail   { color: #2E7D32; }
.api-err .api-detail  { color: #C62828; }
.api-warn .api-detail { color: #E65100; }
.fix-box {
    background: #E3F2FD; border: 1px solid #90CAF9; border-radius: 6px;
    padding: 0.6rem 1rem; margin-top: 8px; font-size: 0.82rem; color: #0D47A1;
}
.key-card {
    background: #F0F4F8; border: 1px solid #D0DCF0;
    border-radius: 8px; padding: 0.9rem 1.2rem; margin-bottom: 0.6rem;
    display: flex; justify-content: space-between; align-items: center;
}
.key-label { font-weight: 600; color: #1A2B4A; font-size: 0.9rem; }
.key-set   { color: #2E7D32; font-size: 0.85rem; font-weight: 600; }
.key-unset { color: #C62828; font-size: 0.85rem; font-weight: 600; }
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white;
    border-radius: 6px; font-weight: 600;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>🔐 Admin Settings</h2>
    <p>Manage API keys, run health checks and configure global defaults</p>
</div>
""", unsafe_allow_html=True)

# ── Password gate ─────────────────────────────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown("### Admin login")
    pw = st.text_input("Password", type="password", placeholder="Enter admin password")
    if st.button("Login", type="primary"):
        try:
            correct = st.secrets.get("ADMIN_PASSWORD", "")
        except Exception:
            correct = ""
        if not correct:
            st.error("ADMIN_PASSWORD not set in Streamlit Secrets yet.")
            st.info("Go to Streamlit Cloud → your app → ⋮ menu → Settings → Secrets → add ADMIN_PASSWORD = your password → Save.")
        elif pw == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

st.success("✅ Authenticated as Admin")

# ── API health check function ─────────────────────────────────────────────────
def get_api_key():
    if st.session_state.get("session_api_key"):
        return st.session_state["session_api_key"]
    try:
        k = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        return k if k else None
    except Exception:
        return None

API_ERRORS = {
    "REQUEST_DENIED":        ("API not enabled or key invalid", "This API is not enabled for your key. Enable it in Google Cloud Console → APIs & Services → Library."),
    "INVALID_REQUEST":       ("Invalid request — key may be malformed", "Check your API key is copied correctly with no extra spaces."),
    "OVER_DAILY_LIMIT":      ("Daily quota exceeded", "Your Google Cloud billing quota has been reached. Check Google Cloud Console → APIs & Services → Quotas."),
    "OVER_QUERY_LIMIT":      ("Rate limit hit", "Too many requests. This will resolve automatically — try again in a few minutes."),
    "ZERO_RESULTS":          ("OK — no results for test location", "API is working correctly. Zero results just means no stores at the test coordinates."),
    "OK":                    ("Active and working", ""),
}

def check_geocoding_api(api_key):
    """Test Geocoding API with a known address."""
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": "Dubai, UAE", "key": api_key},
            timeout=8
        )
        data = r.json()
        status = data.get("status", "UNKNOWN")
        if status == "OK":
            return "ok", "Active — geocoded 'Dubai, UAE' successfully"
        elif status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "")
            return "error", f"Request denied — {error_msg or 'API not enabled or key invalid'}"
        elif status in API_ERRORS:
            label, fix = API_ERRORS[status]
            return "warn", label
        else:
            return "error", f"Unexpected status: {status}"
    except requests.exceptions.Timeout:
        return "warn", "Request timed out — check your internet connection"
    except Exception as e:
        return "error", f"Connection error: {str(e)}"

def check_places_api(api_key):
    """Test Places Nearby Search API with a known location."""
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={"location": "25.2048,55.2708", "radius": "500",
                    "type": "supermarket", "key": api_key},
            timeout=8
        )
        data = r.json()
        status = data.get("status", "UNKNOWN")
        if status in ("OK", "ZERO_RESULTS"):
            count = len(data.get("results", []))
            return "ok", f"Active — found {count} stores near Dubai test location"
        elif status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "")
            return "error", f"Request denied — {error_msg or 'Places API not enabled or key invalid'}"
        elif status in API_ERRORS:
            label, _ = API_ERRORS[status]
            return "warn", label
        else:
            return "error", f"Unexpected status: {status}"
    except requests.exceptions.Timeout:
        return "warn", "Request timed out"
    except Exception as e:
        return "error", f"Connection error: {str(e)}"

def check_place_details_api(api_key):
    """Test Place Details API with a known place_id."""
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={"place_id": "ChIJRcbZaklDXz4RYlEphFBu5r0",  # Dubai Mall
                    "fields": "name,formatted_phone_number",
                    "key": api_key},
            timeout=8
        )
        data = r.json()
        status = data.get("status", "UNKNOWN")
        if status == "OK":
            name = data.get("result", {}).get("name", "unknown")
            return "ok", f"Active — retrieved details for '{name}'"
        elif status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "")
            return "error", f"Request denied — {error_msg or 'Place Details API not enabled or key invalid'}"
        elif status in API_ERRORS:
            label, _ = API_ERRORS[status]
            return "warn", label
        else:
            return "error", f"Unexpected status: {status}"
    except requests.exceptions.Timeout:
        return "warn", "Request timed out"
    except Exception as e:
        return "error", f"Connection error: {str(e)}"

def render_api_status(name, status, message, fix_instructions=""):
    if status == "ok":
        st.markdown(f"""
        <div class="api-check-ok">
            <div class="api-name api-ok">✅ {name}</div>
            <div class="api-detail">{message}</div>
        </div>""", unsafe_allow_html=True)
    elif status == "error":
        st.markdown(f"""
        <div class="api-check-err">
            <div class="api-name api-err">❌ {name}</div>
            <div class="api-detail">{message}</div>
            {f'<div class="fix-box">🔧 How to fix: {fix_instructions}</div>' if fix_instructions else ''}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="api-check-warn">
            <div class="api-name api-warn">⚠️ {name}</div>
            <div class="api-detail">{message}</div>
            {f'<div class="fix-box">🔧 {fix_instructions}</div>' if fix_instructions else ''}
        </div>""", unsafe_allow_html=True)

# ── API KEY STATUS ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">API Key Status</div>', unsafe_allow_html=True)

keys = {
    "GOOGLE_MAPS_API_KEY": "Google Maps API key (Geocoding + Places + Details)",
    "ANTHROPIC_API_KEY":   "Anthropic API key (optional)",
    "ADMIN_PASSWORD":      "Admin password",
}
for key, label in keys.items():
    try:
        val = st.secrets.get(key, "")
        if val:
            masked = val[:4] + "••••••••" + val[-4:] if len(val) > 8 else "••••••••"
            st.markdown(f"""
            <div class="key-card">
                <span class="key-label">{label}</span>
                <span class="key-set">✅ Set — {masked}</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="key-card">
                <span class="key-label">{label}</span>
                <span class="key-unset">❌ Not set</span>
            </div>""", unsafe_allow_html=True)
    except Exception:
        st.markdown(f"""
        <div class="key-card">
            <span class="key-label">{label}</span>
            <span class="key-unset">❌ Not set</span>
        </div>""", unsafe_allow_html=True)

# ── LIVE API HEALTH CHECK ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Live API Health Check</div>', unsafe_allow_html=True)
st.caption("Tests each Google API with a real call to confirm it is enabled and working.")

api_key = get_api_key()

if not api_key:
    st.error("❌ No Google Maps API key found. Set it in Streamlit Secrets or paste it below.")
else:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("Click the button to run a live test of all three Google APIs. Each test makes one small API call.")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_check = st.button("🔍 Run API health check", type="primary")

    if run_check:
        geocode_fix = "Go to console.cloud.google.com → APIs & Services → Library → search 'Geocoding API' → Enable."
        places_fix  = "Go to console.cloud.google.com → APIs & Services → Library → search 'Places API' → Enable."
        details_fix = "Go to console.cloud.google.com → APIs & Services → Library → search 'Places API' → Enable. (Place Details uses the same Places API.)"
        billing_fix = "Make sure a billing account is linked to your Google Cloud project. Go to console.cloud.google.com → Billing."

        with st.spinner("Testing Geocoding API..."):
            geo_status, geo_msg = check_geocoding_api(api_key)
        render_api_status(
            "Geocoding API — converts addresses to GPS coordinates",
            geo_status, geo_msg,
            geocode_fix if geo_status == "error" else billing_fix if geo_status == "warn" else ""
        )

        with st.spinner("Testing Places API..."):
            places_status, places_msg = check_places_api(api_key)
        render_api_status(
            "Places API — scrapes store universe from Google Maps",
            places_status, places_msg,
            places_fix if places_status == "error" else billing_fix if places_status == "warn" else ""
        )

        with st.spinner("Testing Place Details API..."):
            details_status, details_msg = check_place_details_api(api_key)
        render_api_status(
            "Place Details API — fetches phone numbers and opening hours",
            details_status, details_msg,
            details_fix if details_status == "error" else ""
        )

        all_ok = all(s == "ok" for s in [geo_status, places_status, details_status])
        if all_ok:
            st.success("✅ All APIs are active and working. The Coverage Tool is ready to run.")
        else:
            failed = [n for n, s in [
                ("Geocoding API", geo_status),
                ("Places API", places_status),
                ("Place Details API", details_status)
            ] if s == "error"]
            if failed:
                st.error(f"❌ The following APIs need to be enabled: {', '.join(failed)}. See fix instructions above.")

    # How to enable APIs guide
    with st.expander("How to enable Google APIs — step by step"):
        st.markdown("""
**Step 1 — Open Google Cloud Console**
Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in.

**Step 2 — Select your project**
Make sure you are in the same project where your API key was created.
If you do not have a project yet click New Project and create one called Coverage Tool.

**Step 3 — Enable billing**
Go to Billing in the left menu and confirm a billing account is linked.
Google requires billing even for free tier usage.
Your first $200 per month is free — most market runs cost under $5.

**Step 4 — Enable Geocoding API**
Go to APIs & Services → Library → search Geocoding API → click Enable.

**Step 5 — Enable Places API**
Go to APIs & Services → Library → search Places API → click Enable.
This covers both the Nearby Search (scraping) and Place Details (phone/hours).

**Step 6 — Check your API key restrictions**
Go to APIs & Services → Credentials → click your API key.
Under API restrictions make sure it includes Geocoding API and Places API,
or is set to Unrestricted.

**Step 7 — Come back and run the health check**
Once all APIs are enabled click Run API health check above.
All three should show green within 1-2 minutes of enabling.
        """)

# ── UPDATE GLOBAL API KEY ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Update Global API Key</div>', unsafe_allow_html=True)
st.caption("Paste a new key here to update it for this session. To make it permanent update Streamlit Secrets.")

new_key = st.text_input("New Google Maps API key", type="password", placeholder="AIza...")
if st.button("Save as global key for this session", type="primary"):
    if new_key.startswith("AIza"):
        st.session_state["session_api_key"] = new_key
        st.success("Global API key updated for this session. To make it permanent go to Streamlit Cloud → Settings → Secrets and update GOOGLE_MAPS_API_KEY.")
    else:
        st.error("That does not look like a valid Google API key — it should start with AIza.")

if st.session_state.get("session_api_key"):
    k = st.session_state["session_api_key"]
    masked = k[:4] + "••••••••" + k[-4:]
    st.markdown(f"""
    <div class="key-card">
        <span class="key-label">Session key active</span>
        <span class="key-set">✅ {masked}</span>
    </div>""", unsafe_allow_html=True)
    if st.button("Clear session key"):
        st.session_state["session_api_key"] = None
        st.rerun()

# ── HOW TO SET PERMANENT SECRETS ─────────────────────────────────────────────
with st.expander("How to set permanent secrets in Streamlit Cloud"):
    st.markdown("""
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Find your app → click **⋮ menu** → **Settings** → **Secrets**
3. Paste this block with your real values:

```
ADMIN_PASSWORD      = "your-password-here"
GOOGLE_MAPS_API_KEY = "AIza..."
ANTHROPIC_API_KEY   = "sk-ant-..."
```

4. Click **Save** — app restarts in ~30 seconds.
    """)

# ── PER MARKET KEY INFO ───────────────────────────────────────────────────────
with st.expander("Per-market API keys — how they work"):
    st.markdown("""
Each market user can paste their own Google API key in the Configure page.

**Priority order the pipeline uses:**
1. Market key (pasted in Configure page) — used first
2. Session key (pasted here by admin) — used second
3. Secrets key (set in Streamlit Cloud) — used as fallback

This means each country team can manage their own Google billing
while sharing the same app.
    """)

st.markdown("---")
if st.button("🔒 Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
