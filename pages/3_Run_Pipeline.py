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

st.markdown("""
<div class="page-header">
    <h2>  Run Pipeline</h2>



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
                    "fields":"formatted_phone_number,opening_hours,website,formatted_address,price_level",
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
    Uses visits_per_month (pre-route) — reliable estimate before daily budget cuts.
    Returns (recommended_reps, total_minutes_needed_per_month, minutes_per_rep_per_month).
    """
    if not priority_stores:
        return 1, 0.0, 0.0

    monthly_capacity = daily_minutes * working_days



    n_stores = len(priority_stores)

    # Total monthly visit time across all priority stores
    total_visit_time = sum(
        s.get("visit_duration_min", 25) * s.get("visits_per_month", 1)
        for s in priority_stores
    )

    # Travel time estimate based on geographic spread
    # Per-territory estimate: once clustered, each rep covers area/reps
    # We iterate to convergence: start with 1 rep, estimate travel, get reps, repeat
    geo = [s for s in priority_stores if s.get("lat") and s.get("lng")]
    if len(geo) > 1:
        lat_span = max(s["lat"] for s in geo) - min(s["lat"] for s in geo)
        lng_span = max(s["lng"] for s in geo) - min(s["lng"] for s in geo)
        mid_lat  = sum(s["lat"] for s in geo) / len(geo)
        total_area_km2 = max(lat_span * 111 * lng_span * 111 * math.cos(math.radians(mid_lat)), 1)
        total_monthly_visits = sum(s.get("visits_per_month", 1) for s in priority_stores)

        # Iterative: estimate reps → use reps to recalculate per-territory travel
        est_reps = max(1, math.ceil(total_visit_time / monthly_capacity))
        for _ in range(3):  # 3 iterations converges quickly
            territory_area  = total_area_km2 / est_reps
            stores_per_rep  = max(n_stores / est_reps, 1)
            avg_dist_km     = math.sqrt(territory_area / stores_per_rep) * 0.7
            avg_travel_min  = (avg_dist_km / max(avg_speed_kmh, 1)) * 60
            total_travel    = avg_travel_min * total_monthly_visits
            total_minutes   = total_visit_time + total_travel
            est_reps        = max(1, math.ceil(total_minutes / monthly_capacity))
    else:
        total_travel  = total_visit_time * 0.2
        total_minutes = total_visit_time + total_travel
        est_reps      = max(1, math.ceil(total_minutes / monthly_capacity))

    return est_reps, round(total_visit_time), round(monthly_capacity)

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

import calendar as _cal

def get_month_weekdays(year, month):
    """
    Returns dict: {weekday_name: [date, date, ...]} — real calendar dates.
    e.g. {"Monday": [datetime.date(2025,4,7), datetime.date(2025,4,14), ...]}
    Week 5 naturally included when the month has 5 occurrences of a weekday.
    """
    result  = {d: [] for d in WEEKDAYS}
    n_days  = _cal.monthrange(year, month)[1]
    for day_num in range(1, n_days + 1):
        d    = datetime.date(year, month, day_num)
        name = WEEKDAYS[d.weekday()] if d.weekday() < 5 else None
        if name:
            result[name].append(d)
    return result



def group_cities_into_supercities(stores, radius_km=15.0):
    """
    Groups stores by city label, then clusters those city centroids into
    super-cities using a proximity threshold.
    Returns dict: store -> super_city_id (int, 1-based)
    Also returns list of super-city dicts with centroid and workload.
    Uses actual store coordinates for centroids — not city name averages.
    """
    # Build city centroids from actual store coordinates
    city_stores = {}
    for s in stores:
        city = str(s.get("city","") or "").strip()
        if not city: city = "_unknown"
        if city not in city_stores:
            city_stores[city] = []
        if s.get("lat") and s.get("lng"):
            city_stores[city].append(s)

    # Compute centroid per city (from stores not city-name averaging)
    city_centroids = {}
    for city, cstores in city_stores.items():
        if cstores:
            city_centroids[city] = (
                sum(s["lat"] for s in cstores) / len(cstores),
                sum(s["lng"] for s in cstores) / len(cstores),
            )

    # Single-linkage clustering at radius_km
    cities = list(city_centroids.keys())
    cluster_id = {c: None for c in cities}
    next_id    = 1
    for i, ca in enumerate(cities):
        if cluster_id[ca] is not None: continue
        cluster_id[ca] = next_id
        for cb in cities[i+1:]:
            if cluster_id[cb] is not None: continue
            la1,ln1 = city_centroids[ca]
            la2,ln2 = city_centroids[cb]
            if haversine_m(la1,ln1,la2,ln2) / 1000 <= radius_km:
                cluster_id[cb] = next_id
        next_id += 1

    # Build super-city summary
    sc_stores = {}
    for s in stores:



        city = str(s.get("city","") or "").strip() or "_unknown"
        sid  = cluster_id.get(city, 0)
        s["_supercity"] = sid
        if sid not in sc_stores: sc_stores[sid] = []
        sc_stores[sid].append(s)

    supercities = []
    for sid, sts in sc_stores.items():
        geo = [s for s in sts if s.get("lat") and s.get("lng")]
        if not geo: continue
        supercities.append({
            "id":         sid,
            "store_count": len(sts),
            "centre_lat": sum(s["lat"] for s in geo) / len(geo),
            "centre_lng": sum(s["lng"] for s in geo) / len(geo),
            "visit_time": sum(s.get("visits_per_month",1)*s.get("visit_duration_min",25)
                              for s in sts),
            "cities":     list({str(s.get("city","")) for s in sts}),
        })
    return supercities

def calc_zone_monthly_time(stores, avg_speed_kmh=30, daily_minutes=480):
    """
    Compute exact monthly execution + travel time for a set of stores.
    Does NOT include break time (break is a fixed overhead added separately).
    Respects each store's actual visits_per_month frequency.

    Returns (total_monthly_exec_travel, daily_breakdown_list)
    """
    geo = [s for s in stores if s.get("lat") and s.get("lng")]
    if not geo:
        vt = sum(s.get("visits_per_month",1) * s.get("visit_duration_min",25) for s in stores)
        return round(vt), []

    c_lat = sum(s["lat"] for s in geo) / len(geo)
    c_lng = sum(s["lng"] for s in geo) / len(geo)

    # Nearest-neighbour sort
    ordered, remaining = [], geo[:]
    cur_lat, cur_lng = c_lat, c_lng
    while remaining:
        nearest = min(remaining, key=lambda s: haversine_m(cur_lat,cur_lng,s["lat"],s["lng"]))
        ordered.append(nearest)
        cur_lat, cur_lng = nearest["lat"], nearest["lng"]
        remaining.remove(nearest)



    # 5 day-groups
    day_groups = [[] for _ in range(5)]
    for i, s in enumerate(ordered):
        day_groups[i % 5].append(s)

    total_monthly = 0.0
    daily_results = []

    for day_idx, day_stores in enumerate(day_groups):
        if not day_stores: continue

        # Travel for one route occurrence on this day
        travel_t = 0.0
        prev_lat, prev_lng = c_lat, c_lng
        for s in day_stores:
            travel_t += travel_time_minutes(prev_lat, prev_lng,
                                            s["lat"], s["lng"], avg_speed_kmh)
            prev_lat, prev_lng = s["lat"], s["lng"]

        total_dur = sum(s.get("visit_duration_min", 25) for s in day_stores)

        # Monthly contribution per store = vpm × (dur + proportional_travel)
        day_exec   = 0.0
        day_travel = 0.0
        for s in day_stores:
            vpm    = max(0.1, s.get("visits_per_month", 1))
            dur    = s.get("visit_duration_min", 25)
            t_shr  = (dur / max(total_dur, 1)) * travel_t
            day_exec   += vpm * dur
            day_travel += vpm * t_shr

        day_monthly = day_exec + day_travel
        total_monthly += day_monthly

        # Representative single-day stats (for display)
        visit_rep = sum(s.get("visit_duration_min",25) for s in day_stores)
        total_rep = visit_rep + travel_t
        daily_results.append({
            "day":    day_idx + 1,
            "stores": len(day_stores),
            "visit":  round(visit_rep),
            "travel": round(travel_t),
            "total":  round(total_rep),
            "pct":    round(total_rep / daily_minutes * 100),
            "monthly_contrib": round(day_monthly),
        })



    return round(total_monthly), daily_results

def plan_reps_by_supercity(supercities, priority_set, daily_minutes=480,
                            working_days=22, target_util=0.80, merge_threshold=0.70,
                            avg_speed_kmh=30):
    """
    Assigns rep counts to super-cities using city-bound logic:
    1. Calculate total real monthly time (visit + travel) for all priority stores
    2. Compute optimal_reps = ceil(total_time / monthly_cap)
    3. Merge supercities by proximity until count == optimal_reps
    4. Split each merged zone into ceil(zone_time / monthly_cap) reps using k-means
    5. If any resulting rep < 80% -> trim lowest-score stores from other reps instead
    """
    monthly_cap   = daily_minutes * working_days   # 10,560 min
    monthly_max   = monthly_cap * 1.10             # 11,616 min (110% monthly max)
    monthly_min   = monthly_cap * 0.80             # 8,448 min (80% monthly min)
    daily_max_pct = 125                             # 125% daily hard cap

    # Only work with priority stores that have valid coords
    priority_geo = [s for s in priority_set if s.get("lat") and s.get("lng")]
    if not priority_geo:
        return [], 0

    # --- Step 1: Compute total real monthly time for all priority stores combined ---
    total_monthly, _ = calc_zone_monthly_time(priority_geo, avg_speed_kmh, daily_minutes)
    # Use effective capacity (daily_minutes - 30min break) × working_days
    # since calc_zone_monthly_time returns exec+travel only (no break)
    eff_cap      = (daily_minutes - 30) * working_days   # 450 × 22 = 9,900
    optimal_reps = max(1, math.ceil(total_monthly / eff_cap))

    # --- Step 2: Build supercity list from priority stores only ---
    sc_data = {}
    for s in priority_set:
        sid = s.get("_supercity", 0)
        if sid not in sc_data:
            sc_data[sid] = {"stores": [], "visit_time": 0}
        sc_data[sid]["stores"].append(s)
        sc_data[sid]["visit_time"] += (s.get("visits_per_month", 1) *
                                        s.get("visit_duration_min", 25))

    sc_list = []
    for sid, d in sc_data.items():
        if not d["stores"]: continue
        geo = [s for s in d["stores"] if s.get("lat") and s.get("lng")]
        if not geo: continue
        sc_list.append({



            "id":         sid,
            "visit_time": d["visit_time"],
            "stores":     d["stores"],
            "lat":        sum(s["lat"] for s in geo) / len(geo),
            "lng":        sum(s["lng"] for s in geo) / len(geo),
        })

    # --- Step 3: Merge supercities by proximity until count == optimal_reps ---
    # Always merge smallest into nearest until we reach optimal_reps
    while len(sc_list) > optimal_reps and len(sc_list) > 1:
        sc_list.sort(key=lambda x: x["visit_time"])
        smallest = sc_list[0]
        others   = sc_list[1:]
        nearest  = min(others, key=lambda x: haversine_m(
            smallest["lat"], smallest["lng"], x["lat"], x["lng"]))
        # Merge smallest into nearest
        combined = nearest["stores"] + smallest["stores"]
        geo_c    = [s for s in combined if s.get("lat") and s.get("lng")]
        nearest["stores"]     = combined
        nearest["visit_time"] = nearest["visit_time"] + smallest["visit_time"]
        if geo_c:
            nearest["lat"] = sum(s["lat"] for s in geo_c) / len(geo_c)
            nearest["lng"] = sum(s["lng"] for s in geo_c) / len(geo_c)
        sc_list = [x for x in sc_list if x is not smallest]

    # --- Step 4: Assign rep IDs within each merged zone ---
    rep_counter  = 1
    zone_centres = []

    for sc in sc_list:
        sc_stores = sc["stores"]
        sc_geo    = [s for s in sc_stores if s.get("lat") and s.get("lng")]
        if not sc_stores: continue

        # Compute exact monthly time for this zone
        sc_monthly, sc_daily = calc_zone_monthly_time(sc_geo, avg_speed_kmh, daily_minutes)

        # Effective capacity = (480-30) × 22 = 9,900 — exec+travel only (no break)
        eff_cap_zone = (daily_minutes - 30) * working_days
        n_reps = max(1, math.ceil(sc_monthly / eff_cap_zone))

        # Rule: if extra rep would be < 80% -> trim lowest-score stores instead
        if n_reps > 1:
            eff_cap_trim = (daily_minutes - 30) * working_days
            time_per_rep = sc_monthly / n_reps
            if time_per_rep < eff_cap_trim * 0.80:
                # Try trimming lowest-score stores until (n_reps-1) reps fit



                n_try    = n_reps - 1
                sc_sorted = sorted(sc_stores, key=lambda x: x.get("score", 0), reverse=True)
                while sc_sorted:
                    t_try, _ = calc_zone_monthly_time(
                        [s for s in sc_sorted if s.get("lat") and s.get("lng")],
                        avg_speed_kmh, daily_minutes)
                    if t_try / n_try <= monthly_max:
                        break
                    dropped = sc_sorted.pop()
                    dropped["rep_id"] = 0   # unassign from plan
                sc_stores   = sc_sorted
                sc_geo      = [s for s in sc_stores if s.get("lat") and s.get("lng")]
                sc_monthly, sc_daily = calc_zone_monthly_time(sc_geo, avg_speed_kmh, daily_minutes)
                n_reps      = n_try

        # Assign rep IDs
        if n_reps == 1:
            for s in sc_stores:
                s["rep_id"] = rep_counter
        else:
            if len(sc_geo) >= n_reps:
                labels = kmeans_simple([(s["lat"], s["lng"]) for s in sc_geo], n_reps)
                for s, lbl in zip(sc_geo, labels):
                    s["rep_id"] = rep_counter + int(lbl)
            else:
                for i, s in enumerate(sc_stores):
                    s["rep_id"] = rep_counter + (i % n_reps)

        # Build zone_centres entries
        for r in range(n_reps):
            rid = rep_counter + r
            rz  = [s for s in sc_stores if s.get("rep_id") == rid]
            if not rz: continue
            rz_geo = [s for s in rz if s.get("lat") and s.get("lng")]
            rz_monthly, rz_daily = calc_zone_monthly_time(rz_geo, avg_speed_kmh, daily_minutes)
            zone_centres.append({
                "zone":            rid,
                "centre_lat":      round(sum(s["lat"] for s in rz_geo) / max(len(rz_geo), 1), 4),
                "centre_lng":      round(sum(s["lng"] for s in rz_geo) / max(len(rz_geo), 1), 4),
                "store_count":     len(rz),
                "time_needed_min": rz_monthly,
                "capacity_min":    monthly_cap,
                "utilisation_pct": round(rz_monthly / monthly_cap * 100),
                "daily_breakdown": rz_daily,
            })
        rep_counter += n_reps



    actual_reps = rep_counter - 1
    return zone_centres, actual_reps

def assign_cross_city_stores(all_stores, zone_centres, daily_minutes=480,
                              working_days=22, avg_speed_kmh=30):
    """
    After home-city routing, assigns cross-city stores to reps with spare capacity.
    Cross-city visits are batched onto 2-3 consecutive days to minimise travel.
    Stores with no rep_id (rep_id=0) are candidates for cross-city assignment.
    """
    monthly_cap  = daily_minutes * working_days
    max_day      = daily_minutes * 1.10   # 110% hard cap per day
    min_day      = daily_minutes * 0.80   # 80% minimum per day

    unassigned = [s for s in all_stores
                  if s.get("rep_id", 0) == 0
                  and s.get("size_tier") in ("Large","Medium","Small")
                  and s.get("lat") and s.get("lng")]
    if not unassigned: return

    # For each rep: calculate current monthly time and spare capacity
    rep_ids = sorted({z["zone"] for z in zone_centres})
    rep_spare = {}
    for rid in rep_ids:
        # Use exact monthly time already calculated for this rep's zone
        zc   = next((z for z in zone_centres if z["zone"]==rid), None)
        used = zc["time_needed_min"] if zc else sum(
            s.get("visits_per_month",1)*s.get("visit_duration_min",25)
            for s in all_stores if s.get("rep_id")==rid)
        # Leave 10% headroom for cross-city travel overhead
        rep_spare[rid] = (monthly_cap * 0.90) - used

    # Sort unassigned by score desc — assign best stores first
    unassigned.sort(key=lambda x: x.get("_norm_score", x.get("score",0)), reverse=True)

    for s in unassigned:
        best_rep      = None
        best_dist_cap = float("inf")
        s_time = s.get("visits_per_month",1) * s.get("visit_duration_min",25)
        for rid in rep_ids:
            if rep_spare.get(rid, 0) < s_time:
                continue  # no capacity
            zc = next((z for z in zone_centres if z["zone"]==rid), None)
            if not zc: continue
            dist = haversine_m(s["lat"],s["lng"],zc["centre_lat"],zc["centre_lng"])
            # Pick nearest rep with capacity



            if dist < best_dist_cap:
                best_dist_cap = dist
                best_rep      = rid
        if best_rep:
            s["rep_id"]      = best_rep
            rep_spare[best_rep] -= s_time
            s["_cross_city"] = True
        # If no rep has capacity, store stays unassigned (plan_visits=0)

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

    # ── Step 3: Enforce daily time budget (110% max per Jaimin doc) ────────────
    # Stores that exceed 110% cap are marked for cross-rep reassignment.
    # Do NOT push overflow to another day of the same rep — same day, different rep.
    def day_used_time(stores_list):
        t = 0.0
        prev_lat2, prev_lng2 = city_lat, city_lng
        for s2 in stores_list:
            t += s2.get("visit_duration_min", 25)
            if s2.get("lat") and s2.get("lng"):
                t += travel_time_minutes(prev_lat2, prev_lng2, s2["lat"], s2["lng"], avg_speed_kmh)
                prev_lat2, prev_lng2 = s2["lat"], s2["lng"]
        return t

    max_daily    = daily_minutes * 1.25   # 125% of full day = 600 min hard cap (per Jaimin)
    min_daily    = daily_minutes * 0.80   # 80% of full day = 384 min minimum target
    overflow_pool = []  # stores that exceeded 110% — need cross-rep reassignment

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
            if cumulative + total_t <= max_daily:
                kept.append(s)
                cumulative += total_t
                if s.get("lat") and s.get("lng"):
                    prev_lat, prev_lng = s["lat"], s["lng"]
            else:
                # Over 110% — mark for cross-rep reassignment on SAME day
                s["_overflow_day"] = day  # remember which day this store belongs to
                overflow_pool.append(s)
                s["assigned_day"]    = ""
                s["day_visit_order"] = 0
        day_groups[day] = kept

    # Store overflow pool on stores for caller to handle cross-rep reassignment
    for s in overflow_pool:
        s["_needs_cross_rep"] = True

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
st.markdown('<div class="section-title">1. Current Coverage CSV</div>', unsafe_allow_html=True)
st.markdown("Required: `store_name`, `address`, `city` | Optional: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`")

portfolio_df = st.session_state.get("portfolio_df")
if portfolio_df is not None:
    st.success(f"  Current Coverage loaded from Configure — {len(portfolio_df)} stores")
    st.dataframe(portfolio_df.head(3), use_container_width=True)
    if st.checkbox("Upload a different file"):
        portfolio_df = None
        st.session_state["portfolio_df"] = None

if portfolio_df is None:
    up = st.file_uploader("Upload Current Coverage CSV", type=["csv"])
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
st.download_button("  Download sample CSV", sample.to_csv(index=False), "current_coverage_sample.csv", "text/csv")

st.markdown("---")

# ── STEP 2: ENRICHMENT CONFIG ─────────────────────────────────────────────────
st.markdown('<div class="section-title">2. Place Details enrichment</div>', unsafe_allow_html=True)
st.caption("Runs automatically for all scraped stores — fetches phone, opening hours, price level and website.")

# Enrichment always runs for all stores — mandatory to get price_level for affluence scoring
enrich_scope = "all"
st.session_state["enrich_scope"] = enrich_scope

# Estimated universe for cost calculation
radius_m_est, n_tiles_est = smart_tile_radius(
    cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"]
)
est_universe = max(50, n_tiles_est * len(cfg["categories"]) * 15)
enrich_count = min(est_universe, 2000)
st.info(f"  Place Details will run for all scraped stores (~{enrich_count:,} estimated). "
        "This fetches phone, opening hours and price level — required for affluence scoring.")

st.markdown("---")

# ── STEP 3: PRE-FLIGHT ESTIMATE ───────────────────────────────────────────────
# POI enrichment is mandatory — runs automatically as part of Stage 2 scraping
st.info("  Nearby POI enrichment runs automatically for all stores as part of the pipeline.")



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
        <div class="preflight-title">  Area too large to scrape effectively</div>
        <div style="color:#B71C1C;font-size:0.9rem;margin-bottom:0.8rem">
            Your selected coverage area is <strong>~{est['area_km2']:,} km²</strong> —
            this is a full country or large region. Scraping this area would take
            <strong>{time_display}</strong> and cost approximately
            <strong>${est['total_cost']:.2f}</strong> in API credits.
        </div>
        <div class="suggestion-box">
             Go back to <strong>Configure</strong> and add specific cities or districts
            (e.g. Muscat, Salalah) instead of selecting the whole country.
            Each city typically takes 2–5 minutes and costs under $2.
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # ── Normal pre-flight card — pure native Streamlit, no custom HTML ────────
    colour_icons  = {"green": " ", "amber": " ", "red": " "}
    colour_fns    = {"green": st.success, "amber": st.warning, "red": st.error}
    status_fn     = colour_fns.get(est["colour"], st.info)
    status_fn(colour_icons.get(est["colour"],"") + "  " + est["label"])

    # Two headline metrics



    mc1, mc2 = st.columns(2)
    mc1.metric("Total estimated time",       time_display)
    mc2.metric("Total estimated API cost",   "$" + str(round(est["total_cost"], 2)))

    # Cost breakdown as a dataframe — always renders correctly
    breakdown = {
        "Item":   ["Google Places scraping", "Geocoding portfolio"],
        "Detail": [
            str(est["scrape_calls"]) + " calls · " + str(est["n_tiles"]) + " tiles · " + str(est["n_categories"]) + " categories · radius " + radius_label,
            str(est["geocode_calls"]) + " stores x $" + str(PRICE_GEOCODE_PER_CALL),
        ],
        "Cost ($)": [
            round(est["scrape_cost"], 2),
            round(est["geocode_cost"], 2),
        ],
    }
    if est["enrich_calls"] > 0:
        breakdown["Item"].append("Place Details enrichment")
        breakdown["Detail"].append(str(est["enrich_calls"]) + " stores x $" + str(PRICE_DETAILS_PER_CALL))
        breakdown["Cost ($)"].append(round(est["enrich_cost"], 2))

    breakdown["Item"].append("TOTAL")
    breakdown["Detail"].append(str(est["total_calls"]) + " total API calls")
    breakdown["Cost ($)"].append(round(est["total_cost"], 2))

    import pandas as pd
    bdf = pd.DataFrame(breakdown)
    st.dataframe(bdf, use_container_width=True, hide_index=True,
        column_config={"Cost ($)": st.column_config.NumberColumn("Cost ($)", format="$%.2f")})

    st.caption(
        "Coverage area: ~" + str(est["area_km2"]) + " km²"
        " · ~" + str(est["estimated_universe"]) + " stores estimated"
        " · " + str(est["n_portfolio"]) + " portfolio stores"
        " · Tile radius: " + radius_label
    )

    for sug in est["suggestions"]:
        st.info("  " + sug)

st.caption("  Google provides $200 free credit per month — most single-market runs are well within this limit.")

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
        f"  Live mode will call Google APIs — estimated **{time_display}** "
        f"and **${est['total_cost']:.2f}** in API costs."
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
                "business_status":"Active",
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
                "business_status":"Active",
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
        WEEK5_DAYS_DRY = {"Monday","Tuesday","Wednesday"}
        def _pick_weeks_d(vpm, day="", month_idx=0):
            if vpm >= 4:
                weeks = WEEK_LABELS_DRY[:]
                if month_idx == 0 and day in WEEK5_DAYS_DRY:
                    weeks.append("Week 5")
                return weeks
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
                for mk_i, mk in enumerate(plan_keys_d):
                    weeks = _pick_weeks_d(vpm, day, month_idx=mk_i)
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
            # Preserve original lat/lng from CSV before update overwrites them
            _orig_lat = s.get("lat")
            _orig_lng = s.get("lng")
            s.update({"covered":True,"source":"portfolio",
                      "rating":0.0,"review_count":0,"phone":"","opening_hours":"","website":""})
            # Restore original coordinates — only clear if they were missing/invalid



            try:
                s["lat"] = float(_orig_lat) if _orig_lat not in (None,"","nan") else None
                s["lng"] = float(_orig_lng) if _orig_lng not in (None,"","nan") else None
                # Validate range — zero coords are invalid
                if s["lat"] == 0.0: s["lat"] = None
                if s["lng"] == 0.0: s["lng"] = None
            except (TypeError, ValueError):
                s["lat"] = None
                s["lng"] = None
            if "category" not in s: s["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"

        radius_m, _ = smart_tile_radius(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"])
        centres     = grid_centres(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"],radius_m)
        _enrich_cfg   = st.session_state.get("admin_enrichment", {"run_place_details":True,"run_poi":True,"poi_radius_m":500})
        enrich_scope  = "all" if _enrich_cfg.get("run_place_details", True) else "none"
        enrich_poi    = "all" if _enrich_cfg.get("run_poi", True) else "none"
        poi_radius    = _enrich_cfg.get("poi_radius_m", 500)
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

        # ── Geocoding quality check — ALL portfolio stores ──────────────────────
        # Checks BOTH newly geocoded AND pre-existing coordinates
        # because original CSV coords may also be wrong (e.g. geocoded to wrong city)
        bbox_lat_min = cfg.get("lat_min", -90)
        bbox_lat_max = cfg.get("lat_max",  90)
        bbox_lng_min = cfg.get("lng_min", -180)
        bbox_lng_max = cfg.get("lng_max",  180)

        # Tight buffer: 0.5 degrees (~55km) around market bbox
        # Large enough for same-city variation, small enough to catch Muscat vs Al Kamil
        lat_span = bbox_lat_max - bbox_lat_min
        lng_span = bbox_lng_max - bbox_lng_min
        lat_buf  = max(lat_span * 0.5, 0.5)
        lng_buf  = max(lng_span * 0.5, 0.5)

        suspect_stores = []
        for s in portfolio:  # ALL portfolio stores, not just needs_geocode
            if not (s.get("lat") and s.get("lng")):
                s["geocode_suspect"] = False
                continue
            if not (bbox_lat_min - lat_buf <= float(s["lat"]) <= bbox_lat_max + lat_buf and
                    bbox_lng_min - lng_buf <= float(s["lng"]) <= bbox_lng_max + lng_buf):
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
                def _s(v): return str(v).strip() if v and str(v) not in ("nan","None","") else ""
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
                        # Filter out permanently closed stores
                        if place.get("business_status") == "CLOSED_PERMANENTLY":
                            continue
                        seen_ids.add(pid)
                        loc = place.get("geometry",{}).get("location",{})
                        # Extract city from vicinity — Google returns "street, city"
                        # vicinity = full address string, last comma-part is usually the city/area
                        vicinity  = place.get("vicinity","")
                        vparts    = [p.strip() for p in vicinity.split(",") if p.strip()]
                        # Use last part of vicinity as city if it looks like a place name
                        # Fall back to configured market city only if vicinity has 1 part or is empty
                        if len(vparts) >= 2:
                            store_city    = vparts[-1]   # last part = city/area
                            store_address = ", ".join(vparts[:-1])  # everything before = street address
                        elif len(vparts) == 1:
                            store_city    = cfg.get("city","")
                            store_address = vparts[0]
                        else:
                            store_city    = cfg.get("city","")
                            store_address = ""
                        cleaned_name = clean_store_name(place.get("name",""))



                        if not cleaned_name:
                            continue  # skip pure Arabic / garbled names
                        universe.append({
                            "store_id":pid,"place_id":pid,
                            "store_name":cleaned_name,
                            "address":store_address,"city":store_city,
                            "region":cfg.get("city",""),  # configured market area = region
                            "lat":loc.get("lat"),"lng":loc.get("lng"),
                            "rating":float(place.get("rating",0) or 0),
                            "review_count":int(place.get("user_ratings_total",0) or 0),
                            "price_level":int(place.get("price_level",0) or 0),
                            "business_status":place.get("business_status","Active"),
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
                status.info(f"Stage 2/{total_steps} — Scraping {cat}... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores |  {fmt_time(rem).replace('~','')} remaining")
                bar.progress(pct)

        status.info(f"Stage 2/{total_steps} — Found {len(universe):,} unique stores")
        bar.progress(45)

        # Stage 3: Score
        status.info(f"Stage 3/{total_steps} — Scoring all stores...")
        all_stores = portfolio + universe
        # Ensure poi_count and price_level exist on all stores
        for _s in all_stores:
            if "poi_count"   not in _s: _s["poi_count"]   = 0
            if "price_level" not in _s: _s["price_level"] = 0
        for s in all_stores:
            if "poi_count" not in s: s["poi_count"] = 0
            if "price_level" not in s: s["price_level"] = 0
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
        # Two-group scoring per Jaimin doc:
        # Group 1 (Current Coverage): Rating,Reviews,Affluence,POI,Sales,Lines
        # Group 2 (Scraped/Gap): Rating,Reviews,Affluence,POI only
        weights_cc  = st.session_state.get("admin_scoring_weights",
            {"rating":0.20,"reviews":0.25,"affluence":0.15,"poi":0.15,"sales":0.15,"lines":0.10})
        weights_gap = st.session_state.get("admin_scoring_weights_gap",
            {"rating":0.25,"reviews":0.25,"affluence":0.25,"poi":0.25})
        # Normalise weights to fractions
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
                    # Current Coverage group — uses all 6 signals
                    sal_n = min(1.0, _safe_num(s.get("annual_sales_usd",0)) / max_sales) if max_sales > 0 else 0.0
                    lin_n = min(1.0, _safe_num(s.get("lines_per_store",0))  / max_lines) if max_lines > 0 else 0.0
                    raw = (r_n   * wcc.get("rating",0.20) +
                           rv_n  * wcc.get("reviews",0.25) +
                           aff_n * wcc.get("affluence",0.15) +
                           poi_n * wcc.get("poi",0.15) +
                           sal_n * wcc.get("sales",0.15) +
                           lin_n * wcc.get("lines",0.10))
                else:
                    # Scraped/Gap group — Google signals only
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

        # ── Remove covered scraped stores from all_stores ─────────────────────
        # A scraped store marked "covered" means the portfolio already has it.



        # Keeping both creates duplicate rows with different scores/data.
        # Keep: all portfolio stores + scraped stores that are GAPS only.
        all_stores = [s for s in all_stores
                      if s.get("source") == "portfolio"
                      or s.get("coverage_status") == "gap"]
        # Rebuild gap_stores from updated all_stores
        gap_stores = [s for s in all_stores if s.get("coverage_status") == "gap"]

        # ── Enrich portfolio stores with Google data from matched scraped store ─
        # Use SCORING approach: distance + name similarity combined
        # place_id is only copied when there is a strong name match (>=50%)
        # to prevent wrong stores getting each other's Google data
        GOOGLE_FIELDS = ["rating","review_count","price_level",
                         "phone","opening_hours","website","business_status"]

        def _tok_sim(a, b):
            noise = {"trading","est","llc","co","ltd","trd","al","the","-","&",
                     "shopping","super","market","hypermarket","hyper"}
            a_tok = set(str(a).lower().split()) - noise
            b_tok = set(str(b).lower().split()) - noise
            if not a_tok or not b_tok: return 0.0
            return len(a_tok & b_tok) / max(len(a_tok | b_tok), 1)

        # Track which scraped store each portfolio store matched
        # to avoid copying same place_id to many portfolio stores
        used_place_ids = {}  # place_id -> portfolio store that claimed it

        for p in portfolio:
            p_name = str(p.get("store_name","") or "").strip()
            best_match = None
            best_score = -1

            for u in universe:
                if not (u.get("lat") and u.get("lng")): continue
                score = 0.0

                # Distance score
                if p.get("lat") and p.get("lng"):
                    dist = haversine_m(p["lat"],p["lng"],u["lat"],u["lng"])
                    if dist > 1000: continue   # too far
                    if dist <= 100:   score += 3.0
                    elif dist <= 300: score += 2.0
                    elif dist <= 500: score += 1.0

                # Name similarity score
                sim = _tok_sim(p_name, u.get("store_name",""))
                if sim >= 0.5: score += sim * 3   # strong weight on name



                elif sim >= 0.3: score += sim

                if score > best_score and score > 0:
                    best_score = score
                    best_match = u

            if best_match:
                # Copy Google metrics (not place_id yet — handle separately)
                for field in GOOGLE_FIELDS:
                    if best_match.get(field) and not p.get(field):
                        p[field] = best_match[field]
                if best_match.get("rating"):
                    p["rating"]       = best_match["rating"]
                if best_match.get("review_count"):
                    p["review_count"] = best_match["review_count"]
                # Copy place_id ONLY if strong name match — prevents wrong assignment
                # and only if this place_id hasn't been claimed by another portfolio store
                u_pid = best_match.get("place_id","")
                sim   = _tok_sim(p_name, best_match.get("store_name",""))
                if u_pid and sim >= 0.5 and u_pid not in used_place_ids:
                    p["place_id"]     = u_pid
                    used_place_ids[u_pid] = p.get("store_id","")
                # Borrow coordinates ONLY if portfolio store genuinely has no coords
                # Never overwrite valid original coordinates from the portfolio CSV
                if not (p.get("lat") and p.get("lng")) and best_match.get("lat") and sim >= 0.5:
                    p["lat"]           = best_match["lat"]
                    p["lng"]           = best_match["lng"]
                    p["geocode_fixed"] = True

        # ── Direct Google Places lookup for portfolio stores still missing rating ─
        # These are stores with valid coords not in the scraped universe
        # Use Places Text Search to fetch their Google data directly
        no_rating_port = [p for p in portfolio
                          if p.get("lat") and p.get("lng")
                          and not (p.get("rating") and float(p.get("rating") or 0) > 0)
                          and p.get("store_name")]
        if no_rating_port and api_key:
            status.info(f"Stage 4/{total_steps} — Fetching Google data for {len(no_rating_port)} portfolio stores not in scraped universe...")
            mkt_lat = (cfg["lat_min"] + cfg["lat_max"]) / 2
            mkt_lng = (cfg["lng_min"] + cfg["lng_max"]) / 2
            fetched = 0
            for p in no_rating_port:
                try:
                    _s = lambda v: str(v).strip() if v and str(v) not in ("nan","None","") else ""
                    name   = _s(p.get("store_name",""))
                    city   = _s(p.get("city","")) or _s(p.get("address",""))
                    query  = f"{name} {city}".strip() if city else name



                    if not query: continue
                    r = requests.get(
                        "https://maps.googleapis.com/maps/api/place/textsearch/json",
                        params={"query": query,
                                "location": f"{p['lat']},{p['lng']}",
                                "radius": "5000",
                                "key": api_key},
                        timeout=8
                    )
                    data = r.json()
                    if data.get("status") == "OK" and data.get("results"):
                        for res in data["results"]:
                            loc = res.get("geometry",{}).get("location",{})
                            rlat, rlng = loc.get("lat"), loc.get("lng")
                            if not (rlat and rlng): continue
                            # Only use if result is within 2km of the portfolio store
                            if haversine_m(p["lat"],p["lng"],rlat,rlng) > 2000:
                                continue
                            # Check name similarity
                            res_name = res.get("name","")
                            def _simple_sim(a, b):
                                noise = {"trading","est","llc","co","ltd","the","al","-","&"}
                                at = set(str(a).lower().split()) - noise
                                bt = set(str(b).lower().split()) - noise
                                return len(at&bt)/max(len(at|bt),1) if at and bt else 0
                            if _simple_sim(name, res_name) < 0.3:
                                continue
                            # Found a match — copy Google data
                            pid = res.get("place_id","")
                            if res.get("rating"):
                                p["rating"]       = float(res["rating"])
                            if res.get("user_ratings_total"):
                                p["review_count"] = int(res["user_ratings_total"])
                            if res.get("price_level"):
                                p["price_level"]  = int(res["price_level"])
                            if pid and pid not in used_place_ids:
                                p["place_id"]     = pid
                                used_place_ids[pid] = p.get("store_id","")
                            fetched += 1
                            break
                    time.sleep(0.05)
                except Exception:
                    pass
            if fetched:
                status.info(f"Stage 4/{total_steps} — Fetched Google data for {fetched} portfolio stores via direct lookup.")

        # ── Fix suspect portfolio stores using scraped universe ───────────────



        # For portfolio stores still flagged as suspect, try name-match against
        # scraped universe to borrow the correct Google coordinates
        still_suspect = [s for s in portfolio if s.get("geocode_suspect")]
        if still_suspect:
            status.info(f"Stage 4/{total_steps} — Attempting coordinate fix for {len(still_suspect)} suspect stores using scraped data...")
            coord_fixes = 0
            for p in still_suspect:
                best_sim   = 0
                best_score = -1
                best_match = None
                for u in universe:
                    if not (u.get("lat") and u.get("lng")): continue
                    sim = name_similarity(p.get("store_name",""), u.get("store_name",""))
                    if sim < 0.4: continue
                    # Combine name similarity with proximity if suspect store has coords
                    score = sim
                    if p.get("lat") and p.get("lng"):
                        dist = haversine_m(float(p["lat"]), float(p["lng"]),
                                           u["lat"], u["lng"])
                        if dist < 50000:   # within 50km bonus
                            score += (1 - dist/50000) * 0.5
                    if score > best_score:
                        best_score = score
                        best_sim   = sim
                        best_match = u
                if best_match:
                    # Only borrow coords from scraped store if portfolio store has none
                    if not (p.get("lat") and p.get("lng")):
                        p["original_lat"]    = p.get("original_lat", round(float(p.get("lat") or 0), 5))
                        p["original_lng"]    = p.get("original_lng", round(float(p.get("lng") or 0), 5))
                        p["lat"]             = best_match["lat"]
                        p["lng"]             = best_match["lng"]
                        p["geocode_suspect"] = False
                        p["geocode_fixed"]   = True
                    # Always copy Google data from matched scraped store
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
        rep_recommendation = None
        rep_mode      = cfg.get("rep_mode","fixed")
        daily_minutes = cfg.get("daily_minutes", 480)
        working_days  = cfg.get("working_days", 22)
        avg_speed     = cfg.get("avg_speed_kmh", 30)
        break_minutes = cfg.get("break_minutes",
            st.session_state.get("admin_rep_defaults",{}).get("break_minutes", 30))
        effective_daily = daily_minutes - break_minutes

        # ── Two-group normalisation + combination (Jaimin doc) ─────────────
        # Group 1 = Current Coverage (portfolio), Group 2 = Scraped/Gap
        # Normalise each group separately then COMBINE for routing
        priority_all = [s for s in all_stores
                        if s.get("size_tier") in ("Large","Medium","Small")
                        and s.get("lat") and s.get("lng")]

        # Separate by source
        group_cc  = [s for s in priority_all if s.get("source") == "portfolio"]
        group_gap = [s for s in priority_all if s.get("source") != "portfolio"]

        # Normalise each group independently 0-1
        def _normalise_group(stores):
            if not stores: return
            mx = max(s.get("score",0) for s in stores) or 1



            for s in stores:
                s["_norm_score"] = s.get("score",0) / mx

        _normalise_group(group_cc)
        _normalise_group(group_gap)

        if rep_mode == "recommended":
            # Combine both groups then take top 60% by normalised score
            # Per Jaimin: "top 60% of numeric coverage from combined ranking Current + Gap"
            combined = group_cc + group_gap
            combined_sorted = sorted(combined, key=lambda x: x.get("_norm_score",0), reverse=True)
            _store_pct = st.session_state.get("admin_rep_defaults",{}).get("store_select_pct", 60)
            n_select = max(1, round(len(combined_sorted) * _store_pct / 100))
            priority = combined_sorted[:n_select]
        else:
            # Fixed mode: all scored stores — rep capacity is the constraint
            priority = priority_all

        # Safety fallback
        if not priority:
            priority = priority_all
        if not priority:
            priority = [s for s in all_stores if s.get("lat") and s.get("lng")
                        and s.get("size_tier") in ("Large","Medium","Small")]

        current_reps  = cfg.get("rep_count", 0)

        if rep_mode == "recommended":
            status.info(f"Stage 6/{total_steps} — Calculating recommended rep count (time-based)...")

            rec_reps, total_mins, monthly_cap = recommended_reps_time_based(
                priority, daily_minutes, working_days, avg_speed
            )

            # ── City-bound zone clustering (Jaimin doc) ──────────────────────
            # Phase 1: Group stores into super-cities by 15km proximity
            # Phase 2: Merge under-threshold super-cities into nearest neighbour
            # Phase 3: Assign reps within each merged super-city
            zone_centres = []
            actual_reps  = 0
            if priority:
                status.info(f"Stage 6/{total_steps} — Grouping stores into super-cities (15km radius)...")
                # Tag every store with its super-city id
                supercities = group_cities_into_supercities(priority, radius_km=15.0)

                # Build rep territories using city-bound logic
                zone_centres, actual_reps = plan_reps_by_supercity(



                    supercities, priority,
                    daily_minutes=daily_minutes,
                    working_days=working_days,
                    target_util=0.80,
                    merge_threshold=0.70,
                )

                # Stores in priority not yet assigned = cross-city candidates
                # Only use priority stores — never assign the 40% below score threshold
                assign_cross_city_stores(
                    priority, zone_centres,
                    daily_minutes=daily_minutes,
                    working_days=working_days,
                    avg_speed_kmh=avg_speed,
                )

                min_util_pct = 70  # threshold used for merging

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

                # Apply minimum utilisation threshold in fixed mode too
                min_util_pct  = 40  # only remove truly under-utilised reps
                min_util_mins  = daily_minutes * working_days * min_util_pct / 100
                kept_zones_f   = [z for z in zone_centres if z.get("time_needed_min",0) >= min_util_mins]
                under_util     = [z for z in zone_centres if z.get("time_needed_min",0) <  min_util_mins]

                # Reassign stores from under-utilised zones to nearest kept zone
                if under_util and kept_zones_f:
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
        # Plan period driven by lowest visit frequency set in benchmarks
        # e.g. Small=1/mo → 1 month, Small=0.5/mo → 2 months, Small=0.33/mo → 3 months
        _bench      = st.session_state.get("admin_benchmarks", {})
        _freqs      = [
            float(_bench.get("large_visits",  4)),
            float(_bench.get("medium_visits", 2)),
            float(_bench.get("small_visits",  1)),
        ]
        min_freq    = min(f for f in _freqs if f > 0)
        plan_period = max(1, round(1 / min_freq)) if min_freq < 1 else 1

        # Build real calendar months from user-selected start month in Configure
        _start_year  = int(cfg.get("route_year",  datetime.date.today().year))
        _start_month = int(cfg.get("route_month", datetime.date.today().month))

        plan_months_ym = []
        for i in range(plan_period):
            mo = (_start_month - 1 + i) % 12 + 1
            yr = _start_year + ((_start_month - 1 + i) // 12)
            plan_months_ym.append((yr, mo))

        plan_month_keys   = [f"m{i+1}" for i in range(plan_period)]
        plan_month_labels = [datetime.date(yr, mo, 1).strftime("%B %Y")
                             for yr, mo in plan_months_ym]

        city_lat    = (cfg["lat_min"] + cfg["lat_max"]) / 2
        city_lng    = (cfg["lng_min"] + cfg["lng_max"]) / 2
        all_rep_ids = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))

        status.info(f"Stage 6b — Building {plan_period}-month route plan for {len(all_rep_ids)} reps...")

        # Clear ALL route fields BEFORE building routes
        for s in all_stores:



            s["assigned_day"]    = ""
            s["day_visit_order"] = 0
            for mk in plan_month_keys:
                s[f"{mk}_weeks"]  = []
                s[f"{mk}_visits"] = 0
            s["plan_visits"] = 0

        # Build day assignments
        for rep_id in all_rep_ids:
            try:
                rep_stores = [s for s in all_stores
                    if s.get("rep_id") == rep_id
                    and s.get("size_tier") in ("Large","Medium","Small")]
                if rep_stores:
                    build_daily_routes(rep_stores, daily_minutes=effective_daily,
                                       avg_speed_kmh=avg_speed, city_lat=city_lat, city_lng=city_lng)
            except Exception as e:
                status.warning(f"Route building warning for Rep {rep_id}: {e} — continuing...")
                for i, s in enumerate([s for s in all_stores
                        if s.get("rep_id")==rep_id
                        and s.get("size_tier") in ("Large","Medium","Small")]):
                    s["assigned_day"]    = WEEKDAYS[i % 5]
                    s["day_visit_order"] = (i // 5) + 1

        # Abstract week labels — no real calendar dates
        WEEK_LABELS = ["Week 1", "Week 2", "Week 3", "Week 4"]

        def pick_weeks(vpm):
            if vpm >= 4: return WEEK_LABELS           # weekly: all 4
            if vpm >= 2: return [WEEK_LABELS[0], WEEK_LABELS[2]]  # fortnightly: W1+W3
            if vpm >= 1: return [WEEK_LABELS[1]]      # monthly: W2
            return []

        # Assign abstract week labels — only valid assigned_day and size tier
        for s in all_stores:
            if not s.get("assigned_day") or s.get("assigned_day") == "":
                continue
            if s.get("size_tier") not in ("Large","Medium","Small"):
                s["plan_visits"] = 0
                continue

            day = s["assigned_day"]
            vpm = s.get("visits_per_month", 1)

            if vpm >= 1:
                weeks = pick_weeks(vpm)
                for mk in plan_month_keys:



                    s[f"{mk}_weeks"]  = [f"{w} - {day}" for w in weeks]
                    s[f"{mk}_visits"] = len(weeks)
                    s["plan_visits"] += len(weeks)
            else:
                total_visits = max(1, round(vpm * plan_period))
                order        = s.get("day_visit_order", 1)
                visit_count  = 0
                for i, mk in enumerate(plan_month_keys):
                    if visit_count >= total_visits: break
                    if (order + i) % plan_period == 0 or                        (i == len(plan_month_keys)-1 and visit_count == 0):
                        s[f"{mk}_weeks"]  = [f"Week 2 - {day}"]
                        s[f"{mk}_visits"] = 1
                        s["plan_visits"] += 1
                        visit_count      += 1

        # Clear stores not in route
        for s in all_stores:
            if not s.get("assigned_day") or s.get("size_tier") not in ("Large","Medium","Small"):
                s["assigned_day"]    = ""
                s["day_visit_order"] = 0
                s["plan_visits"]     = 0
                for mk in plan_month_keys:
                    s[f"{mk}_dates"]  = []
                    s[f"{mk}_visits"] = 0

        # Store plan metadata
        # Recalculate zone_centres time_needed_min NOW that plan_visits is set
        # Must run AFTER week assignment so plan_visits > 0 filters work correctly
        for zc in zone_centres:
            rid = zc["zone"]
            final_stores = [s for s in all_stores
                            if s.get("rep_id") == rid
                            and s.get("lat") and s.get("lng")
                            and s.get("plan_visits", 0) > 0]
            if final_stores:
                final_t, final_d = calc_zone_monthly_time(
                    final_stores, avg_speed, daily_minutes)
                zc["time_needed_min"] = final_t
                zc["utilisation_pct"] = round(final_t / (daily_minutes * working_days) * 100)
                zc["daily_breakdown"] = final_d
                zc["store_count"]     = len(final_stores)

        st.session_state["route_plan_months"] = {
            "plan_period":   plan_period,
            "month_keys":    plan_month_keys,
            "month_labels":  plan_month_labels,



            "months_ym":     plan_months_ym,
        }
        # ── Post-route rebalancing ─────────────────────────────────────────────
        # Some stores were dropped by daily budget — try to redistribute them
        # to underloaded reps, and enforce 110% daily cap per Jaimin doc

        effective_cap_110 = effective_daily * 1.10  # 110% daily max

        # Build per-rep daily time map
        def rep_day_time(stores_list, rep, day):
            return sum(s.get("visit_duration_min",25)
                       for s in stores_list
                       if s.get("rep_id")==rep and s.get("assigned_day")==day
                       and s.get("plan_visits",0) > 0)

        def rep_monthly_time(stores_list, rep):
            return sum(s.get("plan_visits",0) * s.get("visit_duration_min",25)
                       for s in stores_list
                       if s.get("rep_id")==rep and s.get("plan_visits",0)>0)

        # Find stores dropped by daily budget — assigned_day="" but rep_id>0
        dropped = [s for s in all_stores
                   if s.get("rep_id",0) > 0
                   and not s.get("assigned_day","")
                   and s.get("size_tier") in ("Large","Medium","Small")
                   and s.get("lat") and s.get("lng")]

        all_rep_ids_post = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0)>0))

        if dropped and all_rep_ids_post:
            # Sort dropped by score desc — try to place highest-priority first
            dropped.sort(key=lambda x: x.get("score",0), reverse=True)
            for s in dropped:
                visit_t = s.get("visit_duration_min", 25)
                # Find rep+day combo with most remaining capacity under 110%
                best_rep, best_day, best_remaining = None, None, -1
                for rid in all_rep_ids_post:
                    for day in WEEKDAYS:
                        used = rep_day_time(all_stores, rid, day)
                        remaining = effective_cap_110 - used
                        if remaining >= visit_t and remaining > best_remaining:
                            best_remaining = remaining
                            best_rep = rid
                            best_day = day
                if best_rep and best_day:
                    s["rep_id"]          = best_rep
                    s["assigned_day"]    = best_day



                    s["day_visit_order"] = 99
                    # Assign plan weeks
                    vpm   = s.get("visits_per_month", 1)
                    day_n = best_day
                    if vpm >= 1:
                        wks = pick_weeks(vpm)
                        for mk in plan_month_keys:
                            s[f"{mk}_weeks"]  = [f"{w} - {day_n}" for w in wks]
                            s[f"{mk}_visits"] = len(wks)
                            s["plan_visits"]  = len(wks) * plan_period
                    elif vpm > 0:
                        s[f"{plan_month_keys[0]}_weeks"]  = [f"Week 2 - {day_n}"]
                        s[f"{plan_month_keys[0]}_visits"] = 1
                        s["plan_visits"] = 1

        # Enforce 110% daily cap — move excess stores to other reps
        for rid in all_rep_ids_post:
            for day in WEEKDAYS:
                day_stores = [s for s in all_stores
                              if s.get("rep_id")==rid
                              and s.get("assigned_day")==day
                              and s.get("plan_visits",0)>0]
                # Sort by score asc — move lowest-score excess first
                day_stores_sorted = sorted(day_stores, key=lambda x: x.get("score",0))
                day_used = sum(s.get("visit_duration_min",25) for s in day_stores_sorted)
                for s in day_stores_sorted:
                    if day_used <= effective_cap_110:
                        break
                    vt = s.get("visit_duration_min", 25)
                    # Find another rep+day with capacity
                    found = False
                    for other_rid in all_rep_ids_post:
                        if other_rid == rid: continue
                        for other_day in WEEKDAYS:
                            used_other = rep_day_time(all_stores, other_rid, other_day)
                            if effective_cap_110 - used_other >= vt:
                                s["rep_id"]       = other_rid
                                s["assigned_day"] = other_day
                                day_used -= vt
                                found = True
                                break
                        if found: break

        # ── Final metrics recalculation ──────────────────────────────────────────
        routed_stores = [s for s in all_stores if s.get("plan_visits",0) > 0 and s.get("rep_id",0) > 0]
        if routed_stores:
            _, final_total_mins, final_monthly_cap = recommended_reps_time_based(



                routed_stores, effective_daily, working_days, avg_speed
            )
            rep_time_map = {}
            for s in routed_stores:
                rid = s.get("rep_id", 0)
                rep_time_map[rid] = rep_time_map.get(rid, 0) + (
                    s.get("plan_visits", 0) * s.get("visit_duration_min", 25) / 2
                )
            kept_reps = list(rep_time_map.keys())

                    # Update rep_recommendation
            if rep_recommendation:
                rep_recommendation["total_minutes_needed"] = round(final_total_mins)
                rep_recommendation["monthly_cap_per_rep"]  = round(final_monthly_cap)
                rep_recommendation["recommended_reps"]     = len(kept_reps) if kept_reps else len(rep_time_map)
                # zone_centres time_needed_min already updated by recalc block above
                # (exec+travel via calc_zone_monthly_time) — do not overwrite here

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
                    # Capture price_level from Place Details — not returned by Nearby Search
                    if result.get("price_level") is not None:
                        store["price_level"] = int(result["price_level"])
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
