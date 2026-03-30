import streamlit as st
import pandas as pd
import time
import math
import requests
import random
import datetime

st.set_page_config(page_title="Run Pipeline - Coverage Tool", page_icon="📤", layout="wide")

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

    # Calibrate estimates based on area density
    # Large radius = sparse/rural area — fewer pages per tile, fewer stores per tile
    if radius_m >= 20000:
        avg_pages           = 1.2   # rural — most tiles return only 1 page
        stores_per_tile     = 8     # sparse
    elif radius_m >= 8000:
        avg_pages           = 1.5   # suburban
        stores_per_tile     = 12
    else:
        avg_pages           = 1.8   # dense city
        stores_per_tile     = 18

    # Scraping
    scrape_calls      = round(n_tiles * n_categories * avg_pages)
    scrape_cost       = scrape_calls * PRICE_NEARBY_PER_CALL
    scrape_time       = scrape_calls * 0.25 + n_tiles * n_categories * (avg_pages-1) * 2

    # Geocoding
    geocode_calls     = n_portfolio  # estimate — actual count may be lower if stores have existing coordinates
    geocode_cost      = geocode_calls * PRICE_GEOCODE_PER_CALL
    geocode_time      = geocode_calls * 0.1

    # Enrichment
    # Estimate universe size for scope
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

def geocode_store(address, city, api_key, district="", region=""):
    """Geocode using address + optional district and region for better accuracy."""
    try:
        parts = [p for p in [address, district, city, region] if p and p.strip()]
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
    Calculate recommended rep count.
    Uses plan_visits if available (post route-builder), else visits_per_month.
    Returns (recommended_reps, total_minutes_needed_per_month, minutes_per_rep_per_month).
    """
    if not priority_stores:
        return 1, 0.0, 0.0

    monthly_capacity = daily_minutes * working_days

    # Use plan_visits if route builder has already run, else visits_per_month
    has_plan = any(s.get("plan_visits") is not None for s in priority_stores)
    if has_plan:
        # plan_visits is 2-month total — divide by 2 for monthly equivalent
        total_visit_time = sum(
            s.get("plan_visits", 0) * s.get("visit_duration_min", 25) / 2
            for s in priority_stores
            if s.get("plan_visits", 0) > 0
        )
    else:
        total_visit_time = sum(
            s.get("visit_duration_min", 25) * s.get("visits_per_month", 1)
            for s in priority_stores
        )

    rec_reps = max(1, math.ceil(total_visit_time / monthly_capacity))
    return rec_reps, round(total_visit_time), round(monthly_capacity)


def assign_size_tier(store, category_percentiles, visit_benchmarks, size_percentiles):
    """
    Assign size tier (Large/Medium/Small/Occasional) based on score percentile within category.
    Occasional = bottom W% — visited once every 2 months (0.5 visits/month), locked.
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

    large_pct      = size_percentiles.get("large_pct",      20)
    medium_pct     = size_percentiles.get("medium_pct",     40)
    small_pct      = size_percentiles.get("small_pct",      30)
    occasional_pct = size_percentiles.get("occasional_pct", 10)

    # top X% = Large, next Y% = Medium, next Z% = Small, bottom W% = Occasional
    # If occasional_pct = 0, all bottom stores fall into Small
    if pct >= (100 - large_pct):
        tier = "Large"
    elif pct >= (100 - large_pct - medium_pct):
        tier = "Medium"
    elif pct >= occasional_pct:
        tier = "Small"
    else:
        tier = "Occasional" if occasional_pct > 0 else "Small"

    # Get visit benchmarks for this category
    bench = visit_benchmarks.get(cat, visit_benchmarks.get("default", {
        "large_visits":4,"large_duration":40,
        "medium_visits":2,"medium_duration":25,
        "small_visits":1,"small_duration":15,
        "occasional_duration":15,
    }))

    if tier == "Large":
        visits   = bench.get("large_visits",      4)
        duration = bench.get("large_duration",     40)
    elif tier == "Medium":
        visits   = bench.get("medium_visits",      2)
        duration = bench.get("medium_duration",    25)
    elif tier == "Small":
        visits   = bench.get("small_visits",       1)
        duration = bench.get("small_duration",     15)
    else:  # Occasional — locked at 0.5
        visits   = 0.5
        duration = bench.get("occasional_duration", 15)

    return tier, visits, duration


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

import calendar as cal_module

WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

def get_month_weekdays(year, month):
    """
    Returns dict: {weekday_name: [date, date, ...]} for all occurrences in the month.
    e.g. {"Monday": [date(2025,6,2), date(2025,6,9), ...], ...}
    """
    result = {d: [] for d in WEEKDAYS}
    num_days = cal_module.monthrange(year, month)[1]
    for day in range(1, num_days + 1):
        d = datetime.date(year, month, day)
        name = WEEKDAYS[d.weekday()] if d.weekday() < 5 else None
        if name:
            result[name].append(d)
    return result


def build_daily_routes(rep_stores, year, month, daily_minutes, avg_speed_kmh, city_lat, city_lng):
    """
    Assign each store to a fixed day of the week and build daily visit sequences.

    Returns list of store dicts enriched with:
        assigned_day        — "Monday" etc
        visit_dates         — list of actual date strings for this month
        day_visit_order     — position within that day's route
        day_travel_time_min — cumulative travel time for this day

    Logic:
    1. Sort stores by visits_per_month desc, then score desc
    2. Assign stores to weekdays geographically using k-means into 5 day-clusters
    3. Within each day sort by nearest-neighbour from city centre
    4. Validate daily time budget — if exceeded move lowest-score store to next day
    5. Build visit_dates from actual calendar occurrences
    """
    if not rep_stores:
        return []

    month_days = get_month_weekdays(year, month)

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
# ── STEP 2b: POI ENRICHMENT CONFIG ──────────────────────────────────────────
st.markdown('<div class="section-title">2b. Nearby POI enrichment (optional)</div>', unsafe_allow_html=True)
st.caption("Count points of interest within a radius of each store. Used as a location quality signal in scoring. Same pattern as phone/opening hours enrichment.")

poi_scope_label = st.radio(
    "Which stores to enrich with POI count",
    options=["None — skip POI enrichment",
             "Top N stores by score",
             "All gap stores",
             "All scraped stores"],
    index=0, horizontal=True, key="poi_scope_radio"
)
poi_scope_map = {
    "None — skip POI enrichment": "none",
    "Top N stores by score":       "top_n",
    "All gap stores":              "gaps_only",
    "All scraped stores":          "all",
}
poi_scope = poi_scope_map[poi_scope_label]
st.session_state["enrich_poi_scope"] = poi_scope

poi_count_val = 100
if poi_scope != "none":
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        poi_radius_val = st.number_input(
            "POI search radius (metres)", min_value=100, max_value=2000, value=500, step=100,
            help="How far from each store to count POIs. 500m is a 5-10 min walk."
        )
        st.session_state["enrich_poi_radius"] = poi_radius_val
    with col_p2:
        if poi_scope == "top_n":
            poi_count_val = st.slider("Number of top stores to enrich", 10, 500, 100, step=10)
            st.session_state["poi_count"] = poi_count_val
        else:
            st.info("Will enrich all stores matching the selected scope.")
    poi_cost = poi_count_val * PRICE_NEARBY_PER_CALL if poi_scope == "top_n" else 0
    st.caption(f"Estimated POI enrichment cost: ~${poi_cost:.2f} (included in pre-flight estimate below)")

st.markdown("---")

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
    # ── Normal pre-flight card — pure native Streamlit, no custom HTML ────────
    colour_icons  = {"green": "✅", "amber": "⚠️", "red": "🔴"}
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
        st.info("💡 " + sug)

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
        dry_priority  = [s for s in all_stores if s.get("size_tier") in ("Large","Medium","Small","Occasional") and s.get("lat") and s.get("lng")]
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

        # Build 2-month route plan for dry run
        dry_year   = cfg.get("route_year",   datetime.date.today().year)
        dry_month1 = cfg.get("route_month1", datetime.date.today().month)
        dry_month2 = dry_month1 % 12 + 1
        dry_year2  = dry_year + (1 if dry_month2 == 1 else 0)
        dry_city_lat = (cfg["lat_min"] + cfg["lat_max"]) / 2
        dry_city_lng = (cfg["lng_min"] + cfg["lng_max"]) / 2
        dry_rep_ids  = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))
        dry_speed    = cfg.get("avg_speed_kmh", 30)
        dry_daily    = cfg.get("daily_minutes", 480)
        m1_key  = datetime.date(dry_year,  dry_month1, 1).strftime("%b").lower()
        m2_key  = datetime.date(dry_year2, dry_month2, 1).strftime("%b").lower()
        m1_name = datetime.date(dry_year,  dry_month1, 1).strftime("%B %Y")
        m2_name = datetime.date(dry_year2, dry_month2, 1).strftime("%B %Y")

        for rep_id in dry_rep_ids:
            try:
                rep_s = [s for s in all_stores if s.get("rep_id")==rep_id
                         and s.get("size_tier") in ("Large","Medium","Small","Occasional")]
                if rep_s:
                    build_daily_routes(rep_s, dry_year, dry_month1, dry_daily, dry_speed, dry_city_lat, dry_city_lng)
            except Exception:
                for i, s in enumerate([s for s in all_stores if s.get("rep_id")==rep_id]):
                    s["assigned_day"]    = WEEKDAYS[i % 5]
                    s["day_visit_order"] = (i // 5) + 1

        m1_days = get_month_weekdays(dry_year,  dry_month1)
        m2_days = get_month_weekdays(dry_year2, dry_month2)

        def _pick(occ, vpm):
            if not occ: return []
            if vpm >= len(occ): return occ
            if vpm >= 2: return occ[0:1] + (occ[2:3] if len(occ)>2 else occ[-1:])
            return [occ[len(occ)//2]]

        for s in all_stores:
            if not s.get("assigned_day"):
                s[m1_key+"_dates"]=[]; s[m1_key+"_visits"]=0
                s[m2_key+"_dates"]=[]; s[m2_key+"_visits"]=0
                s["plan_visits"]=0; continue
            day = s["assigned_day"]; vpm = s.get("visits_per_month", 1)
            occ1 = m1_days.get(day,[]); occ2 = m2_days.get(day,[])
            if s.get("size_tier") == "Occasional":
                if s.get("day_visit_order",1) % 2 == 1:
                    m1d = [occ1[len(occ1)//2]] if occ1 else []; m2d = []
                else:
                    m1d = []; m2d = [occ2[len(occ2)//2]] if occ2 else []
            else:
                m1d = _pick(occ1, vpm); m2d = _pick(occ2, vpm)
            s[m1_key+"_dates"]  = [d.strftime("%b %d") for d in m1d]
            s[m1_key+"_visits"] = len(m1d)
            s[m2_key+"_dates"]  = [d.strftime("%b %d") for d in m2d]
            s[m2_key+"_visits"] = len(m2d)
            s["plan_visits"]    = len(m1d) + len(m2d)

        for s in all_stores:
            if "assigned_day" not in s:
                s["assigned_day"]=""; s["day_visit_order"]=0; s["plan_visits"]=0
                s[m1_key+"_dates"]=[]; s[m1_key+"_visits"]=0
                s[m2_key+"_dates"]=[]; s[m2_key+"_visits"]=0

        st.session_state["route_plan_months"] = {
            "month1":m1_name,"month2":m2_name,"m1_key":m1_key,"m2_key":m2_key}

        st.session_state["run_results"] = {
            "all_stores":all_stores,"gap_stores":gap_stores,
            "coverage_rate_before":round(len(base)/max(len(all_stores),1)*100,1),
            "coverage_rate_after":round(covered_n/max(len(all_stores),1)*100,1),
            "portfolio":[s for s in all_stores if s["source"]=="portfolio"],
            "universe":[s for s in all_stores if s["source"]=="scraped"],
            "rep_recommendation": dry_rec,
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

        for s in needs_geocode:
            district = _get_location_field(s, DISTRICT_COLS)
            region   = _get_location_field(s, REGION_COLS)
            lat, lng = geocode_store(s.get("address",""), s.get("city",""), api_key, district, region)
            s["lat"], s["lng"] = lat, lng
            time.sleep(0.05)

        geocode_ok   = sum(1 for s in portfolio if s.get("lat") and s.get("lng"))
        geocode_fail = len(portfolio) - geocode_ok
        status.info(
            f"Stage 1/{total_steps} — Complete: {len(has_coords)} had coordinates · "
            f"{len(needs_geocode) - geocode_fail} geocoded · {geocode_fail} failed"
        )
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
                        universe.append({
                            "store_id":pid,"place_id":pid,
                            "store_name":place.get("name",""),
                            "address":place.get("vicinity",""),"city":cfg.get("city",""),
                            "lat":loc.get("lat"),"lng":loc.get("lng"),
                            "rating":float(place.get("rating",0) or 0),
                            "review_count":int(place.get("user_ratings_total",0) or 0),
                            "price_level":int(place.get("price_level",0) or 0),
                            "business_status":place.get("business_status","OPERATIONAL"),
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
        def _score_store(s):
            try:
                r_n    = min(1.0, _safe_num(s.get("rating",0)) / 5)
                rv_n   = math.log1p(_safe_num(s.get("review_count",0))) / math.log1p(max_rev) if max_rev > 1 else 0.0
                pl_raw = _safe_num(s.get("price_level",0))
                aff_n  = pl_raw / 4 if pl_raw > 0 else 0.5
                poi_raw= _safe_num(s.get("poi_count",0))
                poi_n  = math.log1p(poi_raw) / math.log1p(max_poi) if max_poi > 1 else 0.0
                sal_n  = min(1.0, _safe_num(s.get("annual_sales_usd",0)) / max_sales) if (s.get("covered") and max_sales > 0) else 0.0
                lin_n  = min(1.0, _safe_num(s.get("lines_per_store",0))  / max_lines) if (s.get("covered") and max_lines > 0) else 0.0
                raw = (
                    r_n   * _safe_num(weights.get("rating",    0.20)) +
                    rv_n  * _safe_num(weights.get("reviews",   0.25)) +
                    aff_n * _safe_num(weights.get("affluence", 0.10)) +
                    poi_n * _safe_num(weights.get("poi",       0.15)) +
                    sal_n * _safe_num(weights.get("sales",     0.15)) +
                    lin_n * _safe_num(weights.get("lines",     0.15))
                )
                if not math.isfinite(raw): return 0
                return min(100, max(0, round(raw * 100)))
            except Exception:
                return 0

        for s in all_stores:
            s["score"] = _score_store(s)
        bar.progress(55)

        # Stage 4: Gap match
        status.info(f"Stage 4/{total_steps} — Matching coverage gaps...")

        # Read matching settings from Admin
        match_cfg      = st.session_state.get("admin_matching", {})
        base_radius    = match_cfg.get("base_radius_m",       100)
        fuzzy_radius   = match_cfg.get("fuzzy_radius_m",      150)
        fuzzy_thresh   = match_cfg.get("fuzzy_threshold_pct",  60) / 100

        def name_similarity(a, b):
            """Simple character overlap similarity between two store names."""
            a = str(a).lower().strip()
            b = str(b).lower().strip()
            if not a or not b: return 0.0
            # Remove common words that add noise
            for w in ["supermercado","super","mercado","hipermercado","hiper","atacado","atacadao","ltda","eireli","me "]:
                a = a.replace(w,""); b = b.replace(w,"")
            a = a.strip(); b = b.strip()
            if not a or not b: return 0.0
            # Bigram similarity
            def bigrams(s): return set(s[i:i+2] for i in range(len(s)-1))
            ba, bb = bigrams(a), bigrams(b)
            if not ba or not bb: return 0.0
            return len(ba & bb) / max(len(ba | bb), 1)

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

            # Match 3 + 4: distance-based
            if not matched:
                for p in covered_p:
                    dist = haversine_m(u["lat"],u["lng"],p["lat"],p["lng"])
                    # Match 3: within base radius — always covered
                    if dist <= base_radius:
                        matched = True
                        break
                    # Match 4: within fuzzy radius — only if names are similar enough
                    if dist <= fuzzy_radius:
                        sim = name_similarity(u.get("store_name",""), p.get("store_name",""))
                        if sim >= fuzzy_thresh:
                            matched = True
                            break

            u["covered"]         = matched
            u["coverage_status"] = "covered" if matched else "gap"

        for p in portfolio: p["coverage_status"] = "covered"

        # Log matching summary
        n_covered = sum(1 for u in universe if u.get("covered"))
        n_gap     = sum(1 for u in universe if not u.get("covered"))
        status.info(
            f"Stage 4/{total_steps} — Coverage matching complete: "
            f"{n_covered} covered · {n_gap} gaps "
            f"(base radius: {base_radius}m · fuzzy: {fuzzy_radius}m @ {int(fuzzy_thresh*100)}%)"
        )
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
        priority = [s for s in all_stores if s.get("size_tier") in ("Large","Medium","Small","Occasional") and s.get("lat") and s.get("lng")]
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

            # Apply minimum utilisation threshold
            min_util_pct = cfg.get("min_utilisation_pct",
                st.session_state.get("admin_rep_defaults",{}).get("min_utilisation_pct", 60))
            min_util_mins  = monthly_cap * min_util_pct / 100
            kept_zones     = [z for z in zone_centres if z.get("time_needed_min",0) >= min_util_mins]
            removed_zones  = [z for z in zone_centres if z.get("time_needed_min",0) <  min_util_mins]
            zone_centres   = kept_zones
            actual_reps    = len(zone_centres)

            # Reassign stores from removed zones to nearest kept zone
            if removed_zones and kept_zones:
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

                # Apply minimum utilisation threshold in fixed mode too
                min_util_pct  = cfg.get("min_utilisation_pct",
                    st.session_state.get("admin_rep_defaults",{}).get("min_utilisation_pct",60))
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

        # ── Build 2-month rolling route plan ──────────────────────────────────
        route_year   = cfg.get("route_year",  datetime.date.today().year)
        route_month1 = cfg.get("route_month1", datetime.date.today().month)
        # Month 2 = next calendar month
        route_month2 = route_month1 % 12 + 1
        route_year2  = route_year + (1 if route_month2 == 1 else 0)

        city_lat    = (cfg["lat_min"] + cfg["lat_max"]) / 2
        city_lng    = (cfg["lng_min"] + cfg["lng_max"]) / 2
        all_rep_ids = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))

        import calendar as _cal
        m1_name = datetime.date(route_year,  route_month1, 1).strftime("%B %Y")
        m2_name = datetime.date(route_year2, route_month2, 1).strftime("%B %Y")
        status.info(f"Stage 6b — Building 2-month route plan: {m1_name} + {m2_name} for {len(all_rep_ids)} reps...")

        # Assign Occasional stores: split evenly between month 1 and month 2 by geography
        # First handle all non-occasional stores — build month 1 routes to get day assignments
        for rep_id in all_rep_ids:
            try:
                rep_stores = [s for s in all_stores
                    if s.get("rep_id") == rep_id
                    and s.get("size_tier") in ("Large","Medium","Small","Occasional")]
                if rep_stores:
                    build_daily_routes(rep_stores, route_year, route_month1, daily_minutes, avg_speed, city_lat, city_lng)
            except Exception as e:
                status.warning(f"Route building warning for Rep {rep_id}: {e} — continuing...")
                for i, s in enumerate([s for s in all_stores if s.get("rep_id")==rep_id]):
                    s["assigned_day"]    = WEEKDAYS[i % 5]
                    s["day_visit_order"] = (i // 5) + 1

        # Build month 1 dates for all tiers
        m1_days = get_month_weekdays(route_year,  route_month1)
        m2_days = get_month_weekdays(route_year2, route_month2)
        m1_key  = datetime.date(route_year,  route_month1, 1).strftime("%b").lower()
        m2_key  = datetime.date(route_year2, route_month2, 1).strftime("%b").lower()

        for s in all_stores:
            if not s.get("assigned_day"):
                s[m1_key+"_dates"] = []; s[m1_key+"_visits"] = 0
                s[m2_key+"_dates"] = []; s[m2_key+"_visits"] = 0
                s["plan_visits"] = 0
                continue

            day  = s["assigned_day"]
            vpm  = s.get("visits_per_month", 1)
            tier = s.get("size_tier","")

            occ1 = m1_days.get(day, [])
            occ2 = m2_days.get(day, [])

            if tier == "Occasional":
                # 0.5 visits/month = 1 visit across the 2-month window
                # Assign to month 1 or month 2 based on day_visit_order (alternate)
                if s.get("day_visit_order", 1) % 2 == 1:
                    # Month 1
                    mid = len(occ1) // 2
                    m1_dates = [occ1[mid]] if occ1 else []
                    m2_dates = []
                else:
                    # Month 2
                    mid = len(occ2) // 2
                    m1_dates = []
                    m2_dates = [occ2[mid]] if occ2 else []
            else:
                # Standard: vpm >= 1
                def pick_dates(occurrences, vpm):
                    if not occurrences: return []
                    if vpm >= len(occurrences): return occurrences
                    if vpm >= 2:
                        return occurrences[0:1] + (occurrences[2:3] if len(occurrences) > 2 else occurrences[-1:])
                    mid = len(occurrences) // 2
                    return [occurrences[mid]]
                m1_dates = pick_dates(occ1, vpm)
                m2_dates = pick_dates(occ2, vpm)

            s[m1_key+"_dates"]  = [d.strftime("%b %d") for d in m1_dates]
            s[m1_key+"_visits"] = len(m1_dates)
            s[m2_key+"_dates"]  = [d.strftime("%b %d") for d in m2_dates]
            s[m2_key+"_visits"] = len(m2_dates)
            s["plan_visits"]    = len(m1_dates) + len(m2_dates)

        # Stores not in route
        for s in all_stores:
            if "assigned_day" not in s:
                s["assigned_day"]       = ""
                s["day_visit_order"]    = 0
                s[m1_key+"_dates"]      = []
                s[m1_key+"_visits"]     = 0
                s[m2_key+"_dates"]      = []
                s[m2_key+"_visits"]     = 0
                s["plan_visits"]        = 0

        # Store plan metadata in results
        st.session_state["route_plan_months"] = {
            "month1": m1_name, "month2": m2_name,
            "m1_key": m1_key,  "m2_key": m2_key,
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

            # Apply 60% utilisation threshold — remove under-utilised reps
            min_util_pct  = cfg.get("min_utilisation_pct",
                st.session_state.get("admin_rep_defaults",{}).get("min_utilisation_pct", 60))
            min_util_mins = final_monthly_cap * min_util_pct / 100

            under_util_reps = [rid for rid, t in rep_time_map.items() if t < min_util_mins]
            kept_reps       = [rid for rid, t in rep_time_map.items() if t >= min_util_mins]

            if under_util_reps and kept_reps:
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
                    f"{enriched} updated | ⏱ {fmt_time(rem).replace('~','')} remaining"
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
                    f"{i+1}/{len(poi_candidates)} stores | ⏱ {fmt_time(rem).replace('~','')} remaining"
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
            f"✅ Pipeline complete in {actual_time} · actual cost ~${actual_cost:.2f} · "
            f"{len(all_stores):,} stores scored · {len(gap_stores):,} gaps found{enrich_msg}. "
            f"Open Results in the sidebar."
        )
