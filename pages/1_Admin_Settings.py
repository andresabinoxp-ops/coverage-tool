import streamlit as st
import requests

st.set_page_config(page_title="Admin - Coverage Tool", page_icon="🔐", layout="wide")

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
    border-bottom: 2px solid #1565C0; padding-bottom: 0.4rem; margin: 1.5rem 0 0.3rem;
}
.section-desc {
    font-size: 0.83rem; color: #6B7280; margin-bottom: 1rem; line-height: 1.5;
}
.pipeline-tag {
    display: inline-block; background: #E3F2FD; color: #1565C0;
    border-radius: 4px; padding: 1px 7px; font-size: 0.72rem;
    font-weight: 600; margin-left: 8px;
}
.key-card {
    background: #F0F4F8; border: 1px solid #D0DCF0; border-radius: 8px;
    padding: 0.8rem 1.2rem; margin-bottom: 0.5rem;
    display: flex; justify-content: space-between; align-items: center;
}
.key-label { font-weight: 600; color: #1A2B4A; font-size: 0.88rem; }
.key-set   { color: #2E7D32; font-size: 0.83rem; font-weight: 600; }
.key-unset { color: #C62828; font-size: 0.83rem; font-weight: 600; }
.api-ok  { background:#E8F5E9; border:1px solid #A5D6A7; border-left:4px solid #2E7D32; border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:0.5rem; }
.api-err { background:#FFF5F5; border:1px solid #FFCDD2; border-left:4px solid #C62828; border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:0.5rem; }
.api-warn{ background:#FFF8E1; border:1px solid #FFE082; border-left:4px solid #F57F17; border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:0.5rem; }
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
    <p>Configure global defaults for all markets — changes here apply to every new pipeline run</p>
</div>
""", unsafe_allow_html=True)

# ── PASSWORD GATE ─────────────────────────────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    st.markdown("### Admin login")
    st.caption("This page is for administrators only. Market users do not need to access it.")
    pw = st.text_input("Password", type="password", placeholder="Enter admin password")
    if st.button("Login", type="primary"):
        try:
            correct = st.secrets.get("ADMIN_PASSWORD", "")
        except Exception:
            correct = ""
        if not correct:
            st.error("ADMIN_PASSWORD not set in Streamlit Secrets yet.")
            st.info("Streamlit Cloud → your app → ⋮ → Settings → Secrets → add: ADMIN_PASSWORD = \"your-password\" → Save.")
        elif pw == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

st.success("✅ Authenticated as Admin")
st.caption("Changes made here set the global defaults inherited by all markets.")

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_api_key():
    if st.session_state.get("session_api_key"):
        return st.session_state["session_api_key"]
    try:
        k = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        return k if k else None
    except Exception:
        return None

def sec(number, title, desc, stage=""):
    tag = f'<span class="pipeline-tag">Pipeline: {stage}</span>' if stage else ""
    st.markdown(
        f'<div class="section-title">Section {number} — {title} {tag}</div>'
        f'<div class="section-desc">{desc}</div>',
        unsafe_allow_html=True)

def api_card(name, status, msg, fix=""):
    css   = {"ok":"api-ok","error":"api-err","warn":"api-warn"}
    icons = {"ok":"✅","error":"❌","warn":"⚠️"}
    colors= {"ok":"#1B5E20","error":"#B71C1C","warn":"#E65100"}
    fix_html = (f'<div style="background:#E3F2FD;border-radius:5px;padding:5px 10px;'
                f'margin-top:5px;font-size:0.8rem;color:#0D47A1">🔧 {fix}</div>') if fix and status!="ok" else ""
    st.markdown(
        f'<div class="{css.get(status,"api-warn")}">'
        f'<span style="font-weight:700;color:{colors.get(status,"#555")}">'
        f'{icons.get(status,"⚠️")} {name}</span>'
        f'<span style="font-size:0.82rem;color:{colors.get(status,"#555")};margin-left:8px">{msg}</span>'
        f'{fix_html}</div>',
        unsafe_allow_html=True)

def test_api(url, params):
    try:
        r = requests.get(url, params=params, timeout=8)
        return r.json()
    except Exception as e:
        return {"status":"ERROR","error_message":str(e)}

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — API CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("1", "API Configuration",
    "Set the Google Maps API key used by the pipeline. Required for all stages: location search in Configure, geocoding portfolio stores, scraping the store universe and enrichment (phone, opening hours, POI).",
    "All stages")

# Key status
st.markdown("**Current key status:**")
for sk, label in [("GOOGLE_MAPS_API_KEY","Google Maps API key"),("ADMIN_PASSWORD","Admin password")]:
    try:
        val = st.secrets.get(sk,"")
        if val:
            m = val[:4]+"••••••••"+val[-4:] if len(val)>8 else "••••••••"
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-set">✅ Set — {m}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">❌ Not set</span></div>', unsafe_allow_html=True)
    except Exception:
        st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">❌ Not set</span></div>', unsafe_allow_html=True)

if st.session_state.get("session_api_key"):
    k = st.session_state["session_api_key"]
    m = k[:4]+"••••••••"+k[-4:]
    st.markdown(f'<div class="key-card"><span class="key-label">Session key (this session only)</span><span class="key-set">✅ Active — {m}</span></div>', unsafe_allow_html=True)

st.markdown("**Paste a new API key (saves for this session):**")
st.caption("To make it permanent, update GOOGLE_MAPS_API_KEY in Streamlit Secrets using the guide below.")
new_key = st.text_input("Google Maps API key", type="password", placeholder="AIza...", key="new_key_input")
c1, c2 = st.columns([2,1])
with c1:
    if st.button("Save for this session", type="primary", key="save_key_btn"):
        if new_key.startswith("AIza"):
            st.session_state["session_api_key"] = new_key
            st.success("Key saved for this session.")
            st.rerun()
        else:
            st.error("Invalid key — Google Maps keys start with AIza.")
with c2:
    if st.session_state.get("session_api_key"):
        if st.button("Clear session key", key="clear_key_btn"):
            st.session_state["session_api_key"] = None
            st.rerun()

st.markdown("**Live API health check:**")
st.caption("Makes one real test call to each Google API. Run this after setting a new key or enabling an API in Google Cloud Console.")
api_key = get_api_key()
if not api_key:
    st.warning("No API key set. Paste a key above or set GOOGLE_MAPS_API_KEY in Streamlit Secrets.")
else:
    if st.button("🔍 Run health check", type="primary", key="health_btn"):
        results = {}
        with st.spinner("Checking..."):
            d = test_api("https://maps.googleapis.com/maps/api/geocode/json", {"address":"Dubai, UAE","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Geocoding API"] = ("ok","Active — address lookup working") if s=="OK" else \
                ("error", d.get("error_message","Not enabled or key invalid")) if s=="REQUEST_DENIED" else ("warn", f"Status: {s}")

            d = test_api("https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                {"location":"25.2048,55.2708","radius":"500","type":"supermarket","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Places API"] = ("ok", f"Active — {len(d.get('results',[]))} results in test") if s in ("OK","ZERO_RESULTS") else \
                ("error", d.get("error_message","Not enabled or key invalid")) if s=="REQUEST_DENIED" else ("warn", f"Status: {s}")

            d = test_api("https://maps.googleapis.com/maps/api/place/details/json",
                {"place_id":"ChIJRcbZaklDXz4RYlEphFBu5r0","fields":"name","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Place Details API"] = ("ok","Active — details lookup working") if s=="OK" else \
                ("error", d.get("error_message","Not enabled or key invalid")) if s=="REQUEST_DENIED" else ("warn", f"Status: {s}")

        st.session_state["api_health_cache"] = results

    if "api_health_cache" in st.session_state:
        for name,(status,msg) in st.session_state["api_health_cache"].items():
            fix = "" if status=="ok" else "Enable in Google Cloud Console → APIs & Services → Library → search '" + name.replace(" API","") + "' → Enable."
            api_card(name, status, msg, fix)
        if all(s=="ok" for s,_ in st.session_state["api_health_cache"].values()):
            st.success("✅ All APIs active — pipeline ready to run")
        else:
            st.error("One or more APIs need to be enabled. See fix instructions above.")
    else:
        st.info("Click Run health check to verify all APIs are active.")

with st.expander("How to set permanent Secrets + how to get a Google API key"):
    st.markdown("""
**Set permanent secrets in Streamlit Cloud:**
1. Go to [share.streamlit.io](https://share.streamlit.io) → your app → ⋮ → Settings → Secrets
2. Paste: `ADMIN_PASSWORD = "your-password"` and `GOOGLE_MAPS_API_KEY = "AIza..."`
3. Save — app restarts in ~30 seconds

**Get a Google Maps API key:**
1. [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials → Create API Key
2. Enable: **Geocoding API** and **Places API** (Library → search each → Enable)
3. Link a billing account (required — but first $200/month is free, covers most runs)

**Per-market key priority:** Market key in Configure → Session key here → Secrets key
    """)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SCORING MODEL DEFAULTS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("2", "Scoring Model Defaults",
    "Set the default weights for the store scoring formula. Every store gets a score 0-100 from these six signals combined. Weights must sum to 100%. Gap stores (not in your portfolio) score 0 on Sales and Lines — their potential is what the model identifies as opportunity.",
    "Stage 3 — Scoring")

saved_w = st.session_state.get("admin_scoring_weights", {
    "rating":20,"reviews":25,"affluence":15,"poi":15,"sales":15,"lines":10
})

c1, c2 = st.columns(2)
with c1:
    w_rating    = st.slider("⭐ Rating — Google star rating (0–5 stars)",
        0,50,saved_w.get("rating",20),
        help="Normalised: rating/5. A 4.5-star store = 0.90.")
    w_reviews   = st.slider("👥 Reviews — volume of Google reviews (footfall proxy)",
        0,50,saved_w.get("reviews",25),
        help="Log-normalised within market. Prevents one mega-store dominating.")
    w_affluence = st.slider("💰 Affluence — Google price level (1=budget to 4=luxury)",
        0,50,saved_w.get("affluence",15),
        help="Normalised: price_level/4. Unknown = 0.5 neutral. Premium stores score higher.")
with c2:
    w_poi       = st.slider("📍 Nearby POI — points of interest within radius",
        0,50,saved_w.get("poi",15),
        help="Log-normalised POI count. Stores near offices, schools, transport score higher. Requires POI enrichment.")
    w_sales     = st.slider("💵 Current sales — your revenue at this store",
        0,50,saved_w.get("sales",15),
        help="Normalised: store_sales/max_sales. Zero for gap stores.")
    w_lines     = st.slider("📦 Lines per store — SKU count you sell there",
        0,50,saved_w.get("lines",10),
        help="Normalised: store_lines/max_lines. Zero for gap stores.")

w_total = w_rating + w_reviews + w_affluence + w_poi + w_sales + w_lines
if w_total == 100:
    st.success(f"Total: {w_total}% — valid ✓")
else:
    st.error(f"Total: {w_total}% — must equal exactly 100%")

if w_total == 100:
    if st.button("Save scoring weights", type="primary", key="save_weights"):
        st.session_state["admin_scoring_weights"] = {
            "rating":w_rating,"reviews":w_reviews,"affluence":w_affluence,
            "poi":w_poi,"sales":w_sales,"lines":w_lines
        }
        st.success("✅ Scoring weights saved — all new pipeline runs will use these defaults.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — STORE SIZE & VISIT BENCHMARKS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("3", "Store Size & Visit Benchmarks",
    "Define how stores are classified into Large, Medium and Small tiers by score percentile within each category. Pharmacies are ranked against pharmacies, supermarkets against supermarkets. Visit frequency and duration are then assigned by tier.",
    "Stage 5 — Frequency")

st.caption("Markets inherit these defaults and can override per-category in their Configure page.")

saved_splits = st.session_state.get("admin_size_splits",{"large":20,"medium":60,"small":20})
st.markdown("**Percentile splits — must sum to 100%:**")
c1, c2, c3 = st.columns(3)
with c1:
    pct_large  = st.number_input("Large — top %",    min_value=5,max_value=50,step=5,value=saved_splits.get("large",20))
    st.caption("Highest-scoring stores per category")
with c2:
    pct_medium = st.number_input("Medium — middle %",min_value=20,max_value=80,step=5,value=saved_splits.get("medium",60))
    st.caption("Mid-range stores")
with c3:
    pct_small  = st.number_input("Small — bottom %", min_value=5,max_value=50,step=5,value=saved_splits.get("small",20))
    st.caption("Lower-scoring stores")

split_total = pct_large + pct_medium + pct_small
if split_total == 100:
    st.success(f"Total: {split_total}% — valid ✓")
else:
    st.error(f"Total: {split_total}% — must equal 100%")

saved_bench = st.session_state.get("admin_visit_benchmarks",{
    "large": {"visits_month":4,"duration_min":45},
    "medium":{"visits_month":2,"duration_min":30},
    "small": {"visits_month":1,"duration_min":15},
})

st.markdown("**Default visit benchmarks per tier:**")
st.caption("These are the starting point — markets can override per category in Configure.")
new_bench = {}
bc1, bc2, bc3 = st.columns(3)
for col, tier, label in [(bc1,"large","Large"),(bc2,"medium","Medium"),(bc3,"small","Small")]:
    with col:
        st.markdown(f"**{label}**")
        v = st.number_input(f"Visits per month",min_value=1,max_value=12,
            value=saved_bench[tier]["visits_month"],key=f"v_{tier}")
        d = st.number_input(f"Visit duration (min)",min_value=5,max_value=120,
            value=saved_bench[tier]["duration_min"],key=f"d_{tier}")
        new_bench[tier] = {"visits_month":v,"duration_min":d}
        st.caption(f"{v} visits × {d} min = {v*d} min/month per store")

if split_total == 100:
    if st.button("Save size & visit benchmarks", type="primary", key="save_bench"):
        st.session_state["admin_size_splits"]      = {"large":pct_large,"medium":pct_medium,"small":pct_small}
        st.session_state["admin_visit_benchmarks"] = new_bench
        st.success("✅ Size splits and visit benchmarks saved.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — REP PLANNING DEFAULTS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("4", "Rep Planning Defaults",
    "Set the default parameters used to calculate how many reps a market needs and how their daily routes are planned. Used when Recommended mode is selected in Configure.",
    "Stage 6 — Route allocation")

saved_rep = st.session_state.get("admin_rep_defaults",{
    "minutes_per_day":480,"travel_speed_kmh":30,"working_days":22
})

c1, c2, c3 = st.columns(3)
with c1:
    minutes_day = st.number_input("Working minutes per day",
        min_value=240,max_value=600,step=30,value=saved_rep.get("minutes_per_day",480),
        help="Total productive time per rep per day. 480 = 8 hours.")
    st.caption(f"{minutes_day} min = {minutes_day//60}h {minutes_day%60}min")
with c2:
    travel_speed = st.number_input("Average travel speed (km/h)",
        min_value=10,max_value=80,step=5,value=saved_rep.get("travel_speed_kmh",30),
        help="Used for straight-line travel time between stores. 30 km/h suits dense city. Increase for rural markets.")
    st.caption("Travel time = straight-line distance ÷ speed")
with c3:
    working_days = st.number_input("Working days per month",
        min_value=15,max_value=26,step=1,value=saved_rep.get("working_days",22),
        help="Selling days per month after weekends and holidays.")
    st.caption(f"Total capacity: {minutes_day*working_days:,} min/rep/month")

st.caption(
    f"Rep count formula: Total time needed ÷ ({minutes_day} min/day × {working_days} days) = reps needed (rounded up)"
)

if st.button("Save rep planning defaults", type="primary", key="save_rep"):
    st.session_state["admin_rep_defaults"] = {
        "minutes_per_day":minutes_day,"travel_speed_kmh":travel_speed,"working_days":working_days
    }
    st.success("✅ Rep planning defaults saved.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DASHBOARD MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("5", "Dashboard Management",
    "Upload market snapshot files generated after pipeline runs. Once uploaded, all users can view results in the Dashboard page without needing to re-run the pipeline or have an API key.",
    "Dashboard page")

st.caption("""
After every pipeline run two CSV files are generated: a stores file and a summary file.
Upload both here. Markets can then open the Dashboard page to view, filter and download results.
""")

if "dashboard_snapshots" not in st.session_state:
    st.session_state["dashboard_snapshots"] = []

st.markdown("**Upload new market snapshot:**")
c1, c2 = st.columns(2)
with c1:
    stores_file  = st.file_uploader("Stores CSV",  type=["csv"], key="up_stores",
        help="The stores output file from the pipeline run")
with c2:
    summary_file = st.file_uploader("Summary CSV", type=["csv"], key="up_summary",
        help="The summary output file from the pipeline run")

if stores_file and summary_file:
    import pandas as pd
    import datetime
    try:
        stores_df  = pd.read_csv(stores_file)
        summary_df = pd.read_csv(summary_file)

        fname  = stores_file.name.replace(".csv","")
        parts  = fname.split("_")
        c1, c2, c3 = st.columns(3)
        with c1:
            snap_market = st.text_input("Market name", value=parts[0] if parts else "", key="snap_mkt")
        with c2:
            snap_cat    = st.text_input("Category",    value=parts[1] if len(parts)>1 else "", key="snap_cat")
        with c3:
            snap_date   = st.date_input("Run date", value=datetime.date.today(), key="snap_date")

        gap_count = len(stores_df[stores_df["coverage_status"]=="gap"]) if "coverage_status" in stores_df.columns else 0
        st.success(f"Files loaded — {len(stores_df):,} stores · {gap_count:,} gaps")

        if st.button("Add to dashboard library", type="primary", key="add_snap"):
            st.session_state["dashboard_snapshots"].append({
                "market":      snap_market,
                "category":    snap_cat,
                "run_date":    str(snap_date),
                "store_count": len(stores_df),
                "gap_count":   gap_count,
                "stores_df":   stores_df,
                "summary_df":  summary_df,
            })
            st.success(f"✅ {snap_market} — {snap_cat} ({snap_date}) added to dashboard.")
            st.rerun()
    except Exception as e:
        st.error(f"Error reading files: {e}")

snapshots = st.session_state.get("dashboard_snapshots", [])
if snapshots:
    st.markdown("**Market library:**")
    for i, snap in enumerate(snapshots):
        ca, cb, cc, cd, ce = st.columns([2,1,1,1,1])
        ca.write(f"**{snap['market']}** — {snap['category']}")
        cb.write(snap["run_date"])
        cc.write(f"{snap['store_count']:,} stores")
        cd.write(f"{snap['gap_count']:,} gaps")
        if ce.button("🗑 Remove", key=f"del_{i}"):
            st.session_state["dashboard_snapshots"].pop(i)
            st.rerun()
else:
    st.info("No snapshots uploaded yet. Run a pipeline and upload the two output CSV files here.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — APP ACCESS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sec("6", "App Access",
    "Manage admin session and password. The admin password is stored in Streamlit Secrets — see the guide below to change it.",
    "")

with st.expander("How to change the admin password"):
    st.markdown("""
1. Go to [share.streamlit.io](https://share.streamlit.io) → your app → ⋮ → Settings → Secrets
2. Update: `ADMIN_PASSWORD = "new-password-here"`
3. Save — takes effect in ~30 seconds.
    """)

st.markdown("---")
if st.button("🔒 Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
