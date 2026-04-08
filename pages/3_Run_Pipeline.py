import streamlit as st
import pandas as pd
import time
import math
import requests
import random
import datetime

st.set_page_config(page_title="Run Pipeline - Coverage Tool", page_icon=" ", layout="wide")

st.markdown("""
<style>

/* ── Sidebar navy blue ── */
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #FFFFFF !important; }
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

st.markdown('<div class="page-header"><h2>  Run Pipeline</h2></div>', unsafe_allow_html=True)

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

# ── Checkpoint resume banner ──────────────────────────────────────────────────
_ckpt = st.session_state.get("scrape_checkpoint")
if _ckpt and _ckpt.get("done_tiles",0) < _ckpt.get("total_tiles",1):
    _ckpt_n = len(_ckpt.get("universe",[]))
    _ckpt_pct = round(_ckpt.get("done_tiles",0) / max(_ckpt.get("total_tiles",1),1) * 100)
    st.warning(
        f"  **Incomplete scrape found** — {_ckpt.get('market','')} · "
        f"**{_ckpt_n:,} stores** · **{_ckpt.get('done_tiles',0)}/{_ckpt.get('total_tiles',1)} tiles** ({_ckpt_pct}%) completed."
    )
    _cc1, _cc2 = st.columns(2)
    with _cc1:
        st.download_button(
            f"  Download partial universe ({_ckpt_n:,} stores)",
            pd.DataFrame(_ckpt.get("universe",[])).to_csv(index=False),
            f"{_ckpt.get('market','market')}_partial_universe.csv",
            "text/csv", key="dl_checkpoint"
        )
    with _cc2:
        if st.button("  Clear checkpoint", key="clear_checkpoint"):
            del st.session_state["scrape_checkpoint"]
            st.rerun()
    st.markdown("---")

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

    # Calibrate estimates based on area size and tile radius
    # Key insight: in large sparse areas most tiles return 0 results
    # so effective avg_pages << 1. Only ~20% of tiles in rural areas have stores.
    lat_span = abs(cfg["lat_max"] - cfg["lat_min"])
    lng_span = abs(cfg["lng_max"] - cfg["lng_min"])
    mid_lat  = (cfg["lat_min"] + cfg["lat_max"]) / 2
    area_km2 = lat_span * 111 * lng_span * 111 * math.cos(math.radians(mid_lat))

    if area_km2 > 5000:      # large governorate / region — very sparse
        avg_pages       = 0.25  # ~25% of tiles return any results
        stores_per_tile = 6
    elif area_km2 > 1000:    # medium region
        avg_pages       = 0.6
        stores_per_tile = 10
    elif area_km2 > 200:     # large city
        avg_pages       = 1.2
        stores_per_tile = 14
    else:                    # city / district — dense
        avg_pages       = 1.8
        stores_per_tile = 18

    # Scraping
    scrape_calls      = round(n_tiles * n_categories * avg_pages)
    scrape_cost       = scrape_calls * PRICE_NEARBY_PER_CALL
    scrape_time       = scrape_calls * 0.25 + n_tiles * n_categories * max(avg_pages-1,0) * 2

    # Geocoding



    geocode_calls     = n_portfolio
    geocode_cost      = geocode_calls * PRICE_GEOCODE_PER_CALL
    geocode_time      = geocode_calls * 0.1

    # Enrichment
    estimated_universe = n_tiles * n_categories * stores_per_tile
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
        colour, icon, label = "green", " ", "Quick run — ready to go"
    elif total_minutes < 15:
        colour, icon, label = "amber", " ", "Moderate run — consider narrowing if needed"
    else:
        colour, icon, label = "red", " ", "Long run — recommend selecting specific cities"

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

# Auto-detect sub-city and region column names
DISTRICT_COLS = ["district","area","neighbourhood","neighborhood","bairro","zone","suburb","quarter"]
REGION_COLS   = ["region","state","governorate","province","county","wilaya","emirate","prefecture"]

def _get_location_field(store, col_list):
    """Return first non-empty value from a list of possible column names."""
    for col in col_list:
        v = store.get(col,"")
        if v and str(v).strip() and str(v).strip().lower() not in ("nan","none",""):
            return str(v).strip()
    return ""

def geocode_store(address, city, api_key, district="", region="", country=""):
    """Geocode using address + optional district, region and country for better accuracy.
    Including country is critical to avoid geocoding to wrong countries."""
    try:
        parts = [p for p in [address, district, city, region, country] if p and str(p).strip()]
        full_address = ", ".join(parts)
        r = requests.get(GEOCODE_URL,



            params={"address": full_address, "key": api_key}, timeout=10)
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

def travel_time_minutes(lat1, lng1, lat2, lng2, avg_speed_kmh=30):
    """Straight-line travel time in minutes between two GPS points."""
    dist_km = haversine_m(lat1, lng1, lat2, lng2) / 1000
    return (dist_km / avg_speed_kmh) * 60

def calculate_rep_time_budget(stores_in_route, avg_speed_kmh=30):
    """
    Calculate total time needed per month for a rep covering a set of stores.
    Returns total_minutes_per_month.
    Time = sum(visit_duration × visits_per_month) + sum(travel_time × visits_per_month)
    Stores are visited in score order (highest first = most efficient routing proxy).
    """
    if not stores_in_route:
        return 0.0

    # Sort by score descending for visit order
    ordered = sorted(stores_in_route, key=lambda x: x.get("score",0), reverse=True)

    visit_time = sum(
        s.get("visit_duration_min", 25) * s.get("visits_per_month", 1)
        for s in ordered
    )

    # Travel time — cumulative between consecutive stores each visit
    travel_time = 0.0
    for i in range(1, len(ordered)):
        s_prev = ordered[i-1]
        s_curr = ordered[i]
        if all(k in s_prev and k in s_curr for k in ["lat","lng"]):
            t = travel_time_minutes(
                s_prev["lat"], s_prev["lng"],
                s_curr["lat"], s_curr["lng"],
                avg_speed_kmh



            )
            # multiply by average visits (use min of the two stores' visits)
            avg_visits = (s_prev.get("visits_per_month",1) + s_curr.get("visits_per_month",1)) / 2
            travel_time += t * avg_visits

    return visit_time + travel_time

def recommended_reps_time_based(priority_stores, daily_minutes=480, working_days=22, avg_speed_kmh=30):
    """
    Calculate recommended rep count including geographic travel time estimate.
    Uses visits_per_month (pre-route) always — plan_visits is only reliable post-route
    and at that point we use it separately for utilisation reporting.
    Returns (recommended_reps, total_minutes_needed_per_month, minutes_per_rep_per_month).
    """
    if not priority_stores:
        return 1, 0.0, 0.0

    monthly_capacity = daily_minutes * working_days
    n_stores = len(priority_stores)

    # Always use visits_per_month for rep count estimation
    # plan_visits under-counts because it reflects stores already cut by budget
    # — that creates a circular dependency (fewer reps → more cuts → fewer plan_visits → fewer reps)
    total_visit_time = sum(
        s.get("visit_duration_min", 25) * s.get("visits_per_month", 1)
        for s in priority_stores
    )

    # Estimate travel time based on geographic spread of stores
    geo = [s for s in priority_stores if s.get("lat") and s.get("lng")]
    if len(geo) > 1:
        lat_span = max(s["lat"] for s in geo) - min(s["lat"] for s in geo)
        lng_span = max(s["lng"] for s in geo) - min(s["lng"] for s in geo)
        mid_lat  = sum(s["lat"] for s in geo) / len(geo)
        area_km2 = lat_span * 111 * lng_span * 111 * math.cos(math.radians(mid_lat))
        # Average inter-store distance ~ sqrt(area / stores) × 0.7 (empirical factor)
        avg_dist_km    = math.sqrt(max(area_km2, 1) / max(n_stores, 1)) * 0.7
        avg_travel_min = (avg_dist_km / max(avg_speed_kmh, 1)) * 60
        total_visits   = sum(s.get("visits_per_month", 1) for s in priority_stores)
        total_travel   = avg_travel_min * total_visits
    else:
        total_travel = total_visit_time * 0.2  # 20% overhead if no geo data

    total_minutes = total_visit_time + total_travel
    rec_reps = max(1, math.ceil(total_minutes / monthly_capacity))
    return rec_reps, round(total_minutes), round(monthly_capacity)



def assign_size_tier(store, category_percentiles, visit_benchmarks, size_percentiles):
    """
    Assign size tier (Large/Medium/Small) based on score percentile within category.
    Visits/month can be any value including decimals (0.5 = every 2mo, 0.33 = every 3mo).
    Plan period is determined by the minimum frequency across all tiers.
    Returns (size_tier, visits_per_month, visit_duration_min).
    """
    cat       = store.get("category","")
    score     = store.get("score", 0)
    cat_ranks = category_percentiles.get(cat, [])
    n         = len(cat_ranks)

    if n == 0:
        pct = 50.0
    else:
        rank = sum(1 for s in cat_ranks if s <= score)
        pct  = (rank / n) * 100

    large_pct  = size_percentiles.get("large_pct",  20)
    medium_pct = size_percentiles.get("medium_pct", 40)

    # top X% = Large, next Y% = Medium, bottom = Small
    if pct >= (100 - large_pct):
        tier = "Large"
    elif pct >= (100 - large_pct - medium_pct):
        tier = "Medium"
    else:
        tier = "Small"

    # Get visit benchmarks for this category
    bench = visit_benchmarks.get(cat, visit_benchmarks.get("default", {
        "large_visits":4,"large_duration":40,
        "medium_visits":2,"medium_duration":25,
        "small_visits":1,"small_duration":15,
    }))

    if tier == "Large":
        visits   = float(bench.get("large_visits",  4))
        duration = int(bench.get("large_duration",  40))
    elif tier == "Medium":
        visits   = float(bench.get("medium_visits", 2))
        duration = int(bench.get("medium_duration", 25))
    else:
        visits   = float(bench.get("small_visits",  1))
        duration = int(bench.get("small_duration",  15))



    return tier, visits, duration

def _map_biz_status(raw):
    """Map raw Google business_status to clean display value."""
    m = {
        "OPERATIONAL":        "Active",
        "CLOSED_PERMANENTLY": "Closed",
        "CLOSED_TEMPORARILY": "Temporarily Closed",
    }
    return m.get(str(raw).upper().strip(), "Active" if not raw else str(raw).title())

def clean_store_name(name):
    """Clean store name — fix encoding issues, filter pure Arabic, remove junk.
    Returns empty string for pure Arabic names (no Latin chars) so they are skipped.
    Handles mojibake (double-encoded UTF-8 appearing as Latin-1 garbage like Ù…Ø±ÙƒØ²)."""
    import re
    if not name: return ""
    # Fix mojibake: try to recover double-encoded UTF-8
    # e.g. Ù…Ø±ÙƒØ² is Arabic text encoded as Latin-1 instead of UTF-8
    try:
        fixed = name.encode("latin-1").decode("utf-8")
        name = fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass  # already correct encoding
    # Remove junk symbols
    name = re.sub(r'[|*#@~`^\\]+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # Skip pure Arabic names (no Latin characters at all)
    # These are either untransliterated local names or still-garbled encoding
    has_latin = any(c.isascii() and c.isalpha() for c in name)
    if not has_latin and name:
        return ""  # caller will skip empty names
    return name

def build_category_percentiles(stores):
    """Build a dict of category -> sorted list of scores for percentile ranking."""
    cat_scores = {}
    for s in stores:
        cat = s.get("category","")
        if cat not in cat_scores:
            cat_scores[cat] = []
        cat_scores[cat].append(s.get("score",0))
    # Sort each list
    for cat in cat_scores:
        cat_scores[cat].sort()



    return cat_scores

WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

def get_month_weekdays(year=None, month=None, month_index=None):
    """
    Returns dict: {weekday_name: [week_label, ...]} — e.g. {"Monday": ["Week 1","Week 3"]}
    Uses abstract week labels (Week 1-5) instead of real dates.
    month_index: 0-based index of month in plan (0=Month1, 1=Month2 etc)
    """
    result = {d: [] for d in WEEKDAYS}
    # Each month has 4 weekday occurrences (sometimes 5 for first/last day)
    # Use standard 4 occurrences: Week 1, Week 2, Week 3, Week 4
    for day in WEEKDAYS:
        result[day] = ["Week 1", "Week 2", "Week 3", "Week 4"]
    return result

def build_daily_routes(rep_stores, year=None, month=None, daily_minutes=480, avg_speed_kmh=30, city_lat=0, city_lng=0):
    """
    Assign each store to a fixed day of the week and build daily visit sequences.
    Uses abstract week labels (Week 1-4) instead of real calendar dates.

    Returns list of store dicts enriched with:
        assigned_day        — "Monday" etc
        day_visit_order     — position within that day's route
        day_travel_time_min — cumulative travel time for this day
    """
    if not rep_stores:
        return []

    month_days = get_month_weekdays()

    # ── Step 1: Cluster rep stores into 5 geographic day-groups ──────────────
    geo_stores = [s for s in rep_stores if s.get("lat") and s.get("lng")]
    if not geo_stores:
        # No geo data — assign round-robin
        for i, s in enumerate(rep_stores):
            s["assigned_day"] = WEEKDAYS[i % 5]
        geo_stores = rep_stores

    n_days = min(5, max(1, len(geo_stores)))
    if n_days < 2:
        for s in geo_stores:
            s["assigned_day"] = WEEKDAYS[0]
    else:
        try:



            pts    = [(s["lat"], s["lng"]) for s in geo_stores]
            labels = kmeans_simple(pts, n_days)
            for s, lbl in zip(geo_stores, labels):
                s["assigned_day"] = WEEKDAYS[int(lbl) % 5]
        except Exception:
            # Fallback to round-robin if clustering fails
            for i, s in enumerate(geo_stores):
                s["assigned_day"] = WEEKDAYS[i % 5]

    # ── Step 2: Within each day, sort by nearest neighbour from city ─────────
    day_groups = {d: [] for d in WEEKDAYS}
    for s in geo_stores:
        day_groups[s["assigned_day"]].append(s)

    for day, stores in day_groups.items():
        if not stores:
            continue
        # Nearest neighbour from city centre
        ordered  = []
        remaining = stores[:]
        cur_lat, cur_lng = city_lat, city_lng
        while remaining:
            nearest = min(remaining, key=lambda s: haversine_m(cur_lat, cur_lng, s.get("lat",cur_lat), s.get("lng",cur_lng)))
            ordered.append(nearest)
            cur_lat, cur_lng = nearest.get("lat",cur_lat), nearest.get("lng",cur_lng)
            remaining.remove(nearest)
        for i, s in enumerate(ordered):
            s["day_visit_order"] = i + 1
        day_groups[day] = ordered

    # ── Step 3: Enforce daily time budget — redistribute overflow stores ─────
    # For each day: walk stores in visit order, accumulate time.
    # If a store doesn't fit on this day, try to move it to the least-loaded
    # other day that has remaining capacity. Only drop if no day can fit it.
    def day_used_time(stores_list):
        t = 0.0
        prev_lat2, prev_lng2 = city_lat, city_lng
        for s2 in stores_list:
            t += s2.get("visit_duration_min", 25)
            if s2.get("lat") and s2.get("lng"):
                t += travel_time_minutes(prev_lat2, prev_lng2, s2["lat"], s2["lng"], avg_speed_kmh)
                prev_lat2, prev_lng2 = s2["lat"], s2["lng"]
        return t

    # Two-pass: first pass fills each day to budget, overflow goes to a pool
    overflow_pool = []
    for day in list(day_groups.keys()):



        stores = day_groups[day]
        if not stores:
            continue
        kept       = []
        cumulative = 0.0
        prev_lat, prev_lng = city_lat, city_lng
        for s in stores:
            visit_t  = s.get("visit_duration_min", 25)
            travel_t = 0.0
            if s.get("lat") and s.get("lng"):
                travel_t = travel_time_minutes(prev_lat, prev_lng, s["lat"], s["lng"], avg_speed_kmh)
            total_t = visit_t + travel_t
            if cumulative + total_t <= daily_minutes:
                kept.append(s)
                cumulative += total_t
                if s.get("lat") and s.get("lng"):
                    prev_lat, prev_lng = s["lat"], s["lng"]
            else:
                overflow_pool.append(s)
        day_groups[day] = kept

    # Second pass: try to fit overflow stores into days that still have capacity
    # Sort overflow by score descending — highest priority first
    overflow_pool.sort(key=lambda x: x.get("score", 0), reverse=True)
    for s in overflow_pool:
        visit_t = s.get("visit_duration_min", 25)
        # Find the day with most remaining capacity
        best_day = None
        best_remaining = -1
        for day in WEEKDAYS:
            used      = day_used_time(day_groups[day])
            remaining = daily_minutes - used
            if remaining >= visit_t and remaining > best_remaining:
                best_remaining = remaining
                best_day = day
        if best_day:
            day_groups[best_day].append(s)
            s["assigned_day"] = best_day
            # Re-sort this day by nearest neighbour
            if len(day_groups[best_day]) > 1:
                ordered  = []
                remaining_s = day_groups[best_day][:]
                cur_lat2, cur_lng2 = city_lat, city_lng
                while remaining_s:
                    nearest = min(remaining_s, key=lambda x: haversine_m(cur_lat2, cur_lng2, x.get("lat",cur_lat2), x.get("lng",cur_lng2)))
                    ordered.append(nearest)
                    cur_lat2, cur_lng2 = nearest.get("lat",cur_lat2), nearest.get("lng",cur_lng2)



                    remaining_s.remove(nearest)
                for i2, s2 in enumerate(ordered):
                    s2["day_visit_order"] = i2 + 1
                day_groups[best_day] = ordered
        else:
            # No day can fit this store — drop it from plan
            s["assigned_day"]    = ""
            s["day_visit_order"] = 0

    # ── Step 4: Build visit_dates from calendar ───────────────────────────────
    for day, stores in day_groups.items():
        occurrences = month_days.get(day, [])  # list of actual dates
        for s in stores:
            vpm = s.get("visits_per_month", 1)
            if vpm >= len(occurrences):
                # Visit on every occurrence of this day
                dates = occurrences
            elif vpm == 2:
                # Week 1 and Week 3 occurrences
                dates = occurrences[0:1] + (occurrences[2:3] if len(occurrences) > 2 else occurrences[-1:])
            else:
                # Week 2 occurrence (middle of month)
                mid = len(occurrences) // 2
                dates = [occurrences[mid]]
            s["visit_dates"] = [d.strftime("%b %d") for d in dates]
            s["visit_dates_full"] = [d.strftime("%Y-%m-%d") for d in dates]
            s["n_visits_this_month"] = len(dates)

    # ── Flatten back ──────────────────────────────────────────────────────────
    all_assigned = []
    for stores in day_groups.values():
        all_assigned.extend(stores)

    # Any store without assigned_day (no geo) — assign to Friday
    for s in rep_stores:
        if "assigned_day" not in s:
            s["assigned_day"]      = "Friday"
            s["day_visit_order"]   = 99
            s["visit_dates"]       = []
            s["n_visits_this_month"] = s.get("visits_per_month",1)

    return rep_stores

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
    icons  = {"ok":" ","error":" ","warn":" "}
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
        <div style="font-weight:700;color:#B71C1C;margin-bottom:6px">  No Google API key found</div>
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
        do_check = st.button("  Check APIs", key="quick_check")

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
                '  To fix: go to <a href="https://console.cloud.google.com/apis/library" target="_blank">'
                'console.cloud.google.com → APIs &amp; Services → Library</a> → '
                'search the API name → click Enable → come back and click Check APIs again.'
                '</div>'
            )
        st.markdown(html_out, unsafe_allow_html=True)
        if all_ok:
            st.success("  All APIs active — pipeline ready to run")
    else:
        st.info("Click **Check APIs** above to verify everything is enabled before running.")

st.markdown("---")



# ── STEP 1: PORTFOLIO UPLOAD ──────────────────────────────────────────────────
st.markdown('<div class="section-title">1. Portfolio CSV</div>', unsafe_allow_html=True)
st.markdown("Required: `store_name`, `address`, `city` | Optional: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`")

portfolio_df = st.session_state.get("portfolio_df")
if portfolio_df is not None:
    st.success(f"  Using portfolio from Configure — {len(portfolio_df)} stores")
    st.dataframe(portfolio_df.head(3), use_container_width=True)
    if st.checkbox("Upload a different file"):
        portfolio_df = None
        st.session_state["portfolio_df"] = None

if portfolio_df is None:
    up = st.file_uploader("Upload portfolio CSV", type=["csv"])
    if up:
        try:
            # Try multiple encodings — handles UTF-8, Latin-1, Arabic Windows, etc.
            df = None
            for _enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252", "cp1256", "iso-8859-1"]:
                try:
                    up.seek(0)
                    df = pd.read_csv(up, encoding=_enc)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            if df is None:
                st.error("Could not read the file — unsupported encoding. Please save as UTF-8 CSV and try again.")
                st.stop()
            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            # Drop completely blank rows (empty Excel rows at end of file)
            df = df.dropna(subset=["store_name","address","city"], how="all").reset_index(drop=True)
            df = df[df["store_name"].fillna("").str.strip() != ""].reset_index(drop=True)
            # Ensure lat/lng columns exist (may be empty)
            if "lat" not in df.columns: df["lat"] = None
            if "lng" not in df.columns: df["lng"] = None
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
                st.success(f"  Loaded {len(df)} stores")



                st.dataframe(df.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Qurum","city":"Muscat","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Lulu Hypermarket","address":"Al Khuwair","city":"Muscat","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
])
st.download_button("  Download sample CSV", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")

# ── STEP 2: MARKET UNIVERSE SCRAPE ───────────────────────────────────────────
st.markdown('<div class="section-title">2. Market universe scrape</div>', unsafe_allow_html=True)

_scope_cities   = cfg.get("cities", [])
_scope_regions  = cfg.get("regions", [])
_scope_name     = cfg.get("city", cfg.get("market_name","this market"))
_scope_cats     = cfg.get("categories", [])
_scope_label    = ", ".join(_scope_cities) if _scope_cities else (", ".join(_scope_regions) if _scope_regions else _scope_name)

st.info(
    f"**Scope:** {_scope_label}  ·  "
    f"**Categories:** {', '.join(_scope_cats)}  ·  "
    f"**Bounding box:** {cfg['lat_min']:.3f},{cfg['lng_min']:.3f} → {cfg['lat_max']:.3f},{cfg['lng_max']:.3f}"
)
st.caption(
    "Scrape once, reuse forever — no API credits wasted on re-scraping the same area. "
    "Change the geography or categories in Configure to trigger a fresh scrape."
)

def _scrape_cache_key(cfg):
    cats = ",".join(sorted(cfg.get("categories", [])))
    return f"{cfg['lat_min']:.4f},{cfg['lat_max']:.4f},{cfg['lng_min']:.4f},{cfg['lng_max']:.4f}|{cats}"

_cache_key   = _scrape_cache_key(cfg)
_saved_cache = st.session_state.get("universe_cache", {})
_cached      = _saved_cache.get(_cache_key)

if _cached:
    _n      = len(_cached["universe"])
    _when   = _cached.get("scraped_at", "unknown time")
    st.success(
        f"  Cached universe ready: **{_n:,} stores** scraped for "
        f"**{_scope_label}** · scraped {_when} — pipeline will use this, no re-scraping needed."
    )
    col_r1, col_r2 = st.columns([2,1])



    with col_r1:
        _prev_df = pd.DataFrame(_cached["universe"])[
            ["store_name","city","category","rating","review_count","lat","lng"]
        ].head(5)
        st.dataframe(_prev_df, use_container_width=True, hide_index=True)
        _n_with_phone = sum(1 for s in _cached["universe"] if s.get("phone",""))
        st.caption(f"Quality: {_n:,} stores · {_n_with_phone:,} have phone numbers")
    with col_r2:
        if st.button("  Re-scrape (clear cache)", key="btn_rescrape"):
            del st.session_state["universe_cache"][_cache_key]
            st.rerun()
        _dl_df = pd.DataFrame(_cached["universe"])
        st.download_button(
            "  Download universe CSV",
            _dl_df.to_csv(index=False),
            f"{cfg.get('market_name','market')}_universe.csv",
            "text/csv", key="dl_universe_cache"
        )
        st.caption("  Download to preserve cache across sessions")

    with st.expander("  Replace cache by importing a CSV"):
        _imp_file2 = st.file_uploader("Upload universe CSV", type=["csv"], key="import_universe_csv_replace")
        if _imp_file2:
            try:
                _imp_df2 = pd.read_csv(_imp_file2)
                _imp_df2.columns = [c.strip().lower().replace(" ","_") for c in _imp_df2.columns]
                if "store_name" not in _imp_df2.columns or "lat" not in _imp_df2.columns:
                    st.error("File must have at least store_name and lat columns.")
                else:
                    for _col, _default in [
                        ("lng",0.0),("rating",0.0),("review_count",0),("price_level",0),
                        ("category","supermarket"),("source","scraped"),("covered",False),
                        ("phone",""),("opening_hours",""),("website",""),
                        ("annual_sales_usd",0.0),("lines_per_store",0),("poi_count",0),
                        ("place_id",""),("store_id",""),("address",""),("city",""),("business_status","Active"),
                    ]:
                        if _col not in _imp_df2.columns: _imp_df2[_col] = _default
                    if "universe_cache" not in st.session_state: st.session_state["universe_cache"] = {}
                    st.session_state["universe_cache"][_cache_key] = {
                        "universe":    _imp_df2.to_dict("records"),
                        "market_name": cfg.get("market_name",""),
                        "scraped_at":  f"Imported {datetime.datetime.now().strftime('%d %b %Y %H:%M')}",
                        "categories":  cfg.get("categories",[]),
                        "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
                    }
                    st.success(f"  Cache replaced with {len(_imp_df2):,} stores.")
                    st.rerun()



            except Exception as _ie2:
                st.error(f"Import failed: {_ie2}")
else:
    st.markdown("**Option A — Import a previously downloaded universe CSV:**")
    st.caption("If you downloaded the universe CSV before, upload it here to restore the cache instantly — no re-scraping needed.")
    _imp_file = st.file_uploader("Upload universe CSV", type=["csv"], key="import_universe_csv")
    if _imp_file:
        try:
            _imp_df = pd.read_csv(_imp_file)
            _imp_df.columns = [c.strip().lower().replace(" ","_") for c in _imp_df.columns]
            if "store_name" not in _imp_df.columns or "lat" not in _imp_df.columns:
                st.error("File must have at least store_name and lat columns.")
            else:
                for _col, _default in [
                    ("lng",0.0),("rating",0.0),("review_count",0),("price_level",0),
                    ("category","supermarket"),("source","scraped"),("covered",False),
                    ("phone",""),("opening_hours",""),("website",""),
                    ("annual_sales_usd",0.0),("lines_per_store",0),("poi_count",0),
                    ("place_id",""),("store_id",""),("address",""),("city",""),("business_status","Active"),
                ]:
                    if _col not in _imp_df.columns: _imp_df[_col] = _default
                if "universe_cache" not in st.session_state: st.session_state["universe_cache"] = {}
                st.session_state["universe_cache"][_cache_key] = {
                    "universe":    _imp_df.to_dict("records"),
                    "market_name": cfg.get("market_name",""),
                    "scraped_at":  f"Imported {datetime.datetime.now().strftime('%d %b %Y %H:%M')}",
                    "categories":  cfg.get("categories",[]),
                    "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
                }
                st.success(f"  Imported {len(_imp_df):,} stores from CSV — cache restored.")
                st.rerun()
        except Exception as _ie:
            st.error(f"Import failed: {_ie}")

    st.markdown("**Option B — Build fresh universe from Google Places:**")
    st.info(
        f"No cached data for **{_scope_label}**. "
        "Configure enrichment options below, then click **Build & enrich universe**. "
        "This runs once — every future pipeline run reuses this data automatically."
    )

    _admin_enrich_s2 = st.session_state.get("admin_enrichment", {"run_place_details": True, "run_poi": True, "poi_radius_m": 500})
    _ec1, _ec2, _ec3 = st.columns(3)
    with _ec1:
        st.markdown("  **Price level** — always on (affluence scoring)")
        st.markdown("  **Nearby POI count** — always on (POI scoring)")
    with _ec2:



        _run_phone_s2 = st.toggle("  Phone & opening hours", value=_admin_enrich_s2.get("run_place_details", True), key="enrich_phone_s2", help="~$0.017/store.")
    with _ec3:
        _poi_radius_s2 = st.number_input("POI radius (m)", min_value=100, max_value=2000, value=_admin_enrich_s2.get("poi_radius_m", 500), step=100, key="poi_radius_s2")
    st.session_state["admin_enrichment"] = {"run_place_details": _run_phone_s2, "run_poi": True, "poi_radius_m": _poi_radius_s2}

    _r_est, _t_est = smart_tile_radius(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"])
    _centres_est   = grid_centres(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"], _r_est)
    _est_scrape    = len(_centres_est) * len(cfg.get("categories",[])) * 3
    _est_enrich    = min(len(_centres_est) * 15, 2000) if _run_phone_s2 else 0
    _est_cost      = round(_est_scrape * 0.032 + _est_enrich * 0.017, 2)
    _est_time      = fmt_time(_est_scrape * 0.25 + _est_enrich * 0.1)
    st.caption(f"Estimated: ~{_est_scrape:,} scrape calls + {_est_enrich:,} enrichment calls · ~${_est_cost} · ~{_est_time}")

    _scrape_api_key = (cfg.get("market_api_key") or st.session_state.get("session_api_key"))
    if not _scrape_api_key:
        try: _scrape_api_key = st.secrets.get("GOOGLE_MAPS_API_KEY","") or None
        except: _scrape_api_key = None

    if st.button("  Build & enrich universe", type="primary", key="btn_scrape_universe"):
        if not _scrape_api_key:
            st.error("No API key — set GOOGLE_MAPS_API_KEY in Secrets or Admin Settings.")
        else:
            _scrape_status = st.empty()
            _scrape_bar    = st.progress(0)
            _scrape_t0     = time.time()
            _seen_ids      = set()
            _osm_shops     = []
            _radius_m, _   = smart_tile_radius(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"])
            _centres       = grid_centres(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"],_radius_m)
            _total_tiles   = max(len(_centres)*len(cfg["categories"]),1)
            _done_tiles    = 0

            for _cat in cfg["categories"]:
                for _tlat,_tlng in _centres:
                    _token = None
                    while True:
                        _data = fetch_places(_tlat,_tlng,_radius_m,_cat,_scrape_api_key,_token)
                        for _place in _data.get("results",[]):
                            _pid = _place.get("place_id","")
                            if _pid in _seen_ids: continue
                            if _place.get("business_status") == "CLOSED_PERMANENTLY": continue
                            _seen_ids.add(_pid)
                            _loc   = _place.get("geometry",{}).get("location",{})
                            _vic   = _place.get("vicinity","")
                            _vp    = [p.strip() for p in _vic.split(",") if p.strip()]
                            _scity = _vp[-1] if len(_vp)>=2 else cfg.get("city","")
                            _saddr = ", ".join(_vp[:-1]) if len(_vp)>=2 else (_vp[0] if _vp else "")



                            _cname = clean_store_name(_place.get("name",""))
                            if not _cname: continue
                            _osm_shops.append({
                                "store_id":_pid,"place_id":_pid,"store_name":_cname,
                                "address":_saddr,"city":_scity,"lat":_loc.get("lat"),"lng":_loc.get("lng"),
                                "rating":float(_place.get("rating",0) or 0),
                                "review_count":int(_place.get("user_ratings_total",0) or 0),
                                "price_level":int(_place.get("price_level",0) or 0),
                                "business_status":_map_biz_status(_place.get("business_status","")),
                                "category":_cat,"annual_sales_usd":0.0,"lines_per_store":0,
                                "covered":False,"source":"scraped",
                                "phone":"","opening_hours":"","website":"","poi_count":0,
                            })
                        _token = _data.get("next_page_token")
                        if not _token: break
                    _done_tiles += 1
                    _pct = 5 + int(_done_tiles/_total_tiles*60)
                    _elapsed = time.time() - _scrape_t0
                    _rem = (_elapsed/_done_tiles)*(_total_tiles-_done_tiles) if _done_tiles>0 else 0
                    _scrape_status.info(
                        f"Scraping: {_done_tiles}/{_total_tiles} tiles · "
                        f"{len(_osm_shops):,} stores ·  {fmt_time(_rem).replace('~','')} remaining"
                    )
                    _scrape_bar.progress(_pct)
                    # Checkpoint every 50 tiles — silent save to session state only
                    # No download button here — clicking any button interrupts scraping
                    # Resume banner at top of page handles recovery if scraping is cut off
                    if _done_tiles % 50 == 0 or _done_tiles == _total_tiles:
                        st.session_state["scrape_checkpoint"] = {
                            "universe": _osm_shops[:], "done_tiles": _done_tiles,
                            "total_tiles": _total_tiles, "market": cfg.get("market_name",""),
                        }
                        st.session_state["_live_dl_csv"]  = pd.DataFrame(_osm_shops).to_csv(index=False)
                        st.session_state["_live_dl_name"] = f"{cfg.get('market_name','market')}_{_done_tiles}tiles_{len(_osm_shops)}stores.csv"

            # Phone & hours enrichment
            if _run_phone_s2:
                _need_det = [s for s in _osm_shops if s.get("place_id") and not s.get("phone")]
                _scrape_status.info(f"Phone & hours for {len(_need_det):,} stores...")
                for _di, _s in enumerate(_need_det):
                    _det = fetch_place_details(_s["place_id"], _scrape_api_key)
                    if _det:
                        _s["phone"]         = _det.get("formatted_phone_number","")
                        _s["website"]       = _det.get("website","")
                        _wt = _det.get("opening_hours",{}).get("weekday_text",[])
                        _s["opening_hours"] = " | ".join(_wt) if _wt else ""
                    _scrape_bar.progress(65 + int((_di+1)/max(len(_need_det),1)*20))



                    time.sleep(0.05)

            # POI enrichment
            _poi_r = st.session_state.get("admin_enrichment",{}).get("poi_radius_m", 500)
            _need_poi = [s for s in _osm_shops if s.get("lat") and s.get("lng") and not s.get("poi_count",0)]
            if _need_poi:
                _scrape_status.info(f"POI count for {len(_need_poi):,} stores...")
                for _pi, _s in enumerate(_need_poi):
                    try:
                        _pr = requests.get(PLACES_URL, params={"location":f"{_s['lat']},{_s['lng']}","radius":_poi_r,"key":_scrape_api_key}, timeout=8)
                        _s["poi_count"] = len(_pr.json().get("results",[]))
                    except: _s["poi_count"] = 0
                    _scrape_bar.progress(min(85 + int((_pi+1)/len(_need_poi)*14), 99))
                    time.sleep(0.05)

            # Save cache
            if "universe_cache" not in st.session_state: st.session_state["universe_cache"] = {}
            st.session_state["universe_cache"][_cache_key] = {
                "universe":    _osm_shops,
                "market_name": cfg.get("market_name",""),
                "scraped_at":  datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                "categories":  cfg.get("categories",[]),
                "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
            }
            _scrape_bar.progress(100)
            _scrape_status.success(f"  Universe built: {len(_osm_shops):,} stores · ready for pipeline runs.")
            st.rerun()

st.markdown("---")

# ── Derive enrich_scope from session ─────────────────────────────────────────
_run_enrich_cfg = st.session_state.get("admin_enrichment", {"run_place_details": True, "run_poi": True, "poi_radius_m": 500})
enrich_scope = "all" if _run_enrich_cfg.get("run_place_details", True) else "none"
enrich_count = 0

# ── STEP 3: RUN ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">3. Run the agent</div>', unsafe_allow_html=True)

_run_cache_check = st.session_state.get("universe_cache", {}).get(_scrape_cache_key(cfg))
_portfolio_ready = st.session_state.get("portfolio_df") is not None
_n_portfolio     = len(st.session_state["portfolio_df"]) if _portfolio_ready else 0
_geocode_cost    = round(_n_portfolio * PRICE_GEOCODE_PER_CALL, 2)

if _run_cache_check and _portfolio_ready:
    _cached_n_run = len(_run_cache_check["universe"])
    st.success(f"  Ready — **{_n_portfolio}** portfolio stores · **{_cached_n_run:,}** universe stores cached · estimated geocoding cost ~**${_geocode_cost}**")
elif not _run_cache_check:



    st.warning("  Universe not scraped yet — go to Step 2 to scrape first.")
elif not _portfolio_ready:
    st.warning("  No portfolio uploaded — go to Step 1.")

dry_run = st.checkbox("Dry run mode — no API calls, generates sample data for testing", value=False)
if not dry_run:
    if _run_cache_check:
        st.info("  Live mode — universe cached, only geocoding costs apply.")
    else:
        st.warning("  Live mode will call Google APIs for scraping and geocoding.")

# Show live download button if scrape data is available
if st.session_state.get("_live_dl_csv"):
    st.download_button(
        f"  Save scrape progress — {st.session_state.get('_live_dl_name','universe.csv')}",
        st.session_state["_live_dl_csv"],
        st.session_state.get("_live_dl_name","universe.csv"),
        "text/csv", key="dl_live_progress",
        help="Click at any time to save stores collected so far. Does not affect scraping."
    )

if st.button("  Run Coverage Agent", type="primary"):
    status = st.empty()
    bar    = st.progress(0)
    weights    = cfg["weights"]
    thresholds = cfg.get("thresholds", {"weekly":80,"fortnightly":60,"monthly":40})

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

        # Dry run: assign scores first, then calculate tiers
        dry_visit_benchmarks = cfg.get("visit_benchmarks", {})



        dry_size_pct         = cfg.get("size_percentiles", {"large_pct":20,"medium_pct":60,"small_pct":20})

        for row in base:
            sc = random.randint(50,100)
            all_stores.append({
                "store_id":row.get("store_id","S0"),"store_name":row.get("store_name","Store"),
                "address":row.get("address",""),"city":row.get("city",""),
                "category":row.get("category",cfg["categories"][0] if cfg["categories"] else "supermarket"),
                "lat":cfg["lat_min"]+random.uniform(0.01,max(cfg["lat_max"]-cfg["lat_min"]-0.01,0.02)),
                "lng":cfg["lng_min"]+random.uniform(0.01,max(cfg["lng_max"]-cfg["lng_min"]-0.01,0.02)),
                "rating":round(random.uniform(3.5,4.9),1),"review_count":random.randint(100,3000),
                "price_level":random.choice([2,2,3,3,4]),
                "business_status":"OPERATIONAL",
                "annual_sales_usd":float(row.get("annual_sales_usd",0)),"lines_per_store":int(row.get("lines_per_store",0)),
                "covered":True,"source":"portfolio","score":sc,
                "size_tier":"","visits_per_month":0,"visit_duration_min":0,"visit_frequency":"","calls_per_month":0,
                "rep_id":random.randint(1,cfg["rep_count"]),"coverage_status":"covered",
                "phone":random.choice(phone_samples),"opening_hours":random.choice(hours_samples),
                "website":"","place_id":f"dry_place_{row.get('store_id','S0')}","poi_count":0,
            })
        for i in range(60):
            cat = random.choice(cfg["categories"])
            sc  = random.randint(10,95)
            all_stores.append({
                "store_id":f"G{i:03d}","store_name":f"{random.choice(prefixes)} {cat.replace('_',' ').title()} {i+1}",
                "address":f"{random.randint(1,200)} Sample Street","city":cfg.get("city",""),
                "category":cat,
                "lat":cfg["lat_min"]+random.uniform(0.01,max(cfg["lat_max"]-cfg["lat_min"]-0.01,0.02)),
                "lng":cfg["lng_min"]+random.uniform(0.01,max(cfg["lng_max"]-cfg["lng_min"]-0.01,0.02)),
                "rating":round(random.uniform(2.8,4.9),1),"review_count":random.randint(10,5000),
                "price_level":random.choice([0,1,1,2,2,3]),
                "business_status":"OPERATIONAL",
                "annual_sales_usd":0.0,"lines_per_store":0,
                "covered":False,"source":"scraped","score":sc,
                "size_tier":"","visits_per_month":0,"visit_duration_min":0,"visit_frequency":"","calls_per_month":0,
                "rep_id":0,"coverage_status":"gap",
                "phone":random.choice(phone_samples) if enrich_scope != "none" else "",
                "opening_hours":random.choice(hours_samples) if enrich_scope != "none" else "",
                "website":"","place_id":f"dry_gap_{i:03d}","poi_count":0,
            })
        # Apply size tier assignment to dry run stores
        dry_cat_pct = build_category_percentiles(all_stores)
        for s in all_stores:
            tier, visits, duration = assign_size_tier(s, dry_cat_pct, dry_visit_benchmarks, dry_size_pct)
            s["size_tier"]          = tier
            s["visits_per_month"]   = visits
            s["visit_duration_min"] = duration



            s["calls_per_month"]    = visits
            s["visit_frequency"]    = tier
            if tier == "Large":
                s["rep_id"] = random.randint(1, cfg["rep_count"])
            elif tier == "Medium":
                s["rep_id"] = random.randint(1, cfg["rep_count"])
            else:
                s["rep_id"] = random.randint(1, cfg["rep_count"]) if random.random() > 0.3 else 0

        bar.progress(100)
        gap_stores = sorted([s for s in all_stores if s["coverage_status"]=="gap"],key=lambda x:x["score"],reverse=True)
        covered_n  = sum(1 for s in all_stores if s["covered"])

        # Calculate rep recommendation for dry run — time-based model
        dry_priority  = [s for s in all_stores if s.get("size_tier") in ("Large","Medium","Small") and s.get("lat") and s.get("lng")]
        daily_mins    = cfg.get("daily_minutes", 480)
        work_days     = cfg.get("working_days", 22)
        speed_kmh     = cfg.get("avg_speed_kmh", 30)
        dry_rep_mode  = cfg.get("rep_mode","fixed")

        if dry_rep_mode == "recommended":
            rec_reps, total_mins, monthly_cap = recommended_reps_time_based(dry_priority, daily_mins, work_days, speed_kmh)
            dry_rec = {
                "mode":                 "recommended",
                "total_minutes_needed": total_mins,
                "monthly_cap_per_rep":  monthly_cap,
                "daily_minutes":        daily_mins,
                "working_days":         work_days,
                "avg_speed_kmh":        speed_kmh,
                "recommended_reps":     rec_reps,
                "current_reps":         cfg.get("rep_count",0),
                "shortfall":            rec_reps - cfg.get("rep_count",0),
                "zone_centres":         [],
            }
        else:
            monthly_cap = daily_mins * work_days
            dry_rec = {
                "mode":                "fixed",
                "rep_count":           cfg.get("rep_count",6),
                "daily_minutes":       daily_mins,
                "working_days":        work_days,
                "avg_speed_kmh":       speed_kmh,
                "monthly_cap_per_rep": monthly_cap,
                "zone_centres":        [],
            }

        # Dry run — abstract plan period from frequencies



        all_freqs_d   = [s.get("visits_per_month",1) for s in all_stores if s.get("visits_per_month",0)>0]
        min_freq_d    = min(all_freqs_d) if all_freqs_d else 1
        plan_period_d = max(1, round(1/min_freq_d)) if min_freq_d < 1 else 1
        plan_keys_d   = [f"m{i+1}" for i in range(plan_period_d)]
        plan_labels_d = [f"Month {i+1}" for i in range(plan_period_d)]

        dry_city_lat = (cfg["lat_min"] + cfg["lat_max"]) / 2
        dry_city_lng = (cfg["lng_min"] + cfg["lng_max"]) / 2
        dry_rep_ids  = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))
        dry_speed    = cfg.get("avg_speed_kmh", 30)
        dry_daily    = cfg.get("daily_minutes", 480)

        for rep_id in dry_rep_ids:
            try:
                rep_s = [s for s in all_stores if s.get("rep_id")==rep_id
                         and s.get("size_tier") in ("Large","Medium","Small")]
                if rep_s:
                    build_daily_routes(rep_s, daily_minutes=dry_daily, avg_speed_kmh=dry_speed,
                                       city_lat=dry_city_lat, city_lng=dry_city_lng)
            except Exception:
                for i, s in enumerate([s for s in all_stores if s.get("rep_id")==rep_id]):
                    s["assigned_day"]    = WEEKDAYS[i % 5]
                    s["day_visit_order"] = (i // 5) + 1

        WEEK_LABELS_DRY = ["Week 1","Week 2","Week 3","Week 4"]
        def _pick_weeks_d(vpm):
            if vpm >= 4: return WEEK_LABELS_DRY
            if vpm >= 2: return [WEEK_LABELS_DRY[0], WEEK_LABELS_DRY[2]]
            if vpm >= 1: return [WEEK_LABELS_DRY[1]]
            return []

        for s in all_stores:
            for mk in plan_keys_d:
                s[f"{mk}_weeks"]  = []
                s[f"{mk}_visits"] = 0
            s["plan_visits"] = 0

        for s in all_stores:
            if not s.get("assigned_day"):
                s["plan_visits"] = 0; continue
            day = s["assigned_day"]; vpm = s.get("visits_per_month",1)
            if vpm >= 1:
                weeks = _pick_weeks_d(vpm)
                for mk in plan_keys_d:
                    s[f"{mk}_weeks"]  = [f"{w} - {day}" for w in weeks]
                    s[f"{mk}_visits"] = len(weeks)
                    s["plan_visits"] += len(weeks)



            else:
                total_v = max(1, round(vpm * plan_period_d))
                order   = s.get("day_visit_order",1); vc = 0
                for i, mk in enumerate(plan_keys_d):
                    if vc >= total_v: break
                    if (order+i) % plan_period_d == 0 or (i==len(plan_keys_d)-1 and vc==0):
                        s[f"{mk}_weeks"]  = [f"Week 2 - {day}"]
                        s[f"{mk}_visits"] = 1
                        s["plan_visits"] += 1; vc += 1

        for s in all_stores:
            if "assigned_day" not in s:
                s["assigned_day"]=""; s["day_visit_order"]=0; s["plan_visits"]=0
                for mk in plan_keys_d:
                    s[f"{mk}_weeks"]=[]; s[f"{mk}_visits"]=0

        st.session_state["route_plan_months"] = {
            "plan_period":  plan_period_d,
            "month_keys":   plan_keys_d,
            "month_labels": plan_labels_d,
        }

        st.session_state["run_results"] = {
            "all_stores":all_stores,"gap_stores":gap_stores,
            "coverage_rate_before":round(len(base)/max(len(all_stores),1)*100,1),
            "coverage_rate_after":round(covered_n/max(len(all_stores),1)*100,1),
            "portfolio":[s for s in all_stores if s["source"]=="portfolio"],
            "universe":[s for s in all_stores if s["source"]=="scraped"],
            "rep_recommendation": dry_rec,
        }
        st.session_state["last_market"] = cfg["market_name"]
        status.success(f"  Dry run complete — {len(all_stores)} stores generated. Open Results or Routes in the sidebar.")

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
        enrich_poi    = st.session_state.get("enrich_poi_scope","none")
        poi_radius    = st.session_state.get("enrich_poi_radius", 500)



        total_steps   = 6
        if enrich_scope != "none": total_steps += 1
        if enrich_poi  != "none": total_steps += 1
        run_start   = time.time()

        # Stage 1: Geocode
        # Skip stores that already have both lat and lng — trust existing coordinates
        needs_geocode = []
        has_coords    = []
        for s in portfolio:
            try:
                lat_val = float(s.get("lat","") or "")
                lng_val = float(s.get("lng","") or "")
                s["lat"] = lat_val
                s["lng"] = lng_val
                has_coords.append(s)
            except (ValueError, TypeError):
                s["lat"] = None
                s["lng"] = None
                needs_geocode.append(s)

        if has_coords:
            status.info(f"Stage 1/{total_steps} — {len(has_coords)} stores already have coordinates — skipping geocoding for those.")
        if needs_geocode:
            status.info(f"Stage 1/{total_steps} — Geocoding {len(needs_geocode)} stores...")
        bar.progress(5)

        market_country = cfg.get("country_name","") or st.session_state.get("country_name","")
        for s in needs_geocode:
            district = _get_location_field(s, DISTRICT_COLS)
            region   = _get_location_field(s, REGION_COLS)
            lat, lng = geocode_store(s.get("address",""), s.get("city",""), api_key, district, region, market_country)
            s["lat"], s["lng"] = lat, lng
            time.sleep(0.05)

        # ── Geocoding quality check ───────────────────────────────────────────
        # Flag stores whose geocoded coordinates land outside the market bounding box
        # These are likely geocoding errors (wrong city matched, generic result etc.)
        bbox_lat_min = cfg.get("lat_min", -90)
        bbox_lat_max = cfg.get("lat_max",  90)
        bbox_lng_min = cfg.get("lng_min", -180)
        bbox_lng_max = cfg.get("lng_max",  180)

        # Buffer = larger of: 50% of bbox size OR 2 degrees (~220km)
        # This ensures stores in same country but outside the specific market area
        # are NOT flagged as suspect (e.g. stores in Sur/Muscat when market is Al Kamil)
        lat_span = bbox_lat_max - bbox_lat_min



        lng_span = bbox_lng_max - bbox_lng_min
        lat_buf  = max(lat_span * 0.5, 2.0)
        lng_buf  = max(lng_span * 0.5, 2.0)

        suspect_stores = []
        for s in needs_geocode:
            if not (s.get("lat") and s.get("lng")): continue
            if not (bbox_lat_min - lat_buf <= s["lat"] <= bbox_lat_max + lat_buf and
                    bbox_lng_min - lng_buf <= s["lng"] <= bbox_lng_max + lng_buf):
                s["geocode_suspect"] = True
                suspect_stores.append(s)
            else:
                s["geocode_suspect"] = False

        geocode_ok      = sum(1 for s in portfolio if s.get("lat") and s.get("lng") and not s.get("geocode_suspect"))
        geocode_fail    = sum(1 for s in portfolio if not (s.get("lat") and s.get("lng")))
        geocode_suspect = len(suspect_stores)

        msg = (
            f"Stage 1/{total_steps} — Complete: {len(has_coords)} had coordinates · "
            f"{geocode_ok} geocoded correctly · {geocode_fail} failed"
        )
        if geocode_suspect:
            msg += f" ·  {geocode_suspect} suspect (coordinates outside market area)"
        status.info(msg)

        if suspect_stores:
            status.info(f"Stage 1/{total_steps} — Re-geocoding {len(suspect_stores)} suspect stores...")
            mkt_lat = (bbox_lat_min + bbox_lat_max) / 2
            mkt_lng = (bbox_lng_min + bbox_lng_max) / 2
            st.session_state["_geocode_suspect_stores"] = []

            def try_regeocde(store, api_key, mkt_lat, mkt_lng, bbox_lat_min, bbox_lat_max, bbox_lng_min, bbox_lng_max, lat_buf, lng_buf):
                """Try multiple strategies to re-geocode a suspect store. Returns (lat, lng, google_data) or (None, None, {})."""
                def _s(v):
                    if v is None: return ""
                    try:
                        import math
                        if isinstance(v, float) and math.isnan(v): return ""
                    except Exception: pass
                    return str(v).strip()
                name    = _s(store.get("store_name",""))
                city    = _s(store.get("city","")) or _s(store.get("address",""))
                district= _s(store.get("district",""))
                region  = _s(store.get("region",""))

                # Build query variants from most to least specific



                # ALWAYS include country to prevent geocoding to wrong country
                country_sfx = f", {store.get('_market_country','')}" if store.get('_market_country') else ""
                queries = []
                if name and city:    queries.append(f"{name}, {city}{country_sfx}")
                if name and district:queries.append(f"{name}, {district}{country_sfx}")
                if name and region:  queries.append(f"{name}, {region}{country_sfx}")
                if name:             queries.append(f"{name}{country_sfx}")

                def in_bbox(rlat, rlng):
                    return (bbox_lat_min - lat_buf <= rlat <= bbox_lat_max + lat_buf and
                            bbox_lng_min - lng_buf <= rlng <= bbox_lng_max + lng_buf)

                for query in queries:
                    # Strategy 1: Google Geocoding API with bounds restriction
                    try:
                        r = requests.get(
                            "https://maps.googleapis.com/maps/api/geocode/json",
                            params={"address": query,
                                    "bounds": f"{bbox_lat_min},{bbox_lng_min}|{bbox_lat_max},{bbox_lng_max}",
                                    "key": api_key},
                            timeout=10
                        )
                        data = r.json()
                        if data.get("status") == "OK":
                            for res in data["results"]:
                                loc = res.get("geometry",{}).get("location",{})
                                rlat, rlng = loc.get("lat"), loc.get("lng")
                                if rlat and rlng and in_bbox(rlat, rlng):
                                    return round(rlat,6), round(rlng,6), {}
                        time.sleep(0.05)
                    except Exception:
                        pass

                    # Strategy 2: Google Places Text Search biased to market centre
                    try:
                        r = requests.get(
                            "https://maps.googleapis.com/maps/api/place/textsearch/json",
                            params={"query": query,
                                    "location": f"{mkt_lat},{mkt_lng}",
                                    "radius": "50000",
                                    "key": api_key},
                            timeout=10
                        )
                        data = r.json()
                        if data.get("status") == "OK" and data.get("results"):
                            for res in data["results"]:
                                loc = res.get("geometry",{}).get("location",{})



                                rlat, rlng = loc.get("lat"), loc.get("lng")
                                if rlat and rlng and in_bbox(rlat, rlng):
                                    google_data = {
                                        "place_id":     res.get("place_id",""),
                                        "rating":       float(res.get("rating",0) or 0),
                                        "review_count": int(res.get("user_ratings_total",0) or 0),
                                        "price_level":  int(res.get("price_level",0) or 0),
                                    }
                                    return round(rlat,6), round(rlng,6), google_data
                        time.sleep(0.05)
                    except Exception:
                        pass

                return None, None, {}

            for s in suspect_stores:
                s["_market_country"] = market_country  # pass to try_regeocde
                bad_lat = round(float(s.get("lat") or 0), 5)
                bad_lng = round(float(s.get("lng") or 0), 5)
                fixed_lat, fixed_lng, fixed_google_data = try_regeocde(
                    s, api_key, mkt_lat, mkt_lng,
                    bbox_lat_min, bbox_lat_max, bbox_lng_min, bbox_lng_max,
                    lat_buf, lng_buf
                )
                if fixed_lat and fixed_lng:
                    s["lat"] = fixed_lat
                    s["lng"] = fixed_lng
                    s["geocode_suspect"]  = False
                    s["geocode_fixed"]    = True
                    s["original_lat"]     = bad_lat
                    s["original_lng"]     = bad_lng
                    # Apply Google data captured from text search
                    for k, v in fixed_google_data.items():
                        if v: s[k] = v
                else:
                    # Could not fix — null out bad coordinates so they don't
                    # cause false coverage matches or wrong map positions
                    s["geocode_suspect"]  = True
                    s["original_lat"]     = bad_lat
                    s["original_lng"]     = bad_lng
                    s["lat"]              = None
                    s["lng"]              = None
                st.session_state["_geocode_suspect_stores"].append(s)

        bar.progress(15)

        # Stage 2: Universe — use cache if available, scrape if not



        _run_cache_key = _scrape_cache_key(cfg)
        _run_cache     = st.session_state.get("universe_cache", {}).get(_run_cache_key)

        if _run_cache:
            _cache_all = [dict(s) for s in _run_cache["universe"]]
            universe   = [s for s in _cache_all if s.get("source") != "portfolio"]
            # Bring enriched fields back from cache into live portfolio stores
            _cache_port = {s.get("store_id","") or s.get("store_name",""): s
                           for s in _cache_all if s.get("source") == "portfolio"}
            for p in portfolio:
                _key = p.get("store_id","") or p.get("store_name","")
                if _key in _cache_port:
                    _cp = _cache_port[_key]
                    for _f in ["rating","review_count","price_level","place_id",
                               "phone","opening_hours","website"]:
                        if _cp.get(_f) and not p.get(_f):
                            p[_f] = _cp[_f]
                        elif _f in ["rating","review_count"] and _cp.get(_f,0) > p.get(_f,0):
                            p[_f] = _cp[_f]
                    # Only borrow coordinates if portfolio store genuinely has none
                    if not (p.get("lat") and p.get("lng")) and _cp.get("lat"):
                        p["lat"] = _cp["lat"]
                        p["lng"] = _cp["lng"]
            status.info(
                f"Stage 2/{total_steps} — Cache loaded: "
                f"{len(universe):,} gap stores "
                f"(scraped {_run_cache.get('scraped_at','')}) — skipping API scrape."
            )
            bar.progress(45)
        else:
            # No cache — scrape now and save to cache for future runs
            status.warning("No cached universe found — scraping now. Use Step 2 above to pre-cache next time.")
            seen_ids     = set()
            universe     = []
            total_tiles  = max(len(centres)*len(cfg["categories"]),1)
            done_tiles   = 0
            scrape_start = time.time()

            for cat in cfg["categories"]:
                for lat,lng in centres:
                    token = None
                    while True:
                        data = fetch_places(lat,lng,radius_m,cat,api_key,token)
                        for place in data.get("results",[]):
                            pid = place.get("place_id","")
                            if pid in seen_ids: continue
                            if place.get("business_status") == "CLOSED_PERMANENTLY": continue



                            seen_ids.add(pid)
                            loc     = place.get("geometry",{}).get("location",{})
                            vicinity = place.get("vicinity","")
                            vparts  = [p.strip() for p in vicinity.split(",") if p.strip()]
                            if len(vparts) >= 2:
                                store_city    = vparts[-1]
                                store_address = ", ".join(vparts[:-1])
                            elif len(vparts) == 1:
                                store_city    = cfg.get("city","")
                                store_address = vparts[0]
                            else:
                                store_city    = cfg.get("city","")
                                store_address = ""
                            cleaned_name = clean_store_name(place.get("name",""))
                            if not cleaned_name: continue
                            universe.append({
                                "store_id":pid,"place_id":pid,
                                "store_name":cleaned_name,
                                "address":store_address,"city":store_city,
                                "region":cfg.get("city",""),
                                "lat":loc.get("lat"),"lng":loc.get("lng"),
                                "rating":float(place.get("rating",0) or 0),
                                "review_count":int(place.get("user_ratings_total",0) or 0),
                                "price_level":int(place.get("price_level",0) or 0),
                                "business_status":_map_biz_status(place.get("business_status","")),
                                "category":cat,"annual_sales_usd":0.0,"lines_per_store":0,
                                "covered":False,"source":"scraped",
                                "phone":"","opening_hours":"","website":"","poi_count":0,
                            })
                        token = data.get("next_page_token")
                        if not token: break
                    done_tiles += 1
                    pct     = 15 + int(done_tiles/total_tiles*30)
                    elapsed = time.time()-scrape_start
                    rem     = (elapsed/done_tiles)*(total_tiles-done_tiles) if done_tiles>0 else 0
                    status.info(f"Stage 2/{total_steps} — Scraping {cat}... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores |  {fmt_time(rem).replace('~','')} remaining")
                    bar.progress(pct)
                    # Checkpoint every 50 tiles
                    if done_tiles % 50 == 0 or done_tiles == total_tiles:
                        st.session_state["scrape_checkpoint"] = {
                            "universe": universe[:], "done_tiles": done_tiles,
                            "total_tiles": total_tiles, "market": cfg.get("market_name",""),
                        }
                        st.session_state["_live_dl_csv"]  = pd.DataFrame(universe).to_csv(index=False)
                        st.session_state["_live_dl_name"] = f"{cfg.get('market_name','market')}_{done_tiles}tiles_{len(universe)}stores.csv"

            # Auto-save to cache



            if "universe_cache" not in st.session_state:
                st.session_state["universe_cache"] = {}
            st.session_state["universe_cache"][_run_cache_key] = {
                "universe":    universe,
                "market_name": cfg.get("market_name",""),
                "scraped_at":  datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                "categories":  cfg.get("categories",[]),
                "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
            }
            status.info(f"Stage 2/{total_steps} — Found {len(universe):,} stores (auto-saved to cache)")
            bar.progress(45)

        # Stage 3: Score
        status.info(f"Stage 3/{total_steps} — Scoring all stores...")
        all_stores = portfolio + universe
        def _safe_num(v, default=0):
            try:    return float(v) if v is not None else default
            except: return default
        max_rev   = max((_safe_num(s.get("review_count",0))    for s in all_stores), default=0) or 1
        max_sales = max((_safe_num(s.get("annual_sales_usd",0)) for s in portfolio), default=0) or 1
        max_lines = max((_safe_num(s.get("lines_per_store",0))  for s in portfolio), default=0) or 1
        max_poi   = max((_safe_num(s.get("poi_count",0))         for s in all_stores), default=0) or 1
        max_rev   = max_rev   if max_rev   > 0 else 1
        max_sales = max_sales if max_sales > 0 else 1
        max_lines = max_lines if max_lines > 0 else 1
        max_poi   = max_poi   if max_poi   > 0 else 1
        # Two-group scoring (Jaimin doc):
        # Group 1 (Current Coverage / portfolio): Rating, Reviews, Affluence, POI, Sales, Lines
        # Group 2 (Scraped / Gap): Rating, Reviews, Affluence, POI only
        weights_cc  = st.session_state.get("admin_scoring_weights",
            {"rating":0.20,"reviews":0.25,"affluence":0.15,"poi":0.15,"sales":0.15,"lines":0.10})
        weights_gap = st.session_state.get("admin_scoring_weights_gap",
            {"rating":0.25,"reviews":0.25,"affluence":0.25,"poi":0.25})

        def _w(d):
            tot = sum(d.values()) or 1
            return {k: v/tot for k,v in d.items()}
        wcc  = _w({k: _safe_num(v) for k,v in weights_cc.items()})
        wgap = _w({k: _safe_num(v) for k,v in weights_gap.items()})

        def _score_store(s):
            try:
                r_n    = min(1.0, _safe_num(s.get("rating",0)) / 5)
                rv_n   = math.log1p(_safe_num(s.get("review_count",0))) / math.log1p(max_rev) if max_rev > 1 else 0.0
                pl_raw = _safe_num(s.get("price_level",0))
                aff_n  = pl_raw / 4 if pl_raw > 0 else 0.5
                poi_raw= _safe_num(s.get("poi_count",0))



                poi_n  = math.log1p(poi_raw) / math.log1p(max_poi) if max_poi > 1 else 0.0

                if s.get("source") == "portfolio":
                    # Current Coverage — all 6 signals
                    sal_n = min(1.0, _safe_num(s.get("annual_sales_usd",0)) / max_sales) if max_sales > 0 else 0.0
                    lin_n = min(1.0, _safe_num(s.get("lines_per_store",0))  / max_lines) if max_lines > 0 else 0.0
                    raw = (r_n   * wcc.get("rating",0.20) +
                           rv_n  * wcc.get("reviews",0.25) +
                           aff_n * wcc.get("affluence",0.15) +
                           poi_n * wcc.get("poi",0.15) +
                           sal_n * wcc.get("sales",0.15) +
                           lin_n * wcc.get("lines",0.10))
                else:
                    # Scraped / Gap — Google signals only
                    raw = (r_n   * wgap.get("rating",0.25) +
                           rv_n  * wgap.get("reviews",0.25) +
                           aff_n * wgap.get("affluence",0.25) +
                           poi_n * wgap.get("poi",0.25))
                if not math.isfinite(raw): return 0
                return min(100, max(0, round(raw * 100)))
            except Exception:
                return 0

        for s in all_stores:
            s["score"] = _score_store(s)
        bar.progress(55)

        # Stage 4: Gap match
        status.info(f"Stage 4/{total_steps} — Matching coverage gaps...")

        # Fixed matching thresholds — size-aware, no user config needed
        NAME_SIM_THRESH = 0.75   # 75% bigram similarity required for fuzzy match

        # Size-aware radius — larger stores have bigger physical footprint
        # Large (hypermarket/supermarket): 200m base, 250m fuzzy
        # Medium (supermarket): 100m base, 150m fuzzy
        # Small/Occasional/Unknown: 50m base, 100m fuzzy
        SIZE_RADIUS = {
            "Large":      (200, 250),
            "Medium":     (100, 150),
            "Small":      (50,  100),
            "Occasional": (50,  100),
        }
        DEFAULT_RADIUS = (50, 100)

        # Large chain keywords — always use Large radius regardless of tier
        LARGE_CHAINS = ["lulu","carrefour","hypermarket","hyper","mall","centre","center",



                        "hypermart","spinneys","waitrose","union","giant","geant"]

        def name_similarity(a, b):
            """Bigram similarity between two store names after stripping noise words."""
            a = str(a).lower().strip()
            b = str(b).lower().strip()
            if not a or not b: return 0.0
            for w in ["supermercado","super","mercado","hipermercado","hiper","atacado",
                      "atacadao","ltda","eireli","me ","trading","est ","llc","co ","trd"]:
                a = a.replace(w,""); b = b.replace(w,"")
            a = a.strip(); b = b.strip()
            if not a or not b: return 0.0
            def bigrams(s): return set(s[i:i+2] for i in range(len(s)-1))
            ba, bb = bigrams(a), bigrams(b)
            if not ba or not bb: return 0.0
            return len(ba & bb) / max(len(ba | bb), 1)

        def get_radii(store):
            """Return (base_radius, fuzzy_radius) for a store based on size tier and name."""
            name_lower = str(store.get("store_name","")).lower()
            # Check for large chain keywords — always use large radius
            if any(kw in name_lower for kw in LARGE_CHAINS):
                return SIZE_RADIUS["Large"]
            tier = store.get("size_tier","")
            return SIZE_RADIUS.get(tier, DEFAULT_RADIUS)

        # Build lookup structures
        portfolio_place_ids = {p.get("place_id") for p in portfolio if p.get("place_id")}
        portfolio_coords    = {(round(p["lat"],4), round(p["lng"],4))
                               for p in portfolio if p.get("lat") and p.get("lng")}
        covered_p           = [s for s in portfolio if s.get("lat") and s.get("lng")]

        for u in universe:
            if not (u.get("lat") and u.get("lng")):
                u["coverage_status"] = "no_coords"
                u["covered"] = False
                continue

            matched = False

            # Match 1: same place_id — definitively the same store
            if u.get("place_id") and u["place_id"] in portfolio_place_ids:
                matched = True

            # Match 2: exact same coordinates (rounded to ~11m)
            if not matched:
                if (round(u["lat"],4), round(u["lng"],4)) in portfolio_coords:



                    matched = True

            # Match 3 + 4: size-aware distance matching
            if not matched:
                base_r, fuzzy_r = get_radii(u)
                for p in covered_p:
                    dist = haversine_m(u["lat"],u["lng"],p["lat"],p["lng"])
                    # Match 3: within base radius — always covered
                    if dist <= base_r:
                        matched = True
                        break
                    # Match 4: within fuzzy radius — only if names similar enough
                    if dist <= fuzzy_r:
                        sim = name_similarity(u.get("store_name",""), p.get("store_name",""))
                        if sim >= NAME_SIM_THRESH:
                            matched = True
                            break

            u["covered"]         = matched
            u["coverage_status"] = "covered" if matched else "gap"

        for p in portfolio: p["coverage_status"] = "covered"

        # ── Enrich portfolio stores with Google data from matched scraped store ─
        # Portfolio stores start with rating=0, review_count=0 — copy Google data
        # from the best matching scraped store (closest within fuzzy_radius)
        GOOGLE_FIELDS = ["rating","review_count","price_level","place_id",
                         "phone","opening_hours","website","business_status"]
        for p in portfolio:
            best_match = None

            # Try distance-based match first (if coordinates are valid)
            if p.get("lat") and p.get("lng"):
                best_dist = float("inf")
                for u in universe:
                    if not (u.get("lat") and u.get("lng")): continue
                    dist = haversine_m(p["lat"],p["lng"],u["lat"],u["lng"])
                    if dist < best_dist and dist <= 250:
                        best_dist  = dist
                        best_match = u

            # Fallback: name similarity match if no distance match found
            if not best_match:
                best_sim = 0.0
                p_name   = str(p.get("store_name","")).lower().strip()
                for u in universe:
                    u_name = str(u.get("store_name","")).lower().strip()



                    if not p_name or not u_name: continue
                    # Simple token overlap
                    p_tokens = set(p_name.split())
                    u_tokens = set(u_name.split())
                    if not p_tokens or not u_tokens: continue
                    sim = len(p_tokens & u_tokens) / max(len(p_tokens | u_tokens), 1)
                    if sim > best_sim and sim >= 0.5:
                        best_sim   = sim
                        best_match = u

            if best_match:
                for field in GOOGLE_FIELDS:
                    if best_match.get(field) and not p.get(field):
                        p[field] = best_match[field]
                # Always update rating/reviews from Google
                if best_match.get("rating"):
                    p["rating"]       = best_match["rating"]
                if best_match.get("review_count"):
                    p["review_count"] = best_match["review_count"]
                # If store has no coordinates, borrow from matched scraped store
                if not (p.get("lat") and p.get("lng")) and best_match.get("lat"):
                    p["lat"]          = best_match["lat"]
                    p["lng"]          = best_match["lng"]
                    p["geocode_fixed"]= True

        # ── Fix suspect portfolio stores using scraped universe ───────────────
        # For portfolio stores still flagged as suspect, try name-match against
        # scraped universe to borrow the correct Google coordinates
        still_suspect = [s for s in portfolio if s.get("geocode_suspect")]
        if still_suspect:
            status.info(f"Stage 4/{total_steps} — Attempting coordinate fix for {len(still_suspect)} suspect stores using scraped data...")
            coord_fixes = 0
            for p in still_suspect:
                best_sim   = 0
                best_match = None
                for u in universe:
                    if not (u.get("lat") and u.get("lng")): continue
                    sim = name_similarity(p.get("store_name",""), u.get("store_name",""))
                    if sim > best_sim and sim >= 0.4:  # lowered to 40% for harder names
                        best_sim   = sim
                        best_match = u
                if best_match:
                    p["original_lat"]    = p.get("original_lat", round(float(p.get("lat") or 0), 5))
                    p["original_lng"]    = p.get("original_lng", round(float(p.get("lng") or 0), 5))
                    p["lat"]             = best_match["lat"]
                    p["lng"]             = best_match["lng"]
                    p["geocode_suspect"] = False



                    p["geocode_fixed"]   = True
                    # Copy Google data from matched scraped store
                    for field in ["rating","review_count","price_level","place_id"]:
                        if best_match.get(field):
                            p[field] = best_match[field]
                    coord_fixes         += 1
                else:
                    # Could not fix — null out so it doesn't place store in wrong location
                    p["geocode_fixed"]   = False
                    p["lat"]             = None
                    p["lng"]             = None
            if coord_fixes:
                st.success(f"  Fixed coordinates for {coord_fixes} store(s) using scraped data match.")

        # Log matching summary
        n_covered = sum(1 for u in universe if u.get("covered"))
        n_gap     = sum(1 for u in universe if not u.get("covered"))
        # Count portfolio stores with coord fixes for user info
        n_fixed   = sum(1 for p in portfolio if p.get("geocode_fixed"))
        n_suspect = sum(1 for p in portfolio if p.get("geocode_suspect"))
        msg = (
            f"Stage 4/{total_steps} — Coverage matching complete: "
            f"{n_covered} covered · {n_gap} gaps "
            f"(size-aware radius matching · name similarity ≥ {int(NAME_SIM_THRESH*100)}%)"
        )
        if n_fixed:   msg += f" ·  {n_fixed} coords auto-fixed"
        if n_suspect: msg += f" ·  {n_suspect} coords still suspect"
        status.info(msg)

        # Show consolidated geocoding correction report now that Stage 4 fixes are done
        all_suspect = st.session_state.get("_geocode_suspect_stores", [])
        if all_suspect:
            report_rows = []
            for s in all_suspect:
                if s.get("geocode_fixed"):
                    status_str = "  Fixed automatically"
                elif not s.get("geocode_suspect"):
                    status_str = "  Fixed automatically"
                else:
                    status_str = "  Could not fix — see note below"
                report_rows.append({
                    "Store":            s.get("store_name",""),
                    "Address":          s.get("address",""),
                    "City":             s.get("city",""),
                    "Original lat/lng": f"{s.get('original_lat','')} , {s.get('original_lng','')}",
                    "Corrected lat/lng": f"{round(float(s.get('lat') or 0),5)} , {round(float(s.get('lng') or 0),5)}" if s.get("lat") else "—",
                    "Status":           status_str,



                })
            unfixed = [r for r in report_rows if "Could not fix" in r["Status"]]
            fixed   = [r for r in report_rows if "Fixed" in r["Status"]]
            if fixed:
                st.success(f"  {len(fixed)} store(s) had incorrect geocoding and were automatically corrected.")
            if unfixed:
                st.warning(
                    f"  {len(unfixed)} store(s) could not be corrected automatically. "
                    f"To fix: add correct **lat** and **lng** columns to your portfolio CSV. "
                    f"Open Google Maps → find the store → right-click the pin → 'What's here?' to get coordinates."
                )
            with st.expander(f"  Geocoding correction report ({len(report_rows)} stores)", expanded=bool(unfixed)):
                st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)
                st.caption(
                    "Original lat/lng = coordinates from geocoding (wrong location). "
                    "Corrected lat/lng = fixed coordinates used in this run. "
                    "These corrections are also saved in the output CSV columns original_lat / original_lng / geocode_fixed."
                )
            st.session_state.pop("_geocode_suspect_stores", None)

        bar.progress(65)

        # Stage 5: Size tier + visit frequency assignment
        status.info(f"Stage 5/{total_steps} — Assigning store size tiers and visit frequencies...")
        visit_benchmarks  = cfg.get("visit_benchmarks", {})
        size_percentiles  = cfg.get("size_percentiles", {"large_pct":20,"medium_pct":60,"small_pct":20})
        cat_percentiles   = build_category_percentiles(all_stores)
        for s in all_stores:
            tier, visits, duration = assign_size_tier(s, cat_percentiles, visit_benchmarks, size_percentiles)
            s["size_tier"]          = tier
            s["visits_per_month"]   = visits
            s["visit_duration_min"] = duration
            s["calls_per_month"]    = visits   # keep for backward compatibility
            s["visit_frequency"]    = tier     # keep for backward compatibility
        bar.progress(72)

        # Stage 6: Routes + Time-Based Rep Planning
        # Route universe = ALL scored stores (covered + gap) with a size tier and valid coordinates
        # Gap stores in the route = new distribution points for the rep to develop
        priority = [s for s in all_stores if s.get("size_tier") in ("Large","Medium","Small") and s.get("lat") and s.get("lng")]
        rep_recommendation = None

        rep_mode      = cfg.get("rep_mode","fixed")
        daily_minutes = cfg.get("daily_minutes", 480)
        working_days  = cfg.get("working_days", 22)
        avg_speed     = cfg.get("avg_speed_kmh", 30)
        break_minutes = cfg.get("break_minutes",



            st.session_state.get("admin_rep_defaults",{}).get("break_minutes", 30))
        # Effective daily capacity = total day minus break time
        effective_daily = daily_minutes - break_minutes
        current_reps  = cfg.get("rep_count", 0)

        if rep_mode == "recommended":
            status.info(f"Stage 6/{total_steps} — Calculating recommended rep count (time-based)...")

            rec_reps, total_mins, monthly_cap = recommended_reps_time_based(
                priority, effective_daily, working_days, avg_speed
            )

            # Cluster into recommended rep zones
            zone_centres = []
            if priority:
                pts         = [(s["lat"],s["lng"]) for s in priority]
                zone_labels = kmeans_simple(pts, rec_reps)
                for s, lbl in zip(priority, zone_labels):
                    s["rep_id"] = int(lbl) + 1

                for zone in range(rec_reps):
                    zone_stores = [priority[i] for i in range(len(priority)) if zone_labels[i] == zone]
                    if zone_stores:
                        centre_lat    = sum(s["lat"] for s in zone_stores) / len(zone_stores)
                        centre_lng    = sum(s["lng"] for s in zone_stores) / len(zone_stores)
                        zone_mins     = calculate_rep_time_budget(zone_stores, avg_speed)
                        zone_visits   = sum(s.get("visits_per_month",1) for s in zone_stores)
                        zone_centres.append({
                            "zone":                 zone + 1,
                            "centre_lat":           round(centre_lat, 4),
                            "centre_lng":           round(centre_lng, 4),
                            "store_count":          len(zone_stores),
                            "visits_per_month":     zone_visits,
                            "time_needed_min":      round(zone_mins),
                            "capacity_min":         monthly_cap,
                            "utilisation_pct":      round(zone_mins / monthly_cap * 100) if monthly_cap > 0 else 0,
                        })

            # Utilisation threshold disabled — respect configured rep count
            removed_zones = []
            actual_reps   = len(zone_centres)

            if False and removed_zones:  # disabled
                kept_ids = {z["zone"] for z in kept_zones}
                # Build centroid lookup for kept zones
                kept_centroids = {z["zone"]: (z["centre_lat"], z["centre_lng"]) for z in kept_zones}
                removed_ids    = {z["zone"] for z in removed_zones}



                for s in all_stores:
                    if s.get("rep_id") in removed_ids and s.get("lat") and s.get("lng"):
                        # Assign to nearest kept zone by distance
                        nearest_zone = min(
                            kept_centroids.keys(),
                            key=lambda zid: haversine_m(
                                s["lat"], s["lng"],
                                kept_centroids[zid][0], kept_centroids[zid][1]
                            )
                        )
                        s["rep_id"] = nearest_zone
                    elif s.get("rep_id") in removed_ids:
                        s["rep_id"] = list(kept_ids)[0] if kept_ids else 0

            rep_recommendation = {
                "mode":                "recommended",
                "total_minutes_needed": total_mins,
                "monthly_cap_per_rep":  monthly_cap,
                "daily_minutes":        daily_minutes,
                "working_days":         working_days,
                "avg_speed_kmh":        avg_speed,
                "break_minutes":        break_minutes,
                "recommended_reps":     actual_reps,
                "requested_reps":       rec_reps,
                "current_reps":         current_reps,
                "shortfall":            actual_reps - current_reps if current_reps > 0 else 0,
                "min_utilisation_pct":  min_util_pct,
                "zone_centres":         zone_centres,
            }
        else:
            # Fixed mode — cluster into configured rep count
            rep_count = max(1, cfg.get("rep_count", 1))
            status.info(f"Stage 6/{total_steps} — Allocating {rep_count} rep routes (time-based workload)...")
            if priority:
                pts    = [(s["lat"],s["lng"]) for s in priority]
                labels = kmeans_simple(pts, rep_count)
                for s, lbl in zip(priority, labels):
                    s["rep_id"] = int(lbl) + 1

                # Calculate time utilisation per rep
                zone_centres = []
                for zone in range(rep_count):
                    zone_stores = [priority[i] for i in range(len(priority)) if labels[i] == zone]
                    if zone_stores:
                        centre_lat  = sum(s["lat"] for s in zone_stores) / len(zone_stores)
                        centre_lng  = sum(s["lng"] for s in zone_stores) / len(zone_stores)
                        zone_mins   = calculate_rep_time_budget(zone_stores, avg_speed)



                        monthly_cap = effective_daily * working_days
                        zone_visits = sum(s.get("visits_per_month",1) for s in zone_stores)
                        zone_centres.append({
                            "zone":                 zone + 1,
                            "centre_lat":           round(centre_lat, 4),
                            "centre_lng":           round(centre_lng, 4),
                            "store_count":          len(zone_stores),
                            "visits_per_month":     zone_visits,
                            "time_needed_min":      round(zone_mins),
                            "capacity_min":         monthly_cap,
                            "utilisation_pct":      round(zone_mins / monthly_cap * 100) if monthly_cap > 0 else 0,
                        })

                # Utilisation threshold disabled — respect configured rep count
                kept_zones_f = zone_centres
                under_util   = []

                if False and under_util and kept_zones_f:  # disabled
                    kept_centroids_f = {z["zone"]: (z["centre_lat"], z["centre_lng"]) for z in kept_zones_f}
                    under_ids        = {z["zone"] for z in under_util}
                    kept_ids_f       = set(kept_centroids_f.keys())
                    for s in all_stores:
                        if s.get("rep_id") in under_ids and s.get("lat") and s.get("lng"):
                            nearest_zone = min(
                                kept_centroids_f.keys(),
                                key=lambda zid: haversine_m(
                                    s["lat"], s["lng"],
                                    kept_centroids_f[zid][0], kept_centroids_f[zid][1]
                                )
                            )
                            s["rep_id"] = nearest_zone
                        elif s.get("rep_id") in under_ids:
                            s["rep_id"] = list(kept_ids_f)[0] if kept_ids_f else 0

                rep_recommendation = {
                    "mode":                "fixed",
                    "rep_count":           len(kept_zones_f),
                    "daily_minutes":       daily_minutes,
                    "working_days":        working_days,
                    "avg_speed_kmh":       avg_speed,
                    "break_minutes":       break_minutes,
                    "monthly_cap_per_rep": effective_daily * working_days,
                    "min_utilisation_pct": min_util_pct,
                    "under_utilised_zones": [z["zone"] for z in under_util],
                    "zone_centres":        kept_zones_f,
                }
            else:



                rep_recommendation = {"mode":"fixed","rep_count":rep_count,"zone_centres":[]}

        for s in all_stores:
            if "rep_id" not in s: s["rep_id"] = 0

        # ── Build dynamic plan period route plan ─────────────────────────────
        # Plan period = 1 / min(visits_per_month) across all tiers
        all_freqs   = [s.get("visits_per_month",1) for s in all_stores if s.get("visits_per_month",0) > 0]
        min_freq    = min(all_freqs) if all_freqs else 1
        plan_period = max(1, round(1 / min_freq)) if min_freq < 1 else 1

        # Plan months = abstract labels: m1, m2, m3...
        plan_month_keys    = [f"m{i+1}" for i in range(plan_period)]
        plan_month_labels  = [f"Month {i+1}" for i in range(plan_period)]

        city_lat    = (cfg["lat_min"] + cfg["lat_max"]) / 2
        city_lng    = (cfg["lng_min"] + cfg["lng_max"]) / 2
        all_rep_ids = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))

        status.info(f"Stage 6b — Building {plan_period}-month route plan for {len(all_rep_ids)} reps...")

        # Build day assignments — establishes fixed weekday per store
        for rep_id in all_rep_ids:
            try:
                rep_stores = [s for s in all_stores
                    if s.get("rep_id") == rep_id
                    and s.get("size_tier") in ("Large","Medium","Small")]
                if rep_stores:
                    build_daily_routes(rep_stores, daily_minutes=daily_minutes,
                                       avg_speed_kmh=avg_speed, city_lat=city_lat, city_lng=city_lng)
            except Exception as e:
                status.warning(f"Route building warning for Rep {rep_id}: {e} — continuing...")
                for i, s in enumerate([s for s in all_stores if s.get("rep_id")==rep_id]):
                    s["assigned_day"]    = WEEKDAYS[i % 5]
                    s["day_visit_order"] = (i // 5) + 1

        # WEEK LABELS: 4 weeks per month
        WEEK_LABELS = ["Week 1", "Week 2", "Week 3", "Week 4"]

        def pick_weeks(vpm):
            """Pick which weeks to visit based on visits_per_month."""
            if vpm >= 4:   return WEEK_LABELS          # weekly — all 4 weeks
            if vpm >= 2:   return [WEEK_LABELS[0], WEEK_LABELS[2]]  # fortnightly — Week 1 + 3
            if vpm >= 1:   return [WEEK_LABELS[1]]     # monthly — Week 2
            return []  # sub-monthly handled separately

        # Initialise all month columns



        for s in all_stores:
            for mk in plan_month_keys:
                s[f"{mk}_weeks"]  = []
                s[f"{mk}_visits"] = 0
            s["plan_visits"] = 0

        # Assign weeks per store per month
        for s in all_stores:
            if not s.get("assigned_day"):
                continue

            day = s["assigned_day"]
            vpm = s.get("visits_per_month", 1)

            if vpm >= 1:
                # Visited every month — assign weeks in each plan month
                weeks = pick_weeks(vpm)
                for mk in plan_month_keys:
                    s[f"{mk}_weeks"]  = [f"{w} - {day}" for w in weeks]
                    s[f"{mk}_visits"] = len(weeks)
                    s["plan_visits"] += len(weeks)
            else:
                # Sub-monthly — 1 visit total across the plan window
                # Balance across months by day_visit_order
                total_visits = max(1, round(vpm * plan_period))
                order = s.get("day_visit_order", 1)
                visit_count = 0
                for i, mk in enumerate(plan_month_keys):
                    if visit_count >= total_visits: break
                    if (order + i) % plan_period == 0 or                        (i == len(plan_month_keys)-1 and visit_count == 0):
                        s[f"{mk}_weeks"]  = [f"Week 2 - {day}"]
                        s[f"{mk}_visits"] = 1
                        s["plan_visits"] += 1
                        visit_count      += 1

        # Clear unassigned stores
        for s in all_stores:
            if "assigned_day" not in s:
                s["assigned_day"]    = ""
                s["day_visit_order"] = 0
                s["plan_visits"]     = 0

        # Store plan metadata
        st.session_state["route_plan_months"] = {
            "plan_period":  plan_period,
            "month_keys":   plan_month_keys,
            "month_labels": plan_month_labels,



        }
        # ── Recalculate using plan_visits and apply 60% utilisation threshold ──
        routed_stores = [s for s in all_stores if s.get("plan_visits",0) > 0 and s.get("rep_id",0) > 0]
        if routed_stores:
            _, final_total_mins, final_monthly_cap = recommended_reps_time_based(
                routed_stores, effective_daily, working_days, avg_speed
            )

            # Recalculate utilisation per rep using plan_visits
            rep_time_map = {}
            for s in routed_stores:
                rid = s.get("rep_id", 0)
                rep_time_map[rid] = rep_time_map.get(rid, 0) + (
                    s.get("plan_visits", 0) * s.get("visit_duration_min", 25) / 2
                )

            # Do not drop reps based on utilisation — respect the configured rep count.
            # Low utilisation is informational only.
            under_util_reps = []
            kept_reps       = list(rep_time_map.keys())

            if under_util_reps and kept_reps:  # never true — disabled
                status.info(f"Stage 6b — {len(under_util_reps)} rep(s) below {min_util_pct}% utilisation — redistributing stores...")
                # Build centroids for kept reps
                kept_centroids = {}
                for rid in kept_reps:
                    rs = [s for s in routed_stores if s.get("rep_id") == rid]
                    if rs:
                        kept_centroids[rid] = (
                            sum(s["lat"] for s in rs if s.get("lat")) / max(sum(1 for s in rs if s.get("lat")),1),
                            sum(s["lng"] for s in rs if s.get("lng")) / max(sum(1 for s in rs if s.get("lng")),1),
                        )
                # Reassign stores from under-utilised reps to nearest kept rep
                for s in all_stores:
                    if s.get("rep_id") in under_util_reps:
                        if s.get("lat") and s.get("lng") and kept_centroids:
                            nearest = min(kept_centroids.keys(),
                                key=lambda r: haversine_m(s["lat"],s["lng"],kept_centroids[r][0],kept_centroids[r][1]))
                            s["rep_id"] = nearest
                        elif kept_reps:
                            s["rep_id"] = kept_reps[0]

                # Check if any kept rep is now over 100% capacity — if so rebalance
                # Build rep time map after redistribution
                rep_time_after = {}
                for s in all_stores:
                    rid = s.get("rep_id",0)



                    if rid and s.get("plan_visits",0) > 0:
                        rep_time_after[rid] = rep_time_after.get(rid,0) + (
                            s.get("plan_visits",0) * s.get("visit_duration_min",25) / 2
                        )

                over_cap_reps = {rid for rid,t in rep_time_after.items() if t > final_monthly_cap}
                if over_cap_reps:
                    for over_rid in over_cap_reps:
                        # Get stores for this rep sorted by score ascending (lowest first to move)
                        rep_stores_sorted = sorted(
                            [s for s in all_stores if s.get("rep_id")==over_rid and s.get("plan_visits",0)>0],
                            key=lambda x: x.get("score",0)
                        )
                        rep_t = rep_time_after.get(over_rid, 0)
                        for s in rep_stores_sorted:
                            if rep_t <= final_monthly_cap:
                                break
                            s_t = s.get("plan_visits",0) * s.get("visit_duration_min",25) / 2
                            # Find another kept rep with capacity — not the over-capacity one
                            candidates = {r:t for r,t in rep_time_after.items()
                                          if r != over_rid and r in kept_reps and t + s_t <= final_monthly_cap}
                            if candidates:
                                best_r = min(candidates.keys(), key=lambda r: candidates[r])
                                s["rep_id"] = best_r
                                rep_time_after[best_r] = rep_time_after.get(best_r,0) + s_t
                                rep_t -= s_t
                                rep_time_after[over_rid] = rep_t

                # Final utilisation check — catch any reps still below threshold after rebalancing
                rep_time_final = {}
                for s in all_stores:
                    rid = s.get("rep_id",0)
                    if rid and s.get("plan_visits",0) > 0:
                        rep_time_final[rid] = rep_time_final.get(rid,0) + (
                            s.get("plan_visits",0) * s.get("visit_duration_min",25) / 2
                        )
                still_under = [rid for rid,t in rep_time_final.items() if t < min_util_mins]
                still_kept  = [rid for rid,t in rep_time_final.items() if t >= min_util_mins]
                if still_under and still_kept:
                    still_centroids = {}
                    for rid in still_kept:
                        rs = [s for s in all_stores if s.get("rep_id")==rid and s.get("lat") and s.get("lng")]
                        if rs:
                            still_centroids[rid] = (
                                sum(s["lat"] for s in rs)/len(rs),
                                sum(s["lng"] for s in rs)/len(rs)
                            )



                    for s in all_stores:
                        if s.get("rep_id") in still_under:
                            if s.get("lat") and s.get("lng") and still_centroids:
                                nearest = min(still_centroids.keys(),
                                    key=lambda r: haversine_m(s["lat"],s["lng"],still_centroids[r][0],still_centroids[r][1]))
                                s["rep_id"] = nearest
                            elif still_kept:
                                s["rep_id"] = still_kept[0]

                # Recalculate after redistribution
                routed_stores = [s for s in all_stores if s.get("plan_visits",0) > 0 and s.get("rep_id",0) > 0]
                _, final_total_mins, final_monthly_cap = recommended_reps_time_based(
                    routed_stores, effective_daily, working_days, avg_speed
                )

            # Update rep_recommendation
            if rep_recommendation:
                rep_recommendation["total_minutes_needed"] = round(final_total_mins)
                rep_recommendation["monthly_cap_per_rep"]  = round(final_monthly_cap)
                rep_recommendation["recommended_reps"]     = len(kept_reps) if kept_reps else len(rep_time_map)
                # Update zone_centres utilisation
                for z in rep_recommendation.get("zone_centres", []):
                    zid = z.get("zone", 0)
                    zs  = [s for s in routed_stores if s.get("rep_id") == zid]
                    if zs:
                        z_mins = sum(s.get("plan_visits",0) * s.get("visit_duration_min",25) / 2 for s in zs)
                        z["time_needed_min"] = round(z_mins)
                        z["utilisation_pct"] = round(z_mins / max(final_monthly_cap,1) * 100)

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
                    f"{enriched} updated |  {fmt_time(rem).replace('~','')} remaining"
                )
                bar.progress(min(pct,97))
                time.sleep(0.1)

        # Stage POI: Nearby POI enrichment (optional)
        if enrich_poi != "none":
            poi_stage = total_steps - (1 if enrich_scope == "none" else 0)
            status.info(f"Stage {poi_stage}/{total_steps} — Enriching stores with nearby POI count...")

            if enrich_poi == "top_n":
                poi_candidates = sorted(
                    [s for s in all_stores if s.get("lat") and s.get("lng")],
                    key=lambda x: x.get("score",0), reverse=True
                )[:st.session_state.get("poi_count", 100)]
            elif enrich_poi == "gaps_only":
                poi_candidates = [s for s in all_stores if s.get("coverage_status")=="gap" and s.get("lat") and s.get("lng")]
            else:
                poi_candidates = [s for s in all_stores if s.get("lat") and s.get("lng")]

            poi_enriched = 0
            poi_start    = time.time()
            for i, store in enumerate(poi_candidates):



                try:
                    r = requests.get(PLACES_URL,
                        params={"location":f"{store['lat']},{store['lng']}",
                                "radius":poi_radius,"key":api_key},
                        timeout=8)
                    data = r.json()
                    store["poi_count"] = len(data.get("results",[]))
                    poi_enriched += 1
                except Exception:
                    store["poi_count"] = 0
                rem = (time.time()-poi_start)/(i+1)*(len(poi_candidates)-i-1) if i>0 else 0
                status.info(
                    f"Stage {poi_stage}/{total_steps} — POI enrichment... "
                    f"{i+1}/{len(poi_candidates)} stores |  {fmt_time(rem).replace('~','')} remaining"
                )
                time.sleep(0.05)

            # Re-score with POI data
            max_poi = max((s.get("poi_count",0) for s in all_stores), default=1) or 1
            w       = cfg["weights"]
            for s in all_stores:
                poi_n  = math.log1p(s.get("poi_count",0))/math.log1p(max_poi) if max_poi > 1 else 0.0
                aff_n  = (s.get("price_level",0) or 0)/4 if (s.get("price_level",0) or 0) > 0 else 0.5
                r_n    = _safe_num(s.get("rating",0)) / 5
                rv_n   = math.log1p(s.get("review_count",0) or 0)/math.log1p(max_rev)
                sal_n  = _safe_num(s.get("annual_sales_usd",0)) / max_sales if (s.get("covered") and max_sales > 0) else 0.0
                lin_n  = _safe_num(s.get("lines_per_store",0))  / max_lines if (s.get("covered") and max_lines > 0) else 0.0
                s["score"] = min(100,round((
                    r_n   * w.get("rating",    0.20) +
                    rv_n  * w.get("reviews",   0.25) +
                    aff_n * w.get("affluence", 0.10) +
                    poi_n * w.get("poi",       0.15) +
                    sal_n * w.get("sales",     0.15) +
                    lin_n * w.get("lines",     0.15)
                )*100))
            status.info(f"Stage {poi_stage}/{total_steps} — POI enrichment complete. Scores updated.")

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
            "rep_recommendation": rep_recommendation,
            "geocode_summary": {"ok": geocode_ok, "failed": geocode_fail},
        }
        st.session_state["last_market"] = cfg["market_name"]
        bar.progress(100)

        enrich_msg = f" · {enriched} stores enriched with phone & hours" if enrich_scope != "none" else ""
        status.success(
            f"  Pipeline complete in {actual_time} · actual cost ~${actual_cost:.2f} · "
            f"{len(all_stores):,} stores scored · {len(gap_stores):,} gaps found{enrich_msg}. "
            f"Open Results in the sidebar."
        )
