import streamlit as st
import pandas as pd
import time
import math
import requests
import random

st.set_page_config(page_title="Run Pipeline - Coverage Tool", page_icon="📤", layout="wide")

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
.info-box {
    background: #E3F2FD; border: 1px solid #90CAF9; border-left: 4px solid #1565C0;
    border-radius: 8px; padding: 0.8rem 1.2rem; margin: 0.5rem 0;
    color: #0D47A1; font-size: 0.88rem;
}
.preflight-card { border-radius: 10px; padding: 1.4rem 1.8rem; margin: 1rem 0; border: 1.5px solid; }
.preflight-green { background: #F1F8F1; border-color: #66BB6A; }
.preflight-amber { background: #FFFBF0; border-color: #FFA726; }
.preflight-red   { background: #FFF5F5; border-color: #EF5350; }
.preflight-title { font-size: 1rem; font-weight: 700; margin-bottom: 0.8rem; }
.preflight-green .preflight-title { color: #2E7D32; }
.preflight-amber .preflight-title { color: #E65100; }
.preflight-red   .preflight-title { color: #B71C1C; }

/* Main stat grid - time and cost side by side */
.main-stats {
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 1rem;
}
.main-stat-box {
    background: white; border-radius: 8px; padding: 1rem 1.2rem;
    border: 1px solid #E0E0E0;
}
.main-stat-val   { font-size: 1.8rem; font-weight: 800; color: #1A2B4A; line-height: 1; }
.main-stat-label { font-size: 0.75rem; color: #9E9E9E; text-transform: uppercase;
                   letter-spacing: 0.05em; margin-top: 4px; }

/* Cost breakdown */
.cost-breakdown {
    background: white; border-radius: 8px; padding: 1rem 1.2rem;
    border: 1px solid #E0E0E0; margin-bottom: 0.8rem;
}
.cost-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; border-bottom: 1px solid #F5F5F5; font-size: 0.85rem;
}
.cost-row:last-child { border-bottom: none; font-weight: 700; color: #1A2B4A; }
.cost-label  { color: #4A5568; }
.cost-detail { color: #9E9E9E; font-size: 0.78rem; margin-left: 8px; }
.cost-value  { font-weight: 600; color: #1565C0; }
.cost-total  { font-weight: 800; color: #1A2B4A; font-size: 1rem; }

/* Detail stats */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 0.8rem; }
.stat-box { background: white; border-radius: 8px; padding: 0.7rem 1rem;
            text-align: center; border: 1px solid #E0E0E0; }
.stat-val   { font-size: 1.3rem; font-weight: 800; color: #1A2B4A; line-height: 1; }
.stat-label { font-size: 0.7rem; color: #9E9E9E; text-transform: uppercase;
              letter-spacing: 0.05em; margin-top: 4px; }
.suggestion-box {
    background: white; border-radius: 6px; padding: 0.7rem 1rem;
    border-left: 3px solid #FFA726; font-size: 0.85rem; color: #4A4A4A; margin-top: 0.5rem;
}
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white;
    border-radius: 6px; font-weight: 600; font-size: 1rem; padding: 0.6rem 2rem;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📤 Run Pipeline</h2>
    <p>Upload your portfolio, configure enrichment, review the full cost estimate — then run</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.get("market_config"):
    st.warning("No market configured. Please go to Configure in the sidebar first.")
    st.stop()

cfg = st.session_state["market_config"]
st.markdown(f"""
<div class="info-box">
    <strong>Market:</strong> {cfg['market_name']} &nbsp;|&nbsp;
    <strong>Reps:</strong> {cfg['rep_count']} &nbsp;|&nbsp;
    <strong>Scraping:</strong> {", ".join(cfg["categories"])}
</div>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GEOCODE_URL      = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL       = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACE_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"
TIER_MULT        = {1:1.0, 2:0.8, 3:0.55, 4:0.30}
MAX_TILES        = 400

# Google API pricing (USD)
PRICE_NEARBY_PER_CALL   = 0.032   # per call, returns up to 20 results
PRICE_GEOCODE_PER_CALL  = 0.005   # per address geocoded
PRICE_DETAILS_PER_CALL  = 0.017   # per place details call

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_api_key():
    if cfg.get("market_api_key"):
        return cfg["market_api_key"]
    if st.session_state.get("market_api_key_input"):
        return st.session_state["market_api_key_input"]
    if st.session_state.get("session_api_key"):
        return st.session_state["session_api_key"]
    try:
        k = st.secrets.get("GOOGLE_MAPS_API_KEY","")
        if k: return k
    except Exception:
        pass
    st.error("No Google API key found. Go to Admin Settings or Configure to add your key.")
    st.stop()

def smart_tile_radius(lat_min, lat_max, lng_min, lng_max, max_tiles=MAX_TILES):
    mid        = (lat_min + lat_max) / 2
    lat_span_m = abs(lat_max - lat_min) * 111320
    lng_span_m = abs(lng_max - lng_min) * 111320 * math.cos(math.radians(mid))
    area_m2    = lat_span_m * lng_span_m
    for radius_m in [1000,2000,3000,5000,8000,10000,15000,20000,30000,50000]:
        tile_area = (radius_m * 2) ** 2
        n_tiles   = math.ceil(area_m2 / tile_area)
        if n_tiles <= max_tiles:
            return radius_m, n_tiles
    return 50000, max_tiles

def grid_centres(lat_min, lat_max, lng_min, lng_max, radius_m):
    dlat = (radius_m*2)/111320
    mid  = (lat_min+lat_max)/2
    dlng = (radius_m*2)/(111320*math.cos(math.radians(mid)))
    centres = []
    lat = lat_min + dlat/2
    while lat < lat_max:
        lng = lng_min + dlng/2
        while lng < lng_max:
            centres.append((round(lat,5), round(lng,5)))
            lng += dlng
        lat += dlat
    return centres[:MAX_TILES]

def fmt_time(seconds):
    mins = seconds / 60
    if mins < 1:      return f"~{round(seconds)} seconds"
    elif mins < 60:
        m = int(mins); s = int((mins-m)*60)
        return f"~{m} min {s} sec" if s > 0 else f"~{m} minutes"
    else:
        h = int(mins//60); m = int(mins%60)
        return f"~{h}h {m}min"

def get_portfolio_count():
    pf = st.session_state.get("portfolio_df")
    return len(pf) if pf is not None else 0

def calculate_estimate(enrich_count, enrich_scope):
    """
    Full unified cost + time estimate.
    Returns dict with all breakdown figures.
    """
    radius_m, n_tiles = smart_tile_radius(
        cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"]
    )
    n_categories  = len(cfg["categories"])
    n_portfolio   = get_portfolio_count()

    # Scraping
    avg_pages         = 1.8
    scrape_calls      = round(n_tiles * n_categories * avg_pages)
    scrape_cost       = scrape_calls * PRICE_NEARBY_PER_CALL
    scrape_time       = scrape_calls * 0.35 + n_tiles * n_categories * (avg_pages-1) * 2

    # Geocoding
    geocode_calls     = n_portfolio
    geocode_cost      = geocode_calls * PRICE_GEOCODE_PER_CALL
    geocode_time      = geocode_calls * 0.15

    # Enrichment
    # Estimate universe size for scope
    estimated_universe = n_tiles * n_categories * 15  # ~15 stores per tile average
    if enrich_scope == "none":
        enrich_calls, enrich_cost = 0, 0.0
    elif enrich_scope == "top_n":
        enrich_calls = enrich_count
        enrich_cost  = enrich_calls * PRICE_DETAILS_PER_CALL
    elif enrich_scope == "gaps_only":
        # estimate ~60% are gaps
        enrich_calls = min(enrich_count, round(estimated_universe * 0.6))
        enrich_cost  = enrich_calls * PRICE_DETAILS_PER_CALL
    else:  # all
        enrich_calls = min(enrich_count, estimated_universe)
        enrich_cost  = enrich_calls * PRICE_DETAILS_PER_CALL

    enrich_time = enrich_calls * 0.15

    # Totals
    total_calls   = scrape_calls + geocode_calls + enrich_calls
    total_cost    = scrape_cost + geocode_cost + enrich_cost
    total_seconds = scrape_time + geocode_time + enrich_time + 15

    # Traffic light
    total_minutes = total_seconds / 60
    if total_minutes < 5:
        colour, icon, label = "green", "✅", "Quick run — ready to go"
    elif total_minutes < 15:
        colour, icon, label = "amber", "⚠️", "Moderate run — consider narrowing if needed"
    else:
        colour, icon, label = "red", "🔴", "Long run — recommend selecting specific cities"

    # Area
    lat_span = abs(cfg["lat_max"] - cfg["lat_min"])
    lng_span = abs(cfg["lng_max"] - cfg["lng_min"])
    mid      = (cfg["lat_min"] + cfg["lat_max"]) / 2
    area_km2 = round(lat_span * 111 * lng_span * 111 * math.cos(math.radians(mid)))

    suggestions = []
    if total_minutes > 15:
        suggestions.append("Go back to Configure and select specific cities or districts to reduce run time.")
    if n_categories > 4 and total_minutes > 5:
        suggestions.append(f"Reduce categories from {n_categories} to 2-3 most important to cut scraping time.")
    if enrich_calls > 500:
        suggestions.append(f"Enriching {enrich_calls:,} stores will take ~{fmt_time(enrich_time)} extra. Consider Top N mode to enrich only the highest-scoring stores.")

    return {
        "radius_m":          radius_m,
        "n_tiles":           n_tiles,
        "n_categories":      n_categories,
        "n_portfolio":       n_portfolio,
        "area_km2":          area_km2,
        "scrape_calls":      scrape_calls,
        "scrape_cost":       scrape_cost,
        "scrape_time":       scrape_time,
        "geocode_calls":     geocode_calls,
        "geocode_cost":      geocode_cost,
        "geocode_time":      geocode_time,
        "enrich_calls":      enrich_calls,
        "enrich_cost":       enrich_cost,
        "enrich_time":       enrich_time,
        "total_calls":       total_calls,
        "total_cost":        total_cost,
        "total_seconds":     total_seconds,
        "total_minutes":     total_minutes,
        "colour":            colour,
        "icon":              icon,
        "label":             label,
        "suggestions":       suggestions,
        "estimated_universe": estimated_universe,
    }

def geocode_store(address, city, api_key):
    try:
        r = requests.get(GEOCODE_URL,
            params={"address":f"{address}, {city}","key":api_key}, timeout=10)
        data = r.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception:
        pass
    return None, None

def fetch_places(lat, lng, radius, place_type, api_key, token=None):
    try:
        if token:
            time.sleep(2)
            params = {"pagetoken":token,"key":api_key}
        else:
            params = {"location":f"{lat},{lng}","radius":radius,"type":place_type,"key":api_key}
        r = requests.get(PLACES_URL, params=params, timeout=15)
        return r.json()
    except Exception:
        return {}

def fetch_place_details(place_id, api_key):
    try:
        r = requests.get(PLACE_DETAIL_URL,
            params={"place_id":place_id,
                    "fields":"formatted_phone_number,opening_hours,website,formatted_address",
                    "key":api_key},
            timeout=10)
        data = r.json()
        if data.get("status") == "OK":
            return data.get("result",{})
    except Exception:
        pass
    return {}

def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1,p2 = math.radians(lat1),math.radians(lat2)
    dp,dl = math.radians(lat2-lat1),math.radians(lng2-lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def kmeans_simple(points, k, iterations=20):
    if len(points) <= k: return list(range(len(points)))
    centroids = random.sample(points, k)
    labels = [0]*len(points)
    for _ in range(iterations):
        for i,p in enumerate(points):
            dists = [haversine_m(p[0],p[1],c[0],c[1]) for c in centroids]
            labels[i] = dists.index(min(dists))
        new_c = []
        for j in range(k):
            cluster = [points[i] for i in range(len(points)) if labels[i]==j]
            new_c.append((
                sum(p[0] for p in cluster)/len(cluster),
                sum(p[1] for p in cluster)/len(cluster)
            ) if cluster else centroids[j])
        centroids = new_c
    return labels

def assign_freq(score, t):
    if score >= t["weekly"]:      return "weekly",      4.0
    if score >= t["fortnightly"]: return "fortnightly", 2.0
    if score >= t["monthly"]:     return "monthly",     1.0
    return "bi-weekly", 0.5

# ── API HEALTH CHECK ─────────────────────────────────────────────────────────
def run_api_health_check(api_key):
    results = {}
    apis = [
        ("Geocoding API",
         "https://maps.googleapis.com/maps/api/geocode/json",
         {"address":"Dubai, UAE","key":api_key}),
        ("Places API",
         "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
         {"location":"25.2048,55.2708","radius":"500","type":"supermarket","key":api_key}),
        ("Place Details API",
         "https://maps.googleapis.com/maps/api/place/details/json",
         {"place_id":"ChIJRcbZaklDXz4RYlEphFBu5r0","fields":"name","key":api_key}),
    ]
    for name, url, params in apis:
        try:
            r = requests.get(url, params=params, timeout=6)
            s = r.json().get("status","UNKNOWN")
            if s in ("OK","ZERO_RESULTS"):
                results[name] = ("ok", "Active and working")
            elif s == "REQUEST_DENIED":
                msg = r.json().get("error_message","Not enabled or key invalid")
                results[name] = ("error", msg)
            else:
                results[name] = ("warn", f"Unexpected status: {s}")
        except Exception as e:
            results[name] = ("error", str(e))
    return results

def api_check_html(name, status, message):
    icons  = {"ok":"✅","error":"❌","warn":"⚠️"}
    colors = {"ok":"#2E7D32","error":"#C62828","warn":"#E65100"}
    bgs    = {"ok":"#E8F5E9","error":"#FFF5F5","warn":"#FFF8E1"}
    bords  = {"ok":"#A5D6A7","error":"#FFCDD2","warn":"#FFE082"}
    return (f'<div style="background:{bgs[status]};border:1px solid {bords[status]};'
            f'border-left:4px solid {colors[status]};border-radius:6px;'
            f'padding:8px 12px;margin-bottom:6px">'
            f'<span style="font-weight:700;color:{colors[status]}">{icons[status]} {name}</span>'
            f'<span style="font-size:0.82rem;color:{colors[status]};margin-left:8px">{message}</span>'
            f'</div>')

# Resolve key
_check_key = (cfg.get("market_api_key")
    or st.session_state.get("market_api_key_input")
    or st.session_state.get("session_api_key"))
if not _check_key:
    try:
        _check_key = st.secrets.get("GOOGLE_MAPS_API_KEY","") or None
    except Exception:
        _check_key = None

st.markdown('<div class="section-title">API status</div>', unsafe_allow_html=True)

if not _check_key:
    st.markdown("""
    <div style="background:#FFF5F5;border:1px solid #FFCDD2;border-left:4px solid #C62828;
    border-radius:8px;padding:1rem 1.2rem;margin-bottom:1rem">
        <div style="font-weight:700;color:#B71C1C;margin-bottom:6px">❌ No Google API key found</div>
        <div style="font-size:0.85rem;color:#C62828;line-height:1.6">
            The pipeline cannot run without a Google Maps API key.<br>
            <strong>Option 1:</strong> Ask your admin to set GOOGLE_MAPS_API_KEY in Streamlit Secrets.<br>
            <strong>Option 2:</strong> Go to Admin Settings and paste a key there.<br>
            <strong>Option 3:</strong> Paste your own key in the Configure page under Step 2.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.caption("All three APIs must be enabled in Google Cloud Console. Click Check APIs to verify before running.")
    with col_b:
        do_check = st.button("🔍 Check APIs", key="quick_check")

    if do_check:
        with st.spinner("Checking APIs..."):
            st.session_state["api_health_cache"] = run_api_health_check(_check_key)

    if "api_health_cache" in st.session_state:
        check_res = st.session_state["api_health_cache"]
        all_ok    = all(s == "ok" for s, _ in check_res.values())
        html_out  = "".join(api_check_html(n, s, m) for n, (s, m) in check_res.items())
        if not all_ok:
            html_out += (
                '<div style="background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;'
                'padding:8px 12px;margin-top:6px;font-size:0.82rem;color:#0D47A1">'
                '🔧 To fix: go to <a href="https://console.cloud.google.com/apis/library" target="_blank">'
                'console.cloud.google.com → APIs &amp; Services → Library</a> → '
                'search the API name → click Enable → come back and click Check APIs again.'
                '</div>'
            )
        st.markdown(html_out, unsafe_allow_html=True)
        if all_ok:
            st.success("✅ All APIs active — pipeline ready to run")
    else:
        st.info("Click **Check APIs** above to verify everything is enabled before running.")

st.markdown("---")

# ── STEP 1: PORTFOLIO UPLOAD ──────────────────────────────────────────────────
st.markdown('<div class="section-title">1. Portfolio CSV</div>', unsafe_allow_html=True)
st.markdown("Required: `store_name`, `address`, `city` | Optional: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`")

portfolio_df = st.session_state.get("portfolio_df")
if portfolio_df is not None:
    st.success(f"✅ Using portfolio from Configure — {len(portfolio_df)} stores")
    st.dataframe(portfolio_df.head(3), use_container_width=True)
    if st.checkbox("Upload a different file"):
        portfolio_df = None
        st.session_state["portfolio_df"] = None

if portfolio_df is None:
    up = st.file_uploader("Upload portfolio CSV", type=["csv"])
    if up:
        try:
            df = pd.read_csv(up)
            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            missing = [c for c in ["store_name","address","city"] if c not in df.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                if "store_id"          not in df.columns: df["store_id"]          = [f"S{i+1:03d}" for i in range(len(df))]
                if "annual_sales_usd"  not in df.columns: df["annual_sales_usd"]  = 0
                if "lines_per_store"   not in df.columns: df["lines_per_store"]   = 0
                if "category"          not in df.columns: df["category"]          = cfg["categories"][0] if cfg["categories"] else "supermarket"
                portfolio_df = df
                st.session_state["portfolio_df"] = df
                st.success(f"✅ Loaded {len(df)} stores")
                st.dataframe(df.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Qurum","city":"Muscat","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Lulu Hypermarket","address":"Al Khuwair","city":"Muscat","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
])
st.download_button("⬇️ Download sample CSV", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")

# ── STEP 2: ENRICHMENT CONFIG ─────────────────────────────────────────────────
st.markdown('<div class="section-title">2. Phone & opening hours enrichment (optional)</div>', unsafe_allow_html=True)
st.caption("Configure enrichment before running — cost is included in the pre-flight estimate below.")

enrich_scope_label = st.radio(
    "Which stores to enrich with phone and opening hours",
    options=["None — skip enrichment",
             "Top N stores by score",
             "All gap stores (uncovered only)",
             "All scraped stores (full universe)"],
    index=0,
    horizontal=True,
)

enrich_scope_map = {
    "None — skip enrichment":           "none",
    "Top N stores by score":            "top_n",
    "All gap stores (uncovered only)":  "gaps_only",
    "All scraped stores (full universe)": "all",
}
enrich_scope = enrich_scope_map[enrich_scope_label]

# Estimated universe for slider max
radius_m_est, n_tiles_est = smart_tile_radius(
    cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"]
)
est_universe = max(50, n_tiles_est * len(cfg["categories"]) * 15)

enrich_count = 0
if enrich_scope in ("top_n", "gaps_only", "all"):
    if enrich_scope == "top_n":
        enrich_count = st.slider(
            "Number of top stores to enrich",
            min_value=10,
            max_value=min(est_universe, 2000),
            value=min(50, est_universe),
            step=10,
            help="Stores are ranked by score. Highest-scoring stores are enriched first."
        )
    elif enrich_scope == "gaps_only":
        enrich_count = min(est_universe, 2000)
        st.caption(f"Will enrich all gap stores found during scraping (estimated ~{round(enrich_count*0.6):,} stores — 60% of universe are typically gaps).")
    else:  # all
        enrich_count = min(est_universe, 2000)
        st.caption(f"Will enrich all {enrich_count:,} estimated scraped stores. See cost below before proceeding.")

st.markdown("---")

# ── STEP 3: PRE-FLIGHT ESTIMATE ───────────────────────────────────────────────
st.markdown('<div class="section-title">3. Pre-flight — full cost & time estimate</div>', unsafe_allow_html=True)
st.caption("Calculated from your market area, categories, portfolio size and enrichment selection.")

est          = calculate_estimate(enrich_count, enrich_scope)
time_display = fmt_time(est["total_seconds"])
colour_class = f"preflight-{est['colour']}"
radius_labels = {1000:"1 km",2000:"2 km",3000:"3 km",5000:"5 km",8000:"8 km",
                 10000:"10 km",15000:"15 km",20000:"20 km",30000:"30 km",50000:"50 km"}
radius_label = radius_labels.get(est["radius_m"], f"{est['radius_m']//1000} km")

# Build cost rows HTML
enrich_row = ""
if est["enrich_calls"] > 0:
    enrich_row = f"""
    <div class="cost-row">
        <span class="cost-label">Place Details enrichment
            <span class="cost-detail">{est['enrich_calls']:,} stores × ${PRICE_DETAILS_PER_CALL}</span>
        </span>
        <span class="cost-value">${est['enrich_cost']:.2f}</span>
    </div>"""

# ── Area too large — block the run ───────────────────────────────────────────
if est["area_km2"] > 100000:
    st.markdown(f"""
    <div class="preflight-card preflight-red">
        <div class="preflight-title">🔴 Area too large to scrape effectively</div>
        <div style="color:#B71C1C;font-size:0.9rem;margin-bottom:0.8rem">
            Your selected coverage area is <strong>~{est['area_km2']:,} km²</strong> —
            this is a full country or large region. Scraping this area would take
            <strong>{time_display}</strong> and cost approximately
            <strong>${est['total_cost']:.2f}</strong> in API credits.
        </div>
        <div class="suggestion-box">
            💡 Go back to <strong>Configure</strong> and add specific cities or districts
            (e.g. Muscat, Salalah) instead of selecting the whole country.
            Each city typically takes 2–5 minutes and costs under $2.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # ── Normal pre-flight card ────────────────────────────────────────────────
    # Build HTML using variables to avoid f-string quote conflicts
    scrape_detail   = f"{est['scrape_calls']:,} calls x ${PRICE_NEARBY_PER_CALL} · {est['n_tiles']} tiles · {est['n_categories']} categories · tile radius {radius_label}"
    geocode_detail  = f"{est['geocode_calls']} stores x ${PRICE_GEOCODE_PER_CALL}"
    total_summary   = f"${est['total_cost']:.2f} · {est['total_calls']:,} API calls · {time_display}"
    area_summary    = f"~{est['area_km2']:,} km² · ~{est['estimated_universe']:,} stores estimated · {est['n_portfolio']} portfolio stores"
    scrape_cost_str = f"${est['scrape_cost']:.2f}"
    geocode_cost_str= f"${est['geocode_cost']:.2f}"
    total_cost_str  = f"${est['total_cost']:.2f}"
    enrich_cost_str = f"${est['enrich_cost']:.2f}"
    enrich_detail   = f"{est['enrich_calls']:,} stores x ${PRICE_DETAILS_PER_CALL}"

    enrich_html = ""
    if est["enrich_calls"] > 0:
        enrich_html = f"""
        <div class="cost-row">
            <span class="cost-label">Place Details enrichment
                <span class="cost-detail">{enrich_detail}</span>
            </span>
            <span class="cost-value">{enrich_cost_str}</span>
        </div>"""

    suggestions_html = "".join(
        f'<div class="suggestion-box">💡 {s}</div>' for s in est["suggestions"]
    )

    html = f"""
    <div class="preflight-card {colour_class}">
        <div class="preflight-title">{est['icon']} {est['label']}</div>
        <div class="main-stats">
            <div class="main-stat-box">
                <div class="main-stat-val">{time_display}</div>
                <div class="main-stat-label">Total estimated time</div>
            </div>
            <div class="main-stat-box">
                <div class="main-stat-val">{total_cost_str}</div>
                <div class="main-stat-label">Total estimated API cost</div>
            </div>
        </div>
        <div class="cost-breakdown">
            <div class="cost-row">
                <span class="cost-label">Google Places scraping
                    <span class="cost-detail">{scrape_detail}</span>
                </span>
                <span class="cost-value">{scrape_cost_str}</span>
            </div>
            <div class="cost-row">
                <span class="cost-label">Geocoding portfolio
                    <span class="cost-detail">{geocode_detail}</span>
                </span>
                <span class="cost-value">{geocode_cost_str}</span>
            </div>
            {enrich_html}
            <div class="cost-row">
                <span class="cost-label">Total</span>
                <span class="cost-total">{total_summary}</span>
            </div>
        </div>
        <div style="font-size:0.8rem;color:#6B7280;margin-bottom:0.6rem">
            Coverage area: {area_summary}
        </div>
        {suggestions_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

st.caption("💡 Google provides $200 free credit per month — most single-market runs are well within this limit.")

if est["colour"] != "green":
    st.markdown("""
**To reduce time and cost — go back to Configure and:**
- Select specific cities or districts instead of a full country or region
- Reduce scraping categories to 2-3 most important
- Or use **Dry Run** below to test without using any credits
    """)

st.markdown("---")

# ── STEP 4: RUN ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">4. Run the agent</div>', unsafe_allow_html=True)

dry_run = st.checkbox(
    "Dry run mode — no API calls, generates sample data for testing",
    value=True
)
if not dry_run:
    st.warning(
        f"⚠️ Live mode will call Google APIs — estimated **{time_display}** "
        f"and **${est['total_cost']:.2f}** in API costs."
    )

if st.button("🚀 Run Coverage Agent", type="primary"):
    status = st.empty()
    bar    = st.progress(0)
    weights    = cfg["weights"]
    thresholds = cfg["thresholds"]
    cat_tiers  = cfg["category_tiers"]

    # ── DRY RUN ───────────────────────────────────────────────────────────────
    if dry_run:
        status.info("Generating sample data...")
        pf   = st.session_state.get("portfolio_df")
        base = pf.to_dict("records") if pf is not None else [
            {"store_id":"S001","store_name":"Carrefour Express","address":"Qurum","city":"Muscat","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
            {"store_id":"S002","store_name":"Lulu Hypermarket","address":"Al Khuwair","city":"Muscat","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
        ]
        all_stores = []
        prefixes = ["Metro","City","Quick","Fresh","Express","Central","Star","Royal","Golden","Prime","Al","New"]
        phone_samples = ["+968 2234 5678","+968 9876 5432","+968 2456 7890","","","+968 2345 6789"]
        hours_samples = [
            "Mon-Sat: 8:00 AM - 10:00 PM | Sun: 9:00 AM - 9:00 PM",
            "Daily: 7:00 AM - 11:00 PM",
            "Mon-Fri: 9:00 AM - 9:00 PM | Sat-Sun: 10:00 AM - 8:00 PM",
            "", "",
        ]

        for row in base:
            sc = random.randint(50,100)
            freq, cpm = assign_freq(sc, thresholds)
            all_stores.append({
                "store_id":row.get("store_id","S0"),"store_name":row.get("store_name","Store"),
                "address":row.get("address",""),"city":row.get("city",""),
                "category":row.get("category",cfg["categories"][0] if cfg["categories"] else "supermarket"),
                "lat":cfg["lat_min"]+random.uniform(0.01,max(cfg["lat_max"]-cfg["lat_min"]-0.01,0.02)),
                "lng":cfg["lng_min"]+random.uniform(0.01,max(cfg["lng_max"]-cfg["lng_min"]-0.01,0.02)),
                "rating":round(random.uniform(3.5,4.9),1),"review_count":random.randint(100,3000),
                "annual_sales_usd":float(row.get("annual_sales_usd",0)),"lines_per_store":int(row.get("lines_per_store",0)),
                "covered":True,"source":"portfolio","score":sc,"visit_frequency":freq,
                "calls_per_month":cpm,"rep_id":random.randint(1,cfg["rep_count"]),"coverage_status":"covered",
                "phone":random.choice(phone_samples),"opening_hours":random.choice(hours_samples),
                "website":"","place_id":f"dry_place_{row.get('store_id','S0')}",
            })
        for i in range(60):
            cat = random.choice(cfg["categories"])
            sc  = random.randint(10,95)
            freq, cpm = assign_freq(sc, thresholds)
            all_stores.append({
                "store_id":f"G{i:03d}","store_name":f"{random.choice(prefixes)} {cat.replace('_',' ').title()} {i+1}",
                "address":f"{random.randint(1,200)} Sample Street","city":cfg.get("city",""),
                "category":cat,
                "lat":cfg["lat_min"]+random.uniform(0.01,max(cfg["lat_max"]-cfg["lat_min"]-0.01,0.02)),
                "lng":cfg["lng_min"]+random.uniform(0.01,max(cfg["lng_max"]-cfg["lng_min"]-0.01,0.02)),
                "rating":round(random.uniform(2.8,4.9),1),"review_count":random.randint(10,5000),
                "annual_sales_usd":0.0,"lines_per_store":0,
                "covered":False,"source":"scraped","score":sc,"visit_frequency":freq,
                "calls_per_month":cpm,
                "rep_id":random.randint(1,cfg["rep_count"]) if sc>=thresholds["monthly"] else 0,
                "coverage_status":"gap",
                "phone":random.choice(phone_samples) if enrich_scope != "none" else "",
                "opening_hours":random.choice(hours_samples) if enrich_scope != "none" else "",
                "website":"","place_id":f"dry_gap_{i:03d}",
            })
        bar.progress(100)
        gap_stores = sorted([s for s in all_stores if s["coverage_status"]=="gap"],key=lambda x:x["score"],reverse=True)
        covered_n  = sum(1 for s in all_stores if s["covered"])
        st.session_state["run_results"] = {
            "all_stores":all_stores,"gap_stores":gap_stores,
            "coverage_rate_before":round(len(base)/max(len(all_stores),1)*100,1),
            "coverage_rate_after":round(covered_n/max(len(all_stores),1)*100,1),
            "portfolio":[s for s in all_stores if s["source"]=="portfolio"],
            "universe":[s for s in all_stores if s["source"]=="scraped"],
        }
        st.session_state["last_market"] = cfg["market_name"]
        status.success(f"✅ Dry run complete — {len(all_stores)} stores generated. Open Results or Routes in the sidebar.")

    # ── LIVE RUN ──────────────────────────────────────────────────────────────
    else:
        api_key   = get_api_key()
        pf        = st.session_state.get("portfolio_df")
        portfolio = pf.to_dict("records") if pf is not None else []
        for s in portfolio:
            s.update({"covered":True,"source":"portfolio","lat":None,"lng":None,
                      "rating":0.0,"review_count":0,"phone":"","opening_hours":"","website":""})
            if "category" not in s: s["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"

        radius_m, _ = smart_tile_radius(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"])
        centres     = grid_centres(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"],radius_m)
        total_steps = 7 if enrich_scope != "none" else 6
        run_start   = time.time()

        # Stage 1: Geocode
        status.info(f"Stage 1/{total_steps} — Geocoding {len(portfolio)} portfolio stores...")
        bar.progress(5)
        for s in portfolio:
            lat,lng = geocode_store(s.get("address",""),s.get("city",""),api_key)
            s["lat"],s["lng"] = lat,lng
            time.sleep(0.05)
        bar.progress(15)

        # Stage 2: Scrape
        seen_ids    = set()
        universe    = []
        total_tiles = max(len(centres)*len(cfg["categories"]),1)
        done_tiles  = 0
        scrape_start = time.time()

        for cat in cfg["categories"]:
            for lat,lng in centres:
                token = None
                while True:
                    data = fetch_places(lat,lng,radius_m,cat,api_key,token)
                    for place in data.get("results",[]):
                        pid = place.get("place_id","")
                        if pid in seen_ids: continue
                        seen_ids.add(pid)
                        loc = place.get("geometry",{}).get("location",{})
                        universe.append({
                            "store_id":pid,"place_id":pid,
                            "store_name":place.get("name",""),
                            "address":place.get("vicinity",""),"city":cfg.get("city",""),
                            "lat":loc.get("lat"),"lng":loc.get("lng"),
                            "rating":float(place.get("rating",0) or 0),
                            "review_count":int(place.get("user_ratings_total",0) or 0),
                            "category":cat,"annual_sales_usd":0.0,"lines_per_store":0,
                            "covered":False,"source":"scraped",
                            "phone":"","opening_hours":"","website":"",
                        })
                    token = data.get("next_page_token")
                    if not token: break
                done_tiles += 1
                pct = 15 + int(done_tiles/total_tiles*30)
                elapsed = time.time()-scrape_start
                rem     = (elapsed/done_tiles)*(total_tiles-done_tiles) if done_tiles>0 else 0
                status.info(f"Stage 2/{total_steps} — Scraping {cat}... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores | ⏱ {fmt_time(rem).replace('~','')} remaining")
                bar.progress(pct)

        status.info(f"Stage 2/{total_steps} — Found {len(universe):,} unique stores")
        bar.progress(45)

        # Stage 3: Score
        status.info(f"Stage 3/{total_steps} — Scoring all stores...")
        all_stores = portfolio + universe
        max_rev    = max((s.get("review_count",0) for s in all_stores),default=1) or 1
        max_sales  = max((s.get("annual_sales_usd",0) for s in portfolio),default=1) or 1
        max_lines  = max((s.get("lines_per_store",0) for s in portfolio),default=1) or 1
        for s in all_stores:
            tier  = cat_tiers.get(s.get("category",""),4)
            cat_n = TIER_MULT.get(tier,0.30)
            r_n   = (s.get("rating",0) or 0)/5
            rv_n  = math.log1p(s.get("review_count",0) or 0)/math.log1p(max_rev)
            sal_n = (s.get("annual_sales_usd",0) or 0)/max_sales if s.get("covered") else 0.0
            lin_n = (s.get("lines_per_store",0) or 0)/max_lines if s.get("covered") else 0.0
            s["score"] = min(100,round((r_n*weights["rating"]+rv_n*weights["reviews"]+cat_n*weights["category"]+sal_n*weights["sales"]+lin_n*weights["lines"])*100))
        bar.progress(55)

        # Stage 4: Gap match
        status.info(f"Stage 4/{total_steps} — Matching coverage gaps...")
        covered_p = [s for s in portfolio if s.get("lat") and s.get("lng")]
        for u in universe:
            if not (u.get("lat") and u.get("lng")): u["coverage_status"]="no_coords"; continue
            matched = any(haversine_m(u["lat"],u["lng"],p["lat"],p["lng"])<=50 for p in covered_p)
            u["covered"]         = matched
            u["coverage_status"] = "covered" if matched else "gap"
        for p in portfolio: p["coverage_status"] = "covered"
        bar.progress(65)

        # Stage 5: Frequency
        status.info(f"Stage 5/{total_steps} — Assigning visit frequencies...")
        for s in all_stores:
            freq,cpm = assign_freq(s.get("score",0),thresholds)
            s["visit_frequency"] = freq
            s["calls_per_month"] = cpm
        bar.progress(72)

        # Stage 6: Routes
        status.info(f"Stage 6/{total_steps} — Allocating rep routes...")
        priority = [s for s in all_stores if s.get("score",0)>=thresholds["monthly"] and s.get("lat") and s.get("lng")]
        if priority:
            pts    = [(s["lat"],s["lng"]) for s in priority]
            labels = kmeans_simple(pts,cfg["rep_count"])
            for s,lbl in zip(priority,labels): s["rep_id"] = int(lbl)+1
        for s in all_stores:
            if "rep_id" not in s: s["rep_id"] = 0
        bar.progress(80)

        # Stage 7: Enrichment (optional)
        if enrich_scope != "none":
            status.info(f"Stage 7/{total_steps} — Enriching stores with phone & opening hours...")

            # Select candidates based on scope
            if enrich_scope == "top_n":
                candidates = sorted(
                    [s for s in all_stores if s.get("place_id","")],
                    key=lambda x: x.get("score",0), reverse=True
                )[:enrich_count]
            elif enrich_scope == "gaps_only":
                candidates = sorted(
                    [s for s in all_stores if s.get("coverage_status")=="gap" and s.get("place_id","")],
                    key=lambda x: x.get("score",0), reverse=True
                )[:enrich_count]
            else:  # all
                candidates = [s for s in all_stores if s.get("place_id","")][:enrich_count]

            enriched = 0
            failed   = 0
            enrich_start = time.time()

            for i, store in enumerate(candidates):
                result = fetch_place_details(store.get("place_id",""), api_key)
                if result:
                    store["phone"]   = result.get("formatted_phone_number","")
                    store["website"] = result.get("website","")
                    oh = result.get("opening_hours",{})
                    wt = oh.get("weekday_text",[])
                    store["opening_hours"] = " | ".join(wt) if wt else ""
                    if result.get("formatted_address"):
                        store["full_address"] = result["formatted_address"]
                    enriched += 1
                else:
                    failed += 1

                pct = 80 + int((i+1)/max(len(candidates),1)*17)
                rem = (time.time()-enrich_start)/(i+1)*(len(candidates)-i-1) if i>0 else 0
                status.info(
                    f"Stage 7/{total_steps} — Enriching... {i+1}/{len(candidates)} | "
                    f"{enriched} updated | ⏱ {fmt_time(rem).replace('~','')} remaining"
                )
                bar.progress(min(pct,97))
                time.sleep(0.1)

        # Package results
        gap_stores  = sorted([s for s in universe if s.get("coverage_status")=="gap"],key=lambda x:x.get("score",0),reverse=True)
        covered_n   = sum(1 for s in all_stores if s.get("covered"))
        actual_time = fmt_time(time.time()-run_start).replace("~","")
        actual_cost = (
            round(len(portfolio)*PRICE_GEOCODE_PER_CALL +
                  len(universe)/15*PRICE_NEARBY_PER_CALL +
                  (enriched if enrich_scope != "none" else 0)*PRICE_DETAILS_PER_CALL, 2)
        )

        st.session_state["run_results"] = {
            "all_stores":all_stores,"gap_stores":gap_stores,
            "coverage_rate_before":round(len(covered_p)/max(len(universe),1)*100,1),
            "coverage_rate_after":round(covered_n/max(len(all_stores),1)*100,1),
            "portfolio":portfolio,"universe":universe,
        }
        st.session_state["last_market"] = cfg["market_name"]
        bar.progress(100)

        enrich_msg = f" · {enriched} stores enriched with phone & hours" if enrich_scope != "none" else ""
        status.success(
            f"✅ Pipeline complete in {actual_time} · actual cost ~${actual_cost:.2f} · "
            f"{len(all_stores):,} stores scored · {len(gap_stores):,} gaps found{enrich_msg}. "
            f"Open Results in the sidebar."
        )
