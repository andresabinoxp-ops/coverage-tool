import streamlit as st
import requests

st.set_page_config(page_title="Admin - Coverage Tool", page_icon=" ", layout="wide")

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



    <h2>  Admin Settings</h2>
    <p>Configure global defaults for all markets &mdash; changes here apply to every new pipeline run</p>
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

st.success("  Authenticated as Admin")
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
    icons  = {"ok":" ","error":" ","warn":" "}
    colors = {"ok":"#1B5E20","error":"#B71C1C","warn":"#E65100"}
    fix_html = (f'<div style="background:#E3F2FD;border-radius:5px;padding:5px 10px;'
                f'margin-top:5px;font-size:0.8rem;color:#0D47A1">  {fix}</div>') if fix and status != "ok" else ""
    st.markdown(
        f'<div class="{css.get(status,"api-warn")}">'
        f'<span style="font-weight:700;color:{colors.get(status,"#555")}">'
        f'{icons.get(status," ")} {name}</span>'
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
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-set">  Set — {m}</span></div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">  Not set</span></div>',unsafe_allow_html=True)
    except Exception:
        st.markdown(f'<div class="key-card"><span class="key-label">{label}</span><span class="key-unset">  Not set</span></div>',unsafe_allow_html=True)

if st.session_state.get("session_api_key"):
    k = st.session_state["session_api_key"]
    m = k[:4]+"••••••••"+k[-4:]
    st.markdown(f'<div class="key-card"><span class="key-label">Session key (this session only)</span><span class="key-set">  Active — {m}</span></div>',unsafe_allow_html=True)

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
    if st.button("  Run health check", type="primary", key="health_btn"):
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
            st.success("  All APIs active — pipeline ready to run")
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
    "Two separate scoring groups. Group 1 = Current Coverage (has internal sales data). "
    "Group 2 = Google Scraping (gap stores, no internal data). "
    "After scoring each group separately, all stores are combined for routing.",
    "Stage 3 — Scoring")

saved_w1 = st.session_state.get("admin_scoring_weights",
    {"rating":20,"reviews":25,"affluence":15,"poi":15,"sales":15,"lines":10})
saved_w2 = st.session_state.get("admin_scoring_weights_gap",
    {"rating":25,"reviews":25,"affluence":25,"poi":25})

st.markdown("**Group 1 — Current Coverage** (Rating · Reviews · Affluence · Nearby POI · Lines per Store · Value Sales)")
st.caption("Default weights: 20 · 25 · 15 · 15 · 15 · 10")
c1,c2 = st.columns(2)
with c1:
    w1_rating    = st.slider("  Rating",         0,50,saved_w1.get("rating",20),   key="w1_rat")
    w1_reviews   = st.slider("  Reviews",        0,50,saved_w1.get("reviews",25),  key="w1_rev")
    w1_affluence = st.slider("  Affluence",      0,50,saved_w1.get("affluence",15),key="w1_aff")
with c2:
    w1_poi       = st.slider("  Nearby POI",     0,50,saved_w1.get("poi",15),      key="w1_poi")
    w1_sales     = st.slider("  Value Sales",    0,50,saved_w1.get("sales",15),    key="w1_sal")
    w1_lines     = st.slider("  Lines per Store",0,50,saved_w1.get("lines",10),    key="w1_lin")
w1_total = w1_rating+w1_reviews+w1_affluence+w1_poi+w1_sales+w1_lines
if w1_total==100: st.success(f"Group 1 total: {w1_total}% ✓")
else: st.error(f"Group 1 total: {w1_total}% — must equal 100%")

st.markdown("**Group 2 — Google Scraping** (Rating · Reviews · Affluence · Nearby POI only)")
st.caption("Default weights: 25 · 25 · 25 · 25")
c3,c4 = st.columns(2)
with c3:
    w2_rating    = st.slider("  Rating",    0,50,saved_w2.get("rating",25),   key="w2_rat")



    w2_reviews   = st.slider("  Reviews",   0,50,saved_w2.get("reviews",25),  key="w2_rev")
with c4:
    w2_affluence = st.slider("  Affluence", 0,50,saved_w2.get("affluence",25),key="w2_aff")
    w2_poi       = st.slider("  Nearby POI",0,50,saved_w2.get("poi",25),      key="w2_poi")
w2_total = w2_rating+w2_reviews+w2_affluence+w2_poi
if w2_total==100: st.success(f"Group 2 total: {w2_total}% ✓")
else: st.error(f"Group 2 total: {w2_total}% — must equal 100%")

if w1_total==100 and w2_total==100:
    if st.button("Save scoring weights", type="primary", key="save_weights"):
        st.session_state["admin_scoring_weights"] = {
            "rating":w1_rating,"reviews":w1_reviews,"affluence":w1_affluence,
            "poi":w1_poi,"sales":w1_sales,"lines":w1_lines}
        st.session_state["admin_scoring_weights_gap"] = {
            "rating":w2_rating,"reviews":w2_reviews,
            "affluence":w2_affluence,"poi":w2_poi}
        st.success("  Scoring weights saved for both groups.")

# ── SECTION 3: STORE SIZE & VISIT BENCHMARKS ──────────────────────────────────
st.markdown("---")
sec("3","Store Size & Visit Benchmarks per Sub-channel",
    "Define percentile splits for Large/Medium/Small classification within each category. "
    "Also set default visit frequency and duration per tier. Markets can override per-category in Configure.",
    "Stage 5 — Frequency")

saved_splits = st.session_state.get("admin_size_splits",{"large":20,"medium":40,"small":40})
st.markdown("**Percentile splits:**")
st.caption("Splits must sum to 100%. Small frequency drives the plan period — e.g. 0.5 visits/month = 2-month plan.")
c1,c2,c3 = st.columns(3)
with c1:
    pct_large  = st.number_input("Large — top %",   min_value=5, max_value=50,step=5,value=saved_splits.get("large",20))
with c2:
    pct_medium = st.number_input("Medium — next %", min_value=10,max_value=70,step=5,value=saved_splits.get("medium",40))
with c3:
    pct_small  = st.number_input("Small — bottom %",min_value=5, max_value=70,step=5,value=saved_splits.get("small",40))

split_total = pct_large+pct_medium+pct_small
if split_total==100: st.success(f"Total: {split_total}% — valid ✓")
else: st.error(f"Total: {split_total}% — must equal 100%")

saved_bench = st.session_state.get("admin_visit_benchmarks",{
    "large":{"visits_month":4,"duration_min":45},
    "medium":{"visits_month":2,"duration_min":30},
    "small":{"visits_month":1,"duration_min":15},
})
st.markdown("**Default visit benchmarks per tier:**")
new_bench = {}



bc1,bc2,bc3 = st.columns(3)
for col,tier,label,default_v,default_d in [
    (bc1,"large","Large",4,40),
    (bc2,"medium","Medium",2,25),
    (bc3,"small","Small",1,15)]:
    with col:
        st.markdown(f"**{label}**")
        v = st.number_input("Visits/month", min_value=0.1,max_value=12.0,step=0.01,
            value=float(saved_bench.get(tier,{}).get("visits_month",default_v)),key=f"v_{tier}",
            help="Use decimals for less-than-monthly frequency: 0.5 = every 2 months, 0.33 = every 3 months")
        d = st.number_input("Duration (min)", min_value=5,max_value=120,
            value=saved_bench.get(tier,{}).get("duration_min",default_d),key=f"d_{tier}")
        new_bench[tier] = {"visits_month":v,"duration_min":d}
        if v >= 1:
            st.caption(f"{v:.0f}x/month · {d} min · {v*d:.0f} min/store/month")
        else:
            plan_mo = round(1/v)
            st.caption(f"1 visit every {plan_mo} months · {d} min/visit")

if split_total==100:
    if st.button("Save size & visit benchmarks", type="primary", key="save_bench"):
        st.session_state["admin_size_splits"]      = {"large":pct_large,"medium":pct_medium,"small":pct_small}
        st.session_state["admin_visit_benchmarks"] = new_bench
        st.session_state["admin_benchmarks"]       = {
            "large_pct":pct_large,"medium_pct":pct_medium,"small_pct":pct_small,
            "large_visits":new_bench["large"]["visits_month"],"large_duration":new_bench["large"]["duration_min"],
            "medium_visits":new_bench["medium"]["visits_month"],"medium_duration":new_bench["medium"]["duration_min"],
            "small_visits":new_bench["small"]["visits_month"],"small_duration":new_bench["small"]["duration_min"],
        }
        st.success("  Size splits and visit benchmarks saved.")

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

st.markdown("**Utilisation thresholds:**")
st.caption("60% min daily · 80% min monthly · 110% max daily")
min_util = st.slider(
    "Minimum monthly utilisation % (reps below this are removed)",
    min_value=20, max_value=90, value=saved_rep.get("min_utilisation_pct", 80), step=5,
    help="Recommended: 80% monthly minimum."
)
min_minutes = round(minutes_day * working_days * min_util / 100)
st.caption(
    f"At {min_util}% threshold: a rep needs at least {min_minutes:,} min/month "
    f"(out of {minutes_day*working_days:,} min capacity). Below this their stores go to nearest rep."
)

st.markdown("**Store selection (Recommended mode only):**")
store_select_pct = st.slider(
    "Top % of stores to include",
    min_value=30, max_value=100, value=saved_rep.get("store_select_pct", 60), step=5,
    help="In Recommended mode: top X% by normalised score (Group 1 = with sales data, Group 2 = without — normalised separately). Default 60%."
)
st.caption("Fixed mode always includes all stores.")

if st.button("Save rep planning defaults", type="primary", key="save_rep"):
    st.session_state["admin_rep_defaults"] = {
        "minutes_per_day":     minutes_day,
        "break_minutes":       break_mins,
        "travel_speed_kmh":    travel_speed,
        "working_days":        working_days,
        "min_utilisation_pct": min_util,
        "store_select_pct":    store_select_pct,
    }
    st.success("  Rep planning defaults saved.")

# ── SECTION 5: ENRICHMENT SETTINGS ───────────────────────────────────────────
st.markdown("---")
sec("5","Enrichment Settings",



    "Control which optional enrichment steps run during the pipeline. "
    "Place Details fetches price level, phone and opening hours. "
    "Nearby POI counts points of interest around each store for the affluence and POI score signals.",
    "Stage 7/8 — Enrichment")

saved_enrich = st.session_state.get("admin_enrichment", {
    "run_place_details": True,
    "run_poi":           True,
    "poi_radius_m":      500,
})

col_e1, col_e2, col_e3 = st.columns(3)
with col_e1:
    run_place_details = st.toggle(
        "  Place Details enrichment",
        value=saved_enrich.get("run_place_details", True),
        help="Fetches phone, opening hours, website and price level (affluence) for all stores. Costs ~$0.017/store."
    )
with col_e2:
    run_poi = st.toggle(
        "  Nearby POI enrichment",
        value=saved_enrich.get("run_poi", True),
        help="Counts nearby points of interest within the radius below. Used in POI scoring signal. Costs ~$0.032/call."
    )
with col_e3:
    poi_radius_m = st.number_input(
        "POI search radius (metres)",
        min_value=100, max_value=2000,
        value=saved_enrich.get("poi_radius_m", 500),
        step=100,
        help="Search radius for counting nearby POIs. 500m = ~5 min walk."
    )

if st.button("Save enrichment settings", type="primary", key="save_enrich"):
    st.session_state["admin_enrichment"] = {
        "run_place_details": run_place_details,
        "run_poi":           run_poi,
        "poi_radius_m":      poi_radius_m,
    }
    st.success("  Enrichment settings saved.")
else:
    # Apply immediately to session state even without saving
    st.session_state["admin_enrichment"] = {
        "run_place_details": run_place_details,
        "run_poi":           run_poi,
        "poi_radius_m":      poi_radius_m,
    }



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
if st.button("  Log out"):
    st.session_state["admin_authenticated"] = False
    st.rerun()
