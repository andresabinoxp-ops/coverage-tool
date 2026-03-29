import streamlit as st
import requests

st.set_page_config(page_title="Admin - Coverage Tool", page_icon="🔐", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.page-header {
    background: linear-gradient(135deg, #1A2B4A 0%, #1565C0 100%);
    padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; color: white;
}
.page-header h2 { color: white !important; margin: 0 !important; font-size: 1.6rem !important; }
.page-header p  { color: rgba(255,255,255,0.75); margin: 0.3rem 0 0; font-size: 0.9rem; }
.section-title {
    font-size: 1rem; font-weight: 700; color: #1A2B4A;
    border-bottom: 2px solid #1565C0; padding-bottom: 0.4rem; margin: 1.8rem 0 0.3rem;
}
.section-desc { font-size: 0.83rem; color: #6B7280; margin-bottom: 1rem; line-height: 1.5; }
.pipeline-tag {
    display: inline-block; background: #E3F2FD; color: #1565C0;
    border-radius: 4px; padding: 1px 7px; font-size: 0.72rem; font-weight: 600; margin-left: 8px;
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
    background: #1565C0; border-color: #1565C0; color: white; border-radius: 6px; font-weight: 600;
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
    css    = {"ok":"api-ok","error":"api-err","warn":"api-warn"}
    icons  = {"ok":"✅","error":"❌","warn":"⚠️"}
    colors = {"ok":"#1B5E20","error":"#B71C1C","warn":"#E65100"}
    fix_html = (f'<div style="background:#E3F2FD;border-radius:5px;padding:5px 10px;'
                f'margin-top:5px;font-size:0.8rem;color:#0D47A1">🔧 {fix}</div>') if fix and status != "ok" else ""
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

# ── SECTION 1: API CONFIGURATION ─────────────────────────────────────────────
st.markdown("---")
sec("1","API Configuration",
    "Set the Google Maps API key used for all pipeline stages: location search, geocoding, "
    "store universe scraping, phone/hours enrichment and POI enrichment.","All stages")

st.markdown("**Current key status:**")
for sk,label in [("GOOGLE_MAPS_API_KEY","Google Maps API key"),("ADMIN_PASSWORD","Admin password")]:
    try:
        val = st.secrets.get(sk,"")
        if val:
            m = val[:4]+"••••••••"+val[-4:] if len(val)>8 else "••••••••"
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-set">✅ Set — {m}</span></div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">❌ Not set</span></div>',unsafe_allow_html=True)
    except Exception:
        st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">❌ Not set</span></div>',unsafe_allow_html=True)

if st.session_state.get("session_api_key"):
    k = st.session_state["session_api_key"]
    m = k[:4]+"••••••••"+k[-4:]
    st.markdown(f'<div class="key-card"><span class="key-label">Session key (this session only)</span><span class="key-set">✅ Active — {m}</span></div>',unsafe_allow_html=True)

st.markdown("**Paste a new API key:**")
st.caption("Saves for this session only. To make it permanent update GOOGLE_MAPS_API_KEY in Streamlit Secrets.")
new_key = st.text_input("Google Maps API key", type="password", placeholder="AIza...", key="new_key_input")
c1,c2 = st.columns([2,1])
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
api_key = get_api_key()
if not api_key:
    st.warning("No API key set. Paste a key above or set GOOGLE_MAPS_API_KEY in Streamlit Secrets.")
else:
    if st.button("🔍 Run health check", type="primary", key="health_btn"):
        with st.spinner("Checking APIs..."):
            results = {}
            d = test_api("https://maps.googleapis.com/maps/api/geocode/json",{"address":"Dubai, UAE","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Geocoding API"] = ("ok","Active") if s=="OK" else \
                ("error",d.get("error_message","Not enabled")) if s=="REQUEST_DENIED" else ("warn",f"Status: {s}")
            d = test_api("https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                {"location":"25.2048,55.2708","radius":"500","type":"supermarket","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Places API"] = ("ok",f"Active — {len(d.get('results',[]))} test results") if s in ("OK","ZERO_RESULTS") else \
                ("error",d.get("error_message","Not enabled")) if s=="REQUEST_DENIED" else ("warn",f"Status: {s}")
            d = test_api("https://maps.googleapis.com/maps/api/place/details/json",
                {"place_id":"ChIJRcbZaklDXz4RYlEphFBu5r0","fields":"name","key":api_key})
            s = d.get("status","UNKNOWN")
            results["Place Details API"] = ("ok","Active") if s=="OK" else \
                ("error",d.get("error_message","Not enabled")) if s=="REQUEST_DENIED" else ("warn",f"Status: {s}")
        st.session_state["api_health_cache"] = results

    if "api_health_cache" in st.session_state:
        for name,(status,msg) in st.session_state["api_health_cache"].items():
            fix = f"Enable in Google Cloud Console → APIs & Services → Library → search '{name.replace(' API','')}' → Enable." if status!="ok" else ""
            api_card(name,status,msg,fix)
        if all(s=="ok" for s,_ in st.session_state["api_health_cache"].values()):
            st.success("✅ All APIs active — pipeline ready to run")
        else:
            st.error("One or more APIs need to be enabled. See fix instructions above.")
    else:
        st.info("Click Run health check to verify all APIs are active.")

with st.expander("How to set permanent Secrets + how to get a Google API key"):
    st.markdown("""
**Set permanent secrets:** Streamlit Cloud → your app → ⋮ → Settings → Secrets → add:
```
ADMIN_PASSWORD      = "your-password"
GOOGLE_MAPS_API_KEY = "AIza..."
```
Save — app restarts in ~30 seconds.

**Get a Google API key:** [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials → Create API Key → Enable **Geocoding API** and **Places API** → link billing account.
    """)

# ── SECTION 2: SCORING MODEL DEFAULTS ────────────────────────────────────────
st.markdown("---")
sec("2","Scoring Model Defaults",
    "Set the default weights for the 6-signal store scoring formula. "
    "Each store gets a score 0-100. Weights must sum to 100%. "
    "Gap stores score 0 on Sales and Lines — their potential is what the model identifies as opportunity.",
    "Stage 3 — Scoring")

saved_w = st.session_state.get("admin_scoring_weights",
    {"rating":20,"reviews":25,"affluence":15,"poi":15,"sales":15,"lines":10})

c1,c2 = st.columns(2)
with c1:
    w_rating    = st.slider("⭐ Rating — Google star rating",         0,50,saved_w.get("rating",20))
    w_reviews   = st.slider("👥 Reviews — footfall proxy",           0,50,saved_w.get("reviews",25))
    w_affluence = st.slider("💰 Affluence — Google price level 1–4", 0,50,saved_w.get("affluence",15))
with c2:
    w_poi       = st.slider("📍 Nearby POI — location quality",      0,50,saved_w.get("poi",15))
    w_sales     = st.slider("💵 Current sales — your revenue",       0,50,saved_w.get("sales",15))
    w_lines     = st.slider("📦 Lines per store — SKU breadth",      0,50,saved_w.get("lines",10))

w_total = w_rating+w_reviews+w_affluence+w_poi+w_sales+w_lines
if w_total==100:
    st.success(f"Total: {w_total}% — valid ✓")
    if st.button("Save scoring weights", type="primary", key="save_weights"):
        st.session_state["admin_scoring_weights"] = {
            "rating":w_rating,"reviews":w_reviews,"affluence":w_affluence,
            "poi":w_poi,"sales":w_sales,"lines":w_lines}
        st.success("✅ Scoring weights saved.")
else:
    st.error(f"Total: {w_total}% — must equal exactly 100%")

# ── SECTION 3: STORE SIZE & VISIT BENCHMARKS ──────────────────────────────────
st.markdown("---")
sec("3","Store Size & Visit Benchmarks",
    "Define percentile splits for Large/Medium/Small classification within each category. "
    "Also set default visit frequency and duration per tier. Markets can override per-category in Configure.",
    "Stage 5 — Frequency")

saved_splits = st.session_state.get("admin_size_splits",{"large":20,"medium":40,"small":30,"occasional":10})
st.markdown("**Percentile splits:**")
st.caption("Set Occasional to 0% to disable — all bottom stores will fall into Small tier.")
c1,c2,c3,c4 = st.columns(4)
with c1:
    pct_large      = st.number_input("Large — top %",        min_value=5, max_value=50,step=5,value=saved_splits.get("large",20))
with c2:
    pct_medium     = st.number_input("Medium — next %",      min_value=10,max_value=70,step=5,value=saved_splits.get("medium",40))
with c3:
    pct_small      = st.number_input("Small — next %",       min_value=5, max_value=60,step=5,value=saved_splits.get("small",30))
with c4:
    pct_occasional = st.number_input("Occasional — bottom %",min_value=0, max_value=30,step=5,value=saved_splits.get("occasional",10),
        help="0.5 visits/month — visited once in the 2-month route plan. Set to 0 to disable.")

split_total = pct_large+pct_medium+pct_small+pct_occasional
if split_total==100: st.success(f"Total: {split_total}% — valid ✓")
else: st.error(f"Total: {split_total}% — must equal 100%")

saved_bench = st.session_state.get("admin_visit_benchmarks",{
    "large":{"visits_month":4,"duration_min":45},
    "medium":{"visits_month":2,"duration_min":30},
    "small":{"visits_month":1,"duration_min":15},
})
st.markdown("**Default visit benchmarks per tier:**")
new_bench = {}
bc1,bc2,bc3,bc4 = st.columns(4)
for col,tier,label,locked in [
    (bc1,"large","Large",False),(bc2,"medium","Medium",False),
    (bc3,"small","Small",False),(bc4,"occasional","Occasional",True)]:
    with col:
        st.markdown(f"**{label}**")
        if locked:
            st.info("0.5 visits/month — locked")
            d = st.number_input("Duration (min)", min_value=5,max_value=120,
                value=saved_bench.get(tier,{}).get("duration_min",15), key=f"d_{tier}")
            new_bench[tier] = {"visits_month":0.5,"duration_min":d}
            st.caption(f"1 visit per 2-month plan · {d} min/visit")
        else:
            v = st.number_input("Visits/month", min_value=1,max_value=12,
                value=saved_bench.get(tier,{}).get("visits_month",1 if tier=="small" else (2 if tier=="medium" else 4)),key=f"v_{tier}")
            d = st.number_input("Duration (min)", min_value=5,max_value=120,
                value=saved_bench.get(tier,{}).get("duration_min",15),key=f"d_{tier}")
            new_bench[tier] = {"visits_month":v,"duration_min":d}
            st.caption(f"{v} × {d} min = {v*d} min/store/month")

if split_total==100:
    if st.button("Save size & visit benchmarks", type="primary", key="save_bench"):
        st.session_state["admin_size_splits"]      = {"large":pct_large,"medium":pct_medium,"small":pct_small,"occasional":pct_occasional}
        st.session_state["admin_visit_benchmarks"] = new_bench
        st.session_state["admin_benchmarks"]       = {
            "large_pct":pct_large,"medium_pct":pct_medium,"small_pct":pct_small,"occasional_pct":pct_occasional,
            "large_visits":new_bench["large"]["visits_month"],"large_duration":new_bench["large"]["duration_min"],
            "medium_visits":new_bench["medium"]["visits_month"],"medium_duration":new_bench["medium"]["duration_min"],
            "small_visits":new_bench["small"]["visits_month"],"small_duration":new_bench["small"]["duration_min"],
        }
        st.success("✅ Size splits and visit benchmarks saved.")

# ── SECTION 4: REP PLANNING DEFAULTS ─────────────────────────────────────────
st.markdown("---")
sec("4","Rep Planning Defaults",
    "Set daily time budget, travel speed and minimum utilisation threshold. "
    "The utilisation threshold controls whether a rep is created — if their workload is below the threshold "
    "their stores are redistributed to other reps.",
    "Stage 6 — Route allocation")

saved_rep = st.session_state.get("admin_rep_defaults",{
    "minutes_per_day":480,"travel_speed_kmh":30,"working_days":22,"min_utilisation_pct":60
})

c1,c2,c3,c4 = st.columns(4)
with c1:
    minutes_day  = st.number_input("Total working day (min)",   min_value=240,max_value=600,step=30,value=saved_rep.get("minutes_per_day",480),
        help="Full working day including travel and breaks. Default 480 = 8 hours.")
    st.caption(f"{minutes_day//60}h {minutes_day%60}min total day")
with c2:
    break_mins   = st.number_input("Break time (min/day)",      min_value=0,  max_value=120,step=15,value=saved_rep.get("break_minutes",30),
        help="Lunch and rest breaks deducted from selling time. Default 30 min.")
    st.caption(f"Effective selling time: {minutes_day-break_mins} min/day")
with c3:
    travel_speed = st.number_input("Avg travel speed (km/h)",   min_value=10, max_value=80, step=5, value=saved_rep.get("travel_speed_kmh",30))
    st.caption("30 = dense city · 50 = suburban · 70 = rural")
with c4:
    working_days = st.number_input("Working days per month",    min_value=15, max_value=26, step=1, value=saved_rep.get("working_days",22))
    st.caption(f"Capacity: {(minutes_day-break_mins)*working_days:,} min/rep/month")

st.markdown("**Minimum utilisation threshold:**")
min_util = st.slider(
    "Minimum % of monthly capacity a rep must be assigned to justify their existence",
    min_value=20,max_value=90,value=saved_rep.get("min_utilisation_pct",60),step=5,
    help="Applies in both Recommended and Fixed modes. Under-utilised reps have their stores redistributed."
)
min_minutes = round(minutes_day * working_days * min_util / 100)
st.caption(
    f"At {min_util}% threshold: a rep needs at least {min_minutes:,} min/month of work "
    f"(out of {minutes_day*working_days:,} min capacity) to be assigned. "
    "Below this their stores go to the nearest rep."
)

if st.button("Save rep planning defaults", type="primary", key="save_rep"):
    st.session_state["admin_rep_defaults"] = {
        "minutes_per_day":     minutes_day,
        "break_minutes":       break_mins,
        "travel_speed_kmh":    travel_speed,
        "working_days":        working_days,
        "min_utilisation_pct": min_util,
    }
    st.success("✅ Rep planning defaults saved.")

# ── SECTION 5: COVERAGE MATCHING ─────────────────────────────────────────────
st.markdown("---")
sec("5","Coverage Matching Rules",
    "Controls how the pipeline decides whether a Google-scraped store is already covered by your portfolio. "
    "This affects your coverage rate and gap count — if the radius is too small, stores you already sell to "
    "will appear as gaps. If too large, stores you don't sell to will be incorrectly marked as covered.",
    "Stage 4 — Gap matching")

st.markdown("""
<div style="background:#F0F4F8;border:1px solid #D0DCF0;border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem;font-size:0.88rem;line-height:1.7">
<strong>How coverage matching works:</strong><br>
After scraping Google Places, every store in the universe is checked against your portfolio to see if it is already covered.
A scraped store is marked <strong>covered</strong> if it matches a portfolio store by any of these rules:<br><br>
<strong>1. Same Google Place ID</strong> — Google assigns a unique ID to every location. If the scraped store and your portfolio store share the same ID, they are definitively the same store. No distance needed.<br><br>
<strong>2. Same GPS coordinates</strong> — If the coordinates match (rounded to ~11m precision), it is the same physical point.<br><br>
<strong>3. Within distance radius</strong> — If a scraped store is within the configured radius of a portfolio store, it is treated as covered. This handles GPS rounding and geocoding differences for the same address.<br><br>
<strong>4. Within extended radius + similar name</strong> — If a scraped store is within the extended radius AND its name is similar to a nearby portfolio store, it is also treated as covered. This catches cases where Google uses a slightly different store name.<br><br>
⚠️ <strong>Be careful with large radii in dense cities</strong> — two different stores can be 100-150m apart in a city centre. A radius that is too large will incorrectly mark genuine gaps as covered.
</div>
""", unsafe_allow_html=True)

saved_match = st.session_state.get("admin_matching", {
    "base_radius_m": 100,
    "fuzzy_radius_m": 150,
    "fuzzy_threshold_pct": 60,
})

c1, c2, c3 = st.columns(3)
with c1:
    base_radius = st.number_input(
        "Base match radius (metres)",
        min_value=10, max_value=300, value=saved_match.get("base_radius_m", 100), step=10,
        help="Distance within which a scraped store is automatically marked as covered. Safe range: 50-100m for cities, up to 200m for rural markets."
    )
    st.caption("Recommended: 100m city · 150m suburban · 200m rural")
with c2:
    fuzzy_radius = st.number_input(
        "Extended radius for name matching (metres)",
        min_value=50, max_value=500, value=saved_match.get("fuzzy_radius_m", 150), step=25,
        help="Stores within this radius are also checked for name similarity. Only matched if name similarity passes the threshold below."
    )
    st.caption("Only applies when names are similar enough")
with c3:
    fuzzy_threshold = st.slider(
        "Name similarity threshold %",
        min_value=40, max_value=90, value=saved_match.get("fuzzy_threshold_pct", 60), step=5,
        help="How similar the store names must be to count as a match. 60% = loose match (handles abbreviations). 80% = strict match (near-identical names only)."
    )
    st.caption(f"Example: 'Bom Preco' vs 'Bom Preço' ≈ 85% similar")

st.info(
    f"With current settings: stores within **{base_radius}m** are always covered. "
    f"Stores {base_radius}-{fuzzy_radius}m away are covered only if names are **{fuzzy_threshold}%+ similar**. "
    f"Stores beyond {fuzzy_radius}m are always gaps."
)

if st.button("Save matching rules", type="primary", key="save_match"):
    st.session_state["admin_matching"] = {
        "base_radius_m":      base_radius,
        "fuzzy_radius_m":     fuzzy_radius,
        "fuzzy_threshold_pct": fuzzy_threshold,
    }
    st.success("✅ Matching rules saved — will apply on next pipeline run.")

# ── SECTION 6: APP ACCESS ─────────────────────────────────────────────────────
st.markdown("---")
sec("6","App Access","Manage admin session and password.")

with st.expander("How to change the admin password"):
    st.markdown("""
1. Streamlit Cloud → your app → ⋮ → Settings → Secrets
2. Update: `ADMIN_PASSWORD = "new-password-here"`
3. Save — takes effect in ~30 seconds.
    """)

st.markdown("---")
if st.button("🔒 Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
