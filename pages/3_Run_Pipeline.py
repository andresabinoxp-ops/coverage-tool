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

st.html("""
<div class="page-header">
    <h2>  Run Pipeline</h2>



    <p>Upload your portfolio, configure enrichment, review the full cost estimate &mdash; then run</p>
</div>
""")

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

# ── Performance helpers ──────────────────────────────────────────────────────
def _api_retry(fn, *args, max_retries=3, base_delay=1.0, **kwargs):
    """Call fn(*args, **kwargs) with exponential-backoff retry on failure."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == max_retries - 1:
                return None
            time.sleep(base_delay * (2 ** attempt))
    return None

def _build_spatial_grid(stores, cell_size_deg=0.001):
    """Build a dict grid for O(1) proximity lookups instead of O(N) scans.
    cell_size_deg ~111m at equator — matches the 100m dedup threshold."""
    grid = {}
    for s in stores:
        lat, lng = float(s.get("lat", 0) or 0), float(s.get("lng", 0) or 0)
        if not lat or not lng:
            continue
        cell = (round(lat / cell_size_deg), round(lng / cell_size_deg))
        if cell not in grid:
            grid[cell] = []
        grid[cell].append(s)
    return grid

def _is_duplicate_spatial(lat, lng, grid, threshold_m=100, cell_size_deg=0.001):
    """Check if (lat,lng) is within threshold_m of any store in the spatial grid.
    Only checks the 9 neighbouring cells — O(1) average instead of O(N)."""
    cell_lat = round(lat / cell_size_deg)
    cell_lng = round(lng / cell_size_deg)
    for dlat in (-1, 0, 1):
        for dlng in (-1, 0, 1):
            for s in grid.get((cell_lat + dlat, cell_lng + dlng), []):
                if haversine_m(lat, lng, float(s["lat"]), float(s["lng"])) < threshold_m:
                    return True
    return False

CHECKPOINT_BATCH_SIZE = 100  # save progress every N stores

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
                    "fields":"formatted_phone_number,opening_hours,website,formatted_address,price_level,rating,user_ratings_total",
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
    for _it in range(iterations):
        for i,p in enumerate(points):
            dists = [haversine_m(p[0],p[1],c[0],c[1]) for c in centroids]
            labels[i] = dists.index(min(dists))

        # Re-seed empty clusters by splitting the largest cluster's furthest point
        cluster_sizes = [0] * k
        for lbl in labels:
            cluster_sizes[lbl] += 1
        for j in range(k):
            if cluster_sizes[j] == 0:
                # Find largest cluster
                biggest = max(range(k), key=lambda c: cluster_sizes[c])
                if cluster_sizes[biggest] <= 1:
                    continue
                # Pick the point furthest from the biggest cluster's centroid
                big_pts = [i for i in range(len(points)) if labels[i] == biggest]
                furthest = max(big_pts, key=lambda i: haversine_m(
                    points[i][0], points[i][1],
                    centroids[biggest][0], centroids[biggest][1]))
                labels[furthest] = j
                centroids[j] = points[furthest]
                cluster_sizes[biggest] -= 1
                cluster_sizes[j] = 1

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

    # Return exec+travel as total_minutes_needed (not exec only)
    return est_reps, round(total_minutes), round(monthly_capacity)

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



def assign_cluster_to_stores(stores, cluster_definitions):
    """
    Assign cluster_id to each store based on nearest cluster centroid.
    Uses haversine distance — no city name matching needed.
    """
    if not cluster_definitions or not stores:
        for s in stores:
            s["cluster_id"]   = 0
            s["cluster_name"] = "Unassigned"
        return stores
    import math as _math
    def _hav(la1,ln1,la2,ln2):
        R=6371; p=_math.pi/180
        a=(_math.sin((la2-la1)*p/2)**2+
           _math.cos(la1*p)*_math.cos(la2*p)*_math.sin((ln2-ln1)*p/2)**2)
        return 2*R*_math.asin(_math.sqrt(max(0,a)))
    for s in stores:
        try:
            slat = float(s.get("lat") or 0)
            slng = float(s.get("lng") or 0)
            if not slat or not slng:
                s["cluster_id"] = 0; s["cluster_name"] = "Unassigned"; continue
            nearest = min(cluster_definitions,
                key=lambda c: _hav(slat, slng, c["centre_lat"], c["centre_lng"]))
            s["cluster_id"]   = nearest["cluster_id"]
            s["cluster_name"] = nearest["name"]
        except Exception:
            s["cluster_id"] = 0; s["cluster_name"] = "Unassigned"
    return stores

def should_exclude_low_value_area(stores_in_area, min_stores, max_score):
    """
    Returns True if this geographic area should be excluded from routing.
    Rule: fewer than min_stores AND average score below max_score.
    Both conditions must be true (AND logic).
    """
    n = len(stores_in_area)
    if n >= min_stores:
        return False
    avg = sum(float(s.get("score",0) or 0) for s in stores_in_area) / max(n,1)
    return avg < max_score



def _map_biz_status(raw):
    """Map raw Google business_status to clean display value."""
    m = {
        "OPERATIONAL":          "Active",
        "CLOSED_PERMANENTLY":   "Closed",
        "CLOSED_TEMPORARILY":   "Temporarily Closed",
    }
    return m.get(str(raw).upper().strip(), "Active" if not raw else raw.title())

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

        # Travel = inter-store only (store 1 → 2 → ... → N)
        # First leg (depot → store 1) and last leg (store N → depot) excluded:
        # rep's working day starts when they arrive at the first store.
        travel_t = 0.0
        for i in range(1, len(day_stores)):
            s_prev = day_stores[i - 1]
            s_curr = day_stores[i]
            travel_t += travel_time_minutes(
                s_prev["lat"], s_prev["lng"],
                s_curr["lat"], s_curr["lng"], avg_speed_kmh)

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
                            avg_speed_kmh=30, all_stores_ref=None):
    """
    Assign rep territories using geographic k-means.

    Algorithm:
      1. Calculate optimal_reps = ceil(total_exec_travel / eff_cap)
      2. Run k-means on all priority store coordinates with k = optimal_reps
      3. One rep per cluster — no splitting, no merging loops
      4. Single underload check: if any cluster < 40% capacity AND another
         cluster can absorb it without exceeding 110% capacity, merge once
      5. Rep HQ = geographic centroid of assigned stores

    This ensures each rep owns a geographically contiguous territory.
    Reps never cross into each other's zones.
    """
    eff_cap     = (daily_minutes - 30) * working_days   # 9,900 min exec+travel budget
    monthly_cap = daily_minutes * working_days           # 10,560 min full day

    priority_geo = [s for s in priority_set if s.get("lat") and s.get("lng")]
    if not priority_geo:
        return [], 0

    all_ref = all_stores_ref if all_stores_ref is not None else priority_set

    # ── Step 1: Calculate optimal rep count ───────────────────────────────────
    total_monthly, _ = calc_zone_monthly_time(priority_geo, avg_speed_kmh, daily_minutes)
    optimal_reps     = max(1, math.ceil(total_monthly / eff_cap))

    # ── Step 2: Geographic k-means ────────────────────────────────────────────
    pts = [(s["lat"], s["lng"]) for s in priority_geo]
    if len(priority_geo) <= optimal_reps:



        # Fewer stores than reps — one store per rep
        labels = list(range(len(priority_geo)))
        optimal_reps = len(priority_geo)
    else:
        labels = kmeans_simple(pts, optimal_reps)

    # Assign rep_ids (1-based)
    for s, lbl in zip(priority_geo, labels):
        s["rep_id"] = int(lbl) + 1

    # ── Step 3: Build zone_centres ────────────────────────────────────────────
    zone_centres = []
    for rid in range(1, optimal_reps + 1):
        rz     = [s for s in priority_geo if s.get("rep_id") == rid]
        if not rz:
            continue
        rz_monthly, rz_daily = calc_zone_monthly_time(rz, avg_speed_kmh, daily_minutes)
        rz_exec = sum(s.get("visits_per_month",1)*s.get("visit_duration_min",25) for s in rz)
        zone_centres.append({
            "zone":            rid,
            "centre_lat":      round(sum(s["lat"] for s in rz)/len(rz), 4),
            "centre_lng":      round(sum(s["lng"] for s in rz)/len(rz), 4),
            "store_count":     len(rz),
            "time_needed_min": rz_monthly,
            "exec_min":        round(rz_exec),
            "capacity_min":    eff_cap,
            "utilisation_pct": round(rz_monthly / eff_cap * 100),
            "daily_breakdown": rz_daily,
        })

    # ── Step 4: Single underload check ────────────────────────────────────────
    # If a zone has < 40% capacity AND a neighbour can absorb it under 110%,
    # merge once. This handles the "5 stores, 1350 min" edge case.
    # Only one pass — no loop that could keep reducing rep count.
    MIN_LOAD     = eff_cap * 0.40   # 3,960 min — genuinely too small
    MAX_ABSORB   = eff_cap * 1.10   # 10,890 min — receiving zone ceiling

    zone_centres.sort(key=lambda z: z["time_needed_min"])
    if len(zone_centres) > 1 and zone_centres[0]["time_needed_min"] < MIN_LOAD:
        weak    = zone_centres[0]
        others  = zone_centres[1:]
        nearest = min(others, key=lambda z: haversine_m(
            weak["centre_lat"], weak["centre_lng"],
            z["centre_lat"],    z["centre_lng"]))

        if nearest["time_needed_min"] + weak["time_needed_min"] <= MAX_ABSORB:
            # Merge weak into nearest



            for s in all_ref:
                if s.get("rep_id") == weak["zone"]:
                    s["rep_id"] = nearest["zone"]
            # Recalculate receiving zone
            nz = [s for s in priority_geo if s.get("rep_id") == nearest["zone"]]
            nz_monthly, nz_daily = calc_zone_monthly_time(nz, avg_speed_kmh, daily_minutes)
            nz_exec = sum(s.get("visits_per_month",1)*s.get("visit_duration_min",25) for s in nz)
            nearest.update({
                "store_count":     len(nz),
                "time_needed_min": nz_monthly,
                "exec_min":        round(nz_exec),
                "utilisation_pct": round(nz_monthly / eff_cap * 100),
                "daily_breakdown": nz_daily,
                "centre_lat":      round(sum(s["lat"] for s in nz)/max(len(nz),1), 4),
                "centre_lng":      round(sum(s["lng"] for s in nz)/max(len(nz),1), 4),
            })
            zone_centres = others  # weak zone removed

    actual_reps = len(zone_centres)
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

def rebalance_zones_65pct(all_stores, zone_centres, daily_minutes=480,
                          working_days=22, avg_speed_kmh=30, min_util_pct=65,
                          max_passes=5):
    """
    Rebalance store assignments so no rep is below min_util_pct utilisation.

    Rules:
      - Only move stores from a NEIGHBOURING zone (sorted by centroid distance)
      - Donor must stay >= min_util_pct after giving up the store
      - The moved store must be geographically close to the receiving zone
        (within 2× the receiving zone's intra-cluster radius)
      - One store moved per inner loop, recalculate, repeat
      - max_passes full sweeps to prevent infinite loops

    Returns the number of stores moved.
    """
    if not zone_centres or len(zone_centres) < 2:
        return 0

    monthly_cap = (daily_minutes - 30) * working_days   # effective capacity
    min_thresh  = monthly_cap * min_util_pct / 100

    def _zone_stores(zid):
        return [s for s in all_stores
                if s.get("rep_id") == zid
                and s.get("size_tier") in ("Large", "Medium", "Small")
                and s.get("lat") and s.get("lng")]

    def _zone_time(stores):
        return sum(
            s.get("visits_per_month", 1) * s.get("visit_duration_min", 25)
            for s in stores
        )

    def _zone_centroid(stores):
        if not stores:
            return 0, 0
        return (sum(s["lat"] for s in stores) / len(stores),
                sum(s["lng"] for s in stores) / len(stores))

    def _zone_radius(stores, c_lat, c_lng):
        """Max distance from centroid to any store in the zone."""
        if not stores:
            return 5000  # default 5km
        return max(haversine_m(c_lat, c_lng, s["lat"], s["lng"]) for s in stores)

    total_moved = 0

    for _pass in range(max_passes):
        moved_this_pass = 0

        # Recalculate utilisation for all zones
        zone_util = {}
        for zc in zone_centres:
            zid = zc["zone"]
            zs  = _zone_stores(zid)
            zt  = _zone_time(zs)
            zone_util[zid] = {
                "time": zt,
                "util_pct": round(zt / monthly_cap * 100) if monthly_cap > 0 else 0,
                "stores": zs,
                "centroid": _zone_centroid(zs),
            }

        # Sort zones by utilisation ascending — fix most underloaded first
        sorted_zones = sorted(zone_util.items(), key=lambda x: x[1]["util_pct"])

        for zid, zinfo in sorted_zones:
            if zinfo["util_pct"] >= min_util_pct:
                continue  # this zone is fine

            recv_lat, recv_lng = zinfo["centroid"]
            recv_radius = _zone_radius(zinfo["stores"], recv_lat, recv_lng)
            max_dist    = max(recv_radius * 2, 10000)  # at least 10km, at most 2× zone radius

            # Find neighbouring donors sorted by centroid distance
            donors = []
            for d_zid, d_info in zone_util.items():
                if d_zid == zid:
                    continue
                if d_info["util_pct"] <= min_util_pct:
                    continue  # donor must be above threshold
                d_lat, d_lng = d_info["centroid"]
                dist = haversine_m(recv_lat, recv_lng, d_lat, d_lng)
                donors.append((d_zid, dist, d_info))
            donors.sort(key=lambda x: x[1])  # nearest first

            for d_zid, _d_dist, d_info in donors:
                if zinfo["time"] >= min_thresh:
                    break  # receiver is now at threshold

                # Find candidate stores in donor that are closest to receiver centroid
                candidates = []
                for s in d_info["stores"]:
                    s_dist = haversine_m(recv_lat, recv_lng, s["lat"], s["lng"])
                    if s_dist <= max_dist:
                        candidates.append((s, s_dist))
                candidates.sort(key=lambda x: x[1])  # nearest to receiver first

                for s, s_dist in candidates:
                    if zinfo["time"] >= min_thresh:
                        break  # done

                    s_time = s.get("visits_per_month", 1) * s.get("visit_duration_min", 25)

                    # Check donor stays >= min_util_pct after giving up this store
                    donor_after = d_info["time"] - s_time
                    if donor_after < min_thresh:
                        continue  # would drain donor below threshold

                    # Move the store
                    s["rep_id"] = zid
                    zinfo["time"]    += s_time
                    zinfo["util_pct"] = round(zinfo["time"] / monthly_cap * 100)
                    d_info["time"]   -= s_time
                    d_info["util_pct"] = round(d_info["time"] / monthly_cap * 100)
                    # Remove from donor's store list, add to receiver's
                    d_info["stores"] = [x for x in d_info["stores"] if x is not s]
                    zinfo["stores"].append(s)
                    # Recalculate receiver centroid
                    zinfo["centroid"] = _zone_centroid(zinfo["stores"])
                    recv_lat, recv_lng = zinfo["centroid"]
                    moved_this_pass += 1
                    total_moved     += 1

        if moved_this_pass == 0:
            break  # nothing left to rebalance

    # Update zone_centres with new values
    for zc in zone_centres:
        zid = zc["zone"]
        zs  = _zone_stores(zid)
        if zs:
            zc["store_count"]     = len(zs)
            zc["time_needed_min"] = round(_zone_time(zs))
            zc["capacity_min"]    = monthly_cap
            zc["utilisation_pct"] = round(_zone_time(zs) / monthly_cap * 100) if monthly_cap > 0 else 0
            zc["centre_lat"]      = round(sum(s["lat"] for s in zs) / len(zs), 4)
            zc["centre_lng"]      = round(sum(s["lng"] for s in zs) / len(zs), 4)
            zc["visits_per_month"] = sum(s.get("visits_per_month", 1) for s in zs)

    return total_moved


def build_daily_routes(rep_stores, year=None, month=None, daily_minutes=480, avg_speed_kmh=30, city_lat=0, city_lng=0):
    """
    Assign stores to days (Mon-Fri) and sequence them within each day.

    Prompt rules applied in order:
      Step 1  — Geographic k-means clustering into day groups
                k = max(1, min(5, ceil(n_stores / 8)))
      Step 2  — Nearest-neighbour sequencing within each day
                starting from the geographic centroid of that day's cluster
      Step 3  — Calculate day_length = exec + inter-store travel + 30 min break
                First/last leg (home<->store) excluded
      Step 4  — Enforce 420–550 min window:
                  > 550: remove highest-travel store → least-loaded absorbing day
                  < 420: pull nearest store from most-loaded day (stays ≥ 420)
      Step 5  — Iterative 2-opt cross-day swap (max 20 iterations)
                Keep swap if total inter-store travel decreases and rules hold
      Step 6  — Validate and tag violations (flagged but not blocking)

    Constants (from prompt):
      MAX_DAY   = 550 min



      MIN_DAY   = 420 min
      BREAK     = 30 min
      MAX_TRAVEL_PCT = 25% of (MAX_DAY - BREAK) = 25% of 520 = 130 min
      MIN_OUTLETS    = 8 per active day
    """
    if not rep_stores:
        return []

    MAX_DAY        = 550
    MIN_DAY        = 420
    BREAK          = 30
    MAX_TRAVEL_MIN = (MAX_DAY - BREAK) * 0.25   # 130 min
    MIN_OUTLETS    = 8

    # ── Helpers ──────────────────────────────────────────────────────────────
    def tt(s_a, s_b):
        """Travel time in minutes between two stores."""
        if not (s_a.get("lat") and s_a.get("lng") and s_b.get("lat") and s_b.get("lng")):
            return 0.0
        return travel_time_minutes(s_a["lat"], s_a["lng"], s_b["lat"], s_b["lng"], avg_speed_kmh)

    def day_metrics(stores):
        """Returns (exec_min, travel_min, day_length) for an ordered store list."""
        if not stores:
            return 0.0, 0.0, BREAK
        exec_t   = sum(s.get("visit_duration_min", 25) for s in stores)
        travel_t = sum(tt(stores[i-1], stores[i]) for i in range(1, len(stores)))
        return exec_t, travel_t, exec_t + travel_t + BREAK

    def nn_sequence(stores):
        """Nearest-neighbour sort starting from the centroid of the store list.
        Uses index-based tracking instead of list.remove() for O(N log N) vs O(N^2)."""
        if len(stores) <= 1:
            return stores[:]
        c_lat = sum(s["lat"] for s in stores if s.get("lat")) / max(1, sum(1 for s in stores if s.get("lat")))
        c_lng = sum(s["lng"] for s in stores if s.get("lng")) / max(1, sum(1 for s in stores if s.get("lng")))
        ordered   = []
        used      = [False] * len(stores)
        cur_lat, cur_lng = c_lat, c_lng
        for _ in range(len(stores)):
            best_idx, best_dist = -1, float("inf")
            for j in range(len(stores)):
                if used[j]:
                    continue
                d = haversine_m(cur_lat, cur_lng,
                                stores[j].get("lat", cur_lat),
                                stores[j].get("lng", cur_lng))
                if d < best_dist:
                    best_dist = d
                    best_idx  = j
            if best_idx < 0:
                break
            used[best_idx] = True
            ordered.append(stores[best_idx])
            cur_lat = stores[best_idx].get("lat", cur_lat)
            cur_lng = stores[best_idx].get("lng", cur_lng)
        return ordered



    def total_travel(day_groups):
        """Sum of all inter-store travel across all days."""
        return sum(
            sum(tt(stores[i-1], stores[i]) for i in range(1, len(stores)))
            for stores in day_groups.values()
        )

    # ── Filter to geo stores only ─────────────────────────────────────────────
    geo_stores  = [s for s in rep_stores if s.get("lat") and s.get("lng")]
    no_geo      = [s for s in rep_stores if not (s.get("lat") and s.get("lng"))]
    n           = len(geo_stores)

    if not geo_stores:
        for i, s in enumerate(rep_stores):
            s["assigned_day"]    = WEEKDAYS[i % 5]
            s["day_visit_order"] = i + 1
        return rep_stores

    # ── Step 1: Geographic clustering ────────────────────────────────────────
    # k = enough days so each has ~8 stores; capped at 5
    k = max(1, min(5, math.ceil(n / MIN_OUTLETS)))

    if n <= k:
        # Fewer stores than days — one store per day, nearest-neighbour order
        ordered_all = nn_sequence(geo_stores)
        labels      = list(range(n))
    else:
        pts    = [(s["lat"], s["lng"]) for s in geo_stores]
        labels = kmeans_simple(pts, k)

    # Build initial day groups (only use first k weekdays)
    active_days  = WEEKDAYS[:k]
    day_groups   = {d: [] for d in WEEKDAYS}
    for s, lbl in zip(geo_stores, labels):
        day = active_days[int(lbl) % k]
        day_groups[day].append(s)

    # ── Step 2: Nearest-neighbour sequence within each day ───────────────────
    for day in active_days:
        day_groups[day] = nn_sequence(day_groups[day])

    # ── Step 3+4: Enforce 420–550 min window ─────────────────────────────────
    # Iterate until stable (max 30 passes)
    for _pass in range(30):
        changed = False



        # --- Over 550: remove highest-travel store ---
        for day in active_days:
            stores = day_groups[day]
            if not stores:
                continue
            _, _, day_len = day_metrics(stores)
            if day_len <= MAX_DAY:
                continue

            # Find the store (index ≥ 1) that saves the most travel when removed
            best_save, best_idx = -1, -1
            for idx in range(len(stores)):
                candidate = stores[:idx] + stores[idx+1:]
                _, t_without, _ = day_metrics(candidate)
                _, t_with,    _ = day_metrics(stores)
                save = t_with - t_without
                if save > best_save:
                    best_save = save
                    best_idx  = idx

            if best_idx < 0:
                continue

            moved  = stores.pop(best_idx)
            # Re-sequence after removal
            day_groups[day] = nn_sequence(stores)

            # Place on least-loaded day that can absorb it under 550
            candidate_days = sorted(
                [d for d in active_days if d != day],
                key=lambda d: day_metrics(day_groups[d])[2]
            )
            placed = False
            for target_day in candidate_days:
                test = day_groups[target_day] + [moved]
                test = nn_sequence(test)
                _, _, tl = day_metrics(test)
                if tl <= MAX_DAY:
                    day_groups[target_day] = test
                    placed   = True
                    changed  = True
                    break

            if not placed:
                # Can't place — put back and stop trying for this day
                day_groups[day] = nn_sequence(stores + [moved])



        # --- Under 420: pull nearest store from most-loaded day ---
        for day in active_days:
            stores = day_groups[day]
            if not stores:
                continue
            _, _, day_len = day_metrics(stores)
            if day_len >= MIN_DAY:
                continue

            # Find the most-loaded day that can give up a store and stay ≥ 420
            donor_days = sorted(
                [d for d in active_days if d != day and len(day_groups[d]) > 0],
                key=lambda d: day_metrics(day_groups[d])[2],
                reverse=True
            )
            pulled = False
            for donor in donor_days:
                donor_stores = day_groups[donor]
                # Try removing each store from donor — keep donor ≥ 420 after
                best_store = None
                best_dist  = float("inf")
                for idx, candidate in enumerate(donor_stores):
                    remaining = donor_stores[:idx] + donor_stores[idx+1:]
                    _, _, dl_after = day_metrics(remaining) if remaining else (0,0,BREAK)
                    if remaining and dl_after < MIN_DAY:
                        continue
                    # Pick the candidate nearest to the receiving day's centroid
                    if stores:
                        c_lat = sum(s.get("lat",0) for s in stores) / len(stores)
                        c_lng = sum(s.get("lng",0) for s in stores) / len(stores)
                        dist  = haversine_m(c_lat, c_lng,
                                            candidate.get("lat", c_lat),
                                            candidate.get("lng", c_lng))
                    else:
                        dist = 0
                    if dist < best_dist:
                        best_dist  = dist
                        best_store = (idx, candidate)

                if best_store:
                    idx, store = best_store
                    day_groups[donor].pop(idx)
                    day_groups[donor] = nn_sequence(day_groups[donor])
                    day_groups[day]   = nn_sequence(stores + [store])
                    stores   = day_groups[day]
                    changed  = True
                    pulled   = True



                    break

        if not changed:
            break

    # ── Step 5: Iterative 2-opt cross-day swap ────────────────────────────────
    # Adaptive limits: reduce iterations for large store counts to avoid O(N^2) blowup
    _max_per_day = max((len(day_groups[d]) for d in active_days), default=0)
    if _max_per_day > 60:
        _opt_iters = 3     # very large — minimal optimization
        _swap_cap  = 15    # only try border stores (first/last N per day)
    elif _max_per_day > 30:
        _opt_iters = 8
        _swap_cap  = 25
    else:
        _opt_iters = 20    # original behavior for small counts
        _swap_cap  = 0     # 0 = no cap, try all

    for _iter in range(_opt_iters):
        improved = False
        current_travel = total_travel(day_groups)

        for i, day_a in enumerate(active_days):
            for day_b in active_days[i+1:]:
                stores_a = day_groups[day_a]
                stores_b = day_groups[day_b]
                if not stores_a or not stores_b:
                    continue

                # For large days, only try swapping border stores (first/last N)
                # These are nearest-neighbour ordered, so borders are cluster edges
                if _swap_cap and len(stores_a) > _swap_cap:
                    _half = _swap_cap // 2
                    a_indices = list(range(_half)) + list(range(max(0, len(stores_a) - _half), len(stores_a)))
                else:
                    a_indices = list(range(len(stores_a)))
                if _swap_cap and len(stores_b) > _swap_cap:
                    _half = _swap_cap // 2
                    b_indices = list(range(_half)) + list(range(max(0, len(stores_b) - _half), len(stores_b)))
                else:
                    b_indices = list(range(len(stores_b)))

                for ia in a_indices:
                    if ia >= len(stores_a):
                        continue
                    sa = stores_a[ia]
                    for ib in b_indices:
                        if ib >= len(stores_b):
                            continue
                        sb = stores_b[ib]
                        # Build candidate days after swap
                        new_a = nn_sequence(stores_a[:ia] + [sb] + stores_a[ia+1:])
                        new_b = nn_sequence(stores_b[:ib] + [sa] + stores_b[ib+1:])

                        # Check constraints for both days
                        _, _, la = day_metrics(new_a)
                        _, _, lb = day_metrics(new_b)
                        ta_ok = MIN_DAY <= la <= MAX_DAY if new_a else True
                        tb_ok = MIN_DAY <= lb <= MAX_DAY if new_b else True

                        if not (ta_ok and tb_ok):
                            continue

                        # Check travel cap
                        _, tra, _ = day_metrics(new_a)
                        _, trb, _ = day_metrics(new_b)
                        if tra > MAX_TRAVEL_MIN or trb > MAX_TRAVEL_MIN:
                            continue

                        # Accept if total travel decreases
                        trial = dict(day_groups)
                        trial[day_a] = new_a
                        trial[day_b] = new_b
                        new_travel = total_travel(trial)

                        if new_travel < current_travel - 0.5:  # 0.5 min threshold
                            day_groups[day_a] = new_a
                            day_groups[day_b] = new_b
                            current_travel    = new_travel
                            improved          = True
                            break
                    if improved:
                        break
                if improved:
                    break

        if not improved:
            break

    # ── Step 6: Assign day/order and validate ────────────────────────────────
    violations = []
    for day in WEEKDAYS:
        stores = day_groups[day]
        if not stores:
            continue
        exec_t, travel_t, day_len = day_metrics(stores)
        for i, s in enumerate(stores):
            s["assigned_day"]    = day
            s["day_visit_order"] = i + 1

        # Validate
        if day_len > MAX_DAY:
            violations.append(f"{day}: day_length {round(day_len)}min > {MAX_DAY}min")
        if day_len < MIN_DAY:
            violations.append(f"{day}: day_length {round(day_len)}min < {MIN_DAY}min")
        if travel_t > MAX_TRAVEL_MIN:
            violations.append(f"{day}: travel {round(travel_t)}min > {round(MAX_TRAVEL_MIN)}min (25% cap)")
        if len(stores) < MIN_OUTLETS:
            violations.append(f"{day}: only {len(stores)} outlets < {MIN_OUTLETS} minimum")

    # Assign no-geo stores to Friday as fallback
    for i, s in enumerate(no_geo):
        s["assigned_day"]    = "Friday"
        s["day_visit_order"] = 99 + i

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

# ── STEP 2: MARKET UNIVERSE SCRAPE ───────────────────────────────────────────
st.markdown('<div class="section-title">2. Market universe scrape</div>', unsafe_allow_html=True)

# Show exactly what will be scraped so the user is clear
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
    "This scrapes exactly the geography and categories you configured on the Configure page. "
    "Scrape once, reuse forever — no API credits wasted on re-scraping the same area. "
    "Change the geography or categories in Configure to trigger a fresh scrape."
)

def _scrape_cache_key(cfg):
    """Unique key for this market's bbox + categories combination."""
    cats = ",".join(sorted(cfg.get("categories", [])))
    return f"{cfg['lat_min']:.4f},{cfg['lat_max']:.4f},{cfg['lng_min']:.4f},{cfg['lng_max']:.4f}|{cats}"

_cache_key     = _scrape_cache_key(cfg)
_saved_cache   = st.session_state.get("universe_cache", {})
_cached        = _saved_cache.get(_cache_key)

if _cached:
    _n      = len(_cached["universe"])
    _when   = _cached.get("scraped_at", "unknown time")
    _market = _cached.get("market_name", cfg.get("market_name",""))
    st.success(
        f"  Cached universe ready: **{_n:,} stores** scraped for "
        f"**{_scope_label}** · categories: {', '.join(_scope_cats)} · "
        f"scraped {_when} — pipeline will use this, no re-scraping needed."



    )
    col_r1, col_r2 = st.columns([2,1])
    with col_r1:
        import pandas as _pd_cache
        _prev_df = _pd_cache.DataFrame(_cached["universe"])[
            ["store_name","city","category","rating","review_count","lat","lng"]
        ].head(5)
        st.dataframe(_prev_df, use_container_width=True, hide_index=True)
        # Show enrichment status
        _n_with_rating = sum(1 for s in _cached["universe"] if s.get("rating",0) > 0)
        _n_with_phone  = sum(1 for s in _cached["universe"] if s.get("phone",""))
        st.caption(
            f"Quality: {_n_with_rating:,}/{_n:,} stores have ratings · "
            f"{_n_with_phone:,}/{_n:,} have phone numbers"
        )
    with col_r2:
        if st.button("  Re-scrape (clear cache)", key="btn_rescrape"):
            del st.session_state["universe_cache"][_cache_key]
            st.rerun()
        import pandas as _pd_dl
        _dl_df = _pd_dl.DataFrame(_cached["universe"])
        st.download_button(
            "  Download universe CSV",
            _dl_df.to_csv(index=False),
            f"{cfg.get('market_name','market')}_universe.csv",
            "text/csv", key="dl_universe_cache"
        )
        st.caption("  Download to preserve cache across sessions")

    # ── Import CSV to replace existing cache ─────────────────────────────────
    with st.expander("  Replace cache by importing a CSV"):
        st.caption("Upload a previously downloaded universe CSV to replace the current cache.")
        _imp_file2 = st.file_uploader(
            "Upload universe CSV", type=["csv"], key="import_universe_csv_replace"
        )
        if _imp_file2:
            try:
                import pandas as _pd_imp2
                _imp_df2 = _pd_imp2.read_csv(_imp_file2)
                _imp_df2.columns = [c.strip().lower().replace(" ","_") for c in _imp_df2.columns]
                if "store_name" not in _imp_df2.columns or "lat" not in _imp_df2.columns:
                    st.error("File must have at least store_name and lat columns.")
                else:
                    for _col, _default in [
                        ("lng",0.0),("rating",0.0),("review_count",0),("price_level",0),
                        ("category","supermarket"),("source","scraped"),("covered",False),
                        ("phone",""),("opening_hours",""),("website",""),



                        ("annual_sales_usd",0.0),("lines_per_store",0),("poi_count",0),
                        ("place_id",""),("store_id",""),("address",""),("city",""),
                        ("business_status","Active"),
                    ]:
                        if _col not in _imp_df2.columns:
                            _imp_df2[_col] = _default
                    import datetime as _dt_imp2
                    if "universe_cache" not in st.session_state:
                        st.session_state["universe_cache"] = {}
                    st.session_state["universe_cache"][_cache_key] = {
                        "universe":    _imp_df2.to_dict("records"),
                        "market_name": cfg.get("market_name",""),
                        "scraped_at":  f"Imported {_dt_imp2.datetime.now().strftime('%d %b %Y %H:%M')}",
                        "categories":  cfg.get("categories",[]),
                        "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
                    }
                    st.success(f"  Cache replaced with {len(_imp_df2):,} stores.")
                    st.rerun()
            except Exception as _ie2:
                st.error(f"Import failed: {_ie2}")
else:
    # ── Import previously downloaded universe CSV ────────────────────────────
    st.markdown("**Option A — Import a previously downloaded universe CSV:**")
    st.caption("If you downloaded the universe CSV before a refresh, upload it here to restore the cache instantly — no re-scraping needed.")
    _imp_file = st.file_uploader(
        "Upload universe CSV", type=["csv"], key="import_universe_csv"
    )
    if _imp_file:
        try:
            import pandas as _pd_imp
            _imp_df = _pd_imp.read_csv(_imp_file)
            _imp_df.columns = [c.strip().lower().replace(" ","_") for c in _imp_df.columns]
            if "store_name" not in _imp_df.columns or "lat" not in _imp_df.columns:
                st.error("File must have at least store_name and lat columns.")
            else:
                # Fill missing columns with defaults
                for _col, _default in [
                    ("lng",0.0),("rating",0.0),("review_count",0),("price_level",0),
                    ("category","supermarket"),("source","scraped"),("covered",False),
                    ("phone",""),("opening_hours",""),("website",""),
                    ("annual_sales_usd",0.0),("lines_per_store",0),("poi_count",0),
                    ("place_id",""),("store_id",""),("address",""),("city",""),
                    ("business_status","Active"),
                ]:
                    if _col not in _imp_df.columns:
                        _imp_df[_col] = _default
                _imp_records = _imp_df.to_dict("records")



                import datetime as _dt_imp
                if "universe_cache" not in st.session_state:
                    st.session_state["universe_cache"] = {}
                st.session_state["universe_cache"][_cache_key] = {
                    "universe":    _imp_records,
                    "market_name": cfg.get("market_name",""),
                    "scraped_at":  f"Imported {_dt_imp.datetime.now().strftime('%d %b %Y %H:%M')}",
                    "categories":  cfg.get("categories",[]),
                    "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
                }
                st.success(f"  Imported {len(_imp_records):,} stores from CSV — cache restored.")
                st.rerun()
        except Exception as _ie:
            st.error(f"Import failed: {_ie}")

    st.markdown("**Option B — Build fresh universe from Google Places + OSM:**")
    st.info(
        f"No cached data for **{_scope_label}** ({', '.join(_scope_cats)}). "
        "Configure enrichment options below, then click **Build & enrich universe**. "
        "This runs once — every future pipeline run reuses this data automatically."
    )

    # ── Enrichment options — set before scraping ─────────────────────────────
    st.markdown("**Enrichment options** *(applied once at scrape time, stored in cache)*")
    _admin_enrich_s2 = st.session_state.get("admin_enrichment", {
        "run_place_details": True, "run_poi": True, "poi_radius_m": 500})
    _ec1, _ec2, _ec3 = st.columns(3)
    with _ec1:
        st.markdown("  **Price level** — always on (affluence scoring)")
        st.markdown("  **Nearby POI count** — always on (POI scoring)")
    with _ec2:
        _run_phone_s2 = st.toggle(
            "  Phone & opening hours",
            value=_admin_enrich_s2.get("run_place_details", True),
            key="enrich_phone_s2",
            help="~$0.017/store. Turn off for test runs to save credits."
        )
    with _ec3:
        _poi_radius_s2 = st.number_input(
            "POI radius (m)", min_value=100, max_value=2000,
            value=_admin_enrich_s2.get("poi_radius_m", 500), step=100,
            key="poi_radius_s2"
        )
    # Save to session so pipeline picks it up
    st.session_state["admin_enrichment"] = {
        "run_place_details": _run_phone_s2,
        "run_poi": True,



        "poi_radius_m": _poi_radius_s2,
    }

    # Cost estimate
    _r_est, _t_est = smart_tile_radius(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"])
    _centres_est   = grid_centres(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"], _r_est)
    _est_scrape    = len(_centres_est) * len(cfg.get("categories",[])) * 3
    _est_enrich    = min(len(_centres_est) * 15, 2000) if _run_phone_s2 else 0
    _est_cost      = round(_est_scrape * 0.032 + _est_enrich * 0.017, 2)
    _est_time      = fmt_time(_est_scrape * 0.25 + _est_enrich * 0.1)
    st.caption(f"Estimated: ~{_est_scrape:,} scrape calls + {_est_enrich:,} enrichment calls · ~${_est_cost} · ~{_est_time}")

    _scrape_api_key = (cfg.get("market_api_key")
        or st.session_state.get("market_api_key_input")
        or st.session_state.get("session_api_key"))
    if not _scrape_api_key:
        try: _scrape_api_key = st.secrets.get("GOOGLE_MAPS_API_KEY","") or None
        except: _scrape_api_key = None

    # ── Resume from checkpoint if available ────────────────────────────
    _ckpt = st.session_state.get("_scrape_checkpoint")
    if _ckpt and _ckpt.get("universe"):
        st.warning(
            f"  Checkpoint available from a previous interrupted run "
            f"({_ckpt.get('step','unknown')} · {_ckpt.get('saved_at','?')} · "
            f"{len(_ckpt['universe']):,} stores). "
        )
        _rc1, _rc2 = st.columns(2)
        with _rc1:
            if st.button("  Restore checkpoint to cache", key="btn_restore_ckpt"):
                import datetime as _dt_rc
                if "universe_cache" not in st.session_state:
                    st.session_state["universe_cache"] = {}
                st.session_state["universe_cache"][_cache_key] = {
                    "universe":    _ckpt["universe"],
                    "market_name": cfg.get("market_name",""),
                    "scraped_at":  f"Restored {_dt_rc.datetime.now().strftime('%d %b %Y %H:%M')}",
                    "categories":  cfg.get("categories",[]),
                    "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
                }
                del st.session_state["_scrape_checkpoint"]
                st.success(f"  Restored {len(_ckpt['universe']):,} stores from checkpoint.")
                st.rerun()
        with _rc2:
            if st.button("  Discard checkpoint", key="btn_discard_ckpt"):
                del st.session_state["_scrape_checkpoint"]
                st.rerun()

    if st.button("  Build & enrich universe", type="primary", key="btn_scrape_universe"):
        if not _scrape_api_key:
            st.error("No API key — set GOOGLE_MAPS_API_KEY in Secrets or Admin Settings.")
        else:
            st.session_state["_cancel_scrape"] = False
            _scrape_status = st.empty()
            _scrape_bar    = st.progress(0)
            if st.button("  Stop build (saves progress)", key="btn_cancel_scrape"):
                st.session_state["_cancel_scrape"] = True
            _scrape_t0     = time.time()

            # ── Step A: Portfolio stores (Option 3) ───────────────────────────
            _portfolio_stores = []
            _pf_df = st.session_state.get("portfolio_df")
            if _pf_df is not None:
                for _, _row in _pf_df.iterrows():
                    _s = _row.to_dict()
                    _s["covered"]  = True
                    _s["source"]   = "portfolio"
                    for _k in ["annual_sales_usd","lines_per_store","rating","review_count",
                               "price_level","phone","opening_hours","website","poi_count"]:
                        _s.setdefault(_k, 0 if _k not in ["phone","opening_hours","website"] else "")
                    _portfolio_stores.append(_s)
            _scrape_status.info(f"Step A: {len(_portfolio_stores)} portfolio stores loaded.")
            _scrape_bar.progress(5)

            # ── Step B: Google Places scraping (primary source) ───────────────
            # Google Places is the primary gap discovery source for markets like Oman
            # where OSM coverage is sparse. We use the "types" array Google returns
            # per place to filter accurately — not name keywords.
            # GROCERY_TYPES: must have at least one of these in the types array.



            _GROCERY_TYPES = {
                "supermarket", "grocery_or_supermarket",
                "convenience_store", "department_store",
                "food", "store",
            }
            def _is_grocery_by_types(place_types):
                """True only if Google tags this place with a grocery/retail type."""
                ts = set(place_types)
                # Must have supermarket, grocery, convenience, or department_store
                strong = {"supermarket","grocery_or_supermarket","convenience_store","department_store"}
                return bool(ts & strong)

            _radius_m, _ = smart_tile_radius(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"])
            _centres     = grid_centres(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"],_radius_m)
            _seen_ids    = set()
            _osm_shops   = []  # reuse variable name for compatibility
            _total_tiles = max(len(_centres)*len(cfg["categories"]),1)
            _done_tiles  = 0
            _type_filtered = 0

            _scrape_cancelled = False
            for _cat in cfg["categories"]:
                if _scrape_cancelled:
                    break
                for _tlat,_tlng in _centres:
                    if st.session_state.get("_cancel_scrape"):
                        _scrape_status.warning(f"Step B: Cancelled at {_done_tiles}/{_total_tiles} tiles. Saving {len(_osm_shops):,} stores...")
                        _scrape_cancelled = True
                        break
                    _token = None
                    while True:
                        _data = fetch_places(_tlat,_tlng,_radius_m,_cat,_scrape_api_key,_token)
                        for _place in _data.get("results",[]):
                            _pid = _place.get("place_id","")
                            if _pid in _seen_ids: continue
                            if _place.get("business_status") == "CLOSED_PERMANENTLY": continue
                            # Filter by Google's own types array — most reliable signal
                            _ptypes = _place.get("types", [])
                            if not _is_grocery_by_types(_ptypes):
                                _type_filtered += 1
                                continue
                            _seen_ids.add(_pid)
                            _loc    = _place.get("geometry",{}).get("location",{})
                            _vic    = _place.get("vicinity","")
                            _vparts = [_p.strip() for _p in _vic.split(",") if _p.strip()]
                            _scity  = _vparts[-1] if len(_vparts)>=2 else cfg.get("city","")
                            _saddr  = ", ".join(_vparts[:-1]) if len(_vparts)>=2 else (_vparts[0] if _vparts else "")
                            _cname  = clean_store_name(_place.get("name",""))
                            if not _cname: continue
                            _osm_shops.append({
                                "store_id":_pid,"place_id":_pid,"store_name":_cname,
                                "address":_saddr,"city":_scity,"region":cfg.get("city",""),
                                "lat":_loc.get("lat"),"lng":_loc.get("lng"),
                                "rating":float(_place.get("rating",0) or 0),



                                "review_count":int(_place.get("user_ratings_total",0) or 0),
                                "price_level":int(_place.get("price_level",0) or 0),
                                "business_status":_map_biz_status(_place.get("business_status","")),
                                "category":_cat,"annual_sales_usd":0.0,"lines_per_store":0,
                                "covered":False,"source":"scraped",
                                "phone":"","opening_hours":"","website":"","poi_count":0,
                                "google_types": _ptypes,
                            })
                        _token = _data.get("next_page_token")
                        if not _token: break
                    _done_tiles += 1
                    _pct = 5 + int(_done_tiles/_total_tiles*20)
                    _elapsed = time.time() - _scrape_t0
                    _rem = (_elapsed/_done_tiles)*(_total_tiles-_done_tiles) if _done_tiles>0 else 0
                    _scrape_status.info(
                        f"Step B: {_done_tiles}/{_total_tiles} tiles · "
                        f"{len(_osm_shops):,} kept · {_type_filtered} filtered by type · "
                        f"  {fmt_time(_rem).replace('~','')} remaining"
                    )
                    _scrape_bar.progress(_pct)

            _scrape_status.info(
                f"Step B: {len(_osm_shops):,} stores from Google Places "
                f"(filtered {_type_filtered} non-grocery by types array). "
                f"Now topping up with OpenStreetMap..."
            )

            # ── Step B2: OSM top-up (secondary, deduplicated) ─────────────────
            # Add OSM stores not already found by Google (by proximity dedup)
            _osm_topup = []
            _OSM_TAGS  = "supermarket|convenience|wholesale|grocery|greengrocer|general|department_store|mall|variety_store"
            _b         = (cfg["lat_min"], cfg["lng_min"], cfg["lat_max"], cfg["lng_max"])
            _osm_q     = (
                "[out:json][timeout:90];("
                + 'node["shop"~"' + _OSM_TAGS + '"](' + str(_b[0]) + "," + str(_b[1]) + "," + str(_b[2]) + "," + str(_b[3]) + ");"
                + 'way["shop"~"' + _OSM_TAGS + '"](' + str(_b[0]) + "," + str(_b[1]) + "," + str(_b[2]) + "," + str(_b[3]) + ");"
                + ");out center tags;"
            )
            _osm_cat_map = {
                "supermarket":"supermarket","wholesale":"supermarket",
                "department_store":"supermarket","mall":"supermarket",
                "convenience":"convenience_store","general":"convenience_store",
                "grocery":"convenience_store","greengrocer":"convenience_store",
                "variety_store":"convenience_store",
            }
            _osm_mirrors = [
                "https://overpass-api.de/api/interpreter",



                "https://overpass.kumi.systems/api/interpreter",
            ]
            # Build spatial grid for fast deduplication (O(1) per lookup vs O(N))
            _google_grid = _build_spatial_grid(_osm_shops)

            for _mirror in _osm_mirrors:
                try:
                    _osm_r = requests.post(_mirror, data={"data":_osm_q}, timeout=30)
                    _osm_els = _osm_r.json().get("elements",[])
                    for _el in _osm_els:
                        _tags  = _el.get("tags",{})
                        _ename = clean_store_name(_tags.get("name") or _tags.get("name:en") or "")
                        if not _ename: continue
                        _elat  = _el["lat"] if _el["type"]=="node" else _el.get("center",{}).get("lat")
                        _elng  = _el["lon"] if _el["type"]=="node" else _el.get("center",{}).get("lon")
                        if not (_elat and _elng): continue
                        # Deduplicate against Google results using spatial grid (O(1) avg)
                        _duplicate = _is_duplicate_spatial(float(_elat), float(_elng), _google_grid)
                        if _duplicate: continue
                        _addr = _tags.get("addr:street","")
                        _city = _tags.get("addr:city") or _tags.get("addr:suburb") or cfg.get("city","")
                        _cat  = _osm_cat_map.get(_tags.get("shop",""), cfg["categories"][0] if cfg["categories"] else "supermarket")
                        _osm_topup.append({
                            "store_id": f"osm_{_el['type']}_{_el['id']}",
                            "place_id": "", "store_name": _ename,
                            "address": _addr, "city": _city, "region": cfg.get("city",""),
                            "lat": float(_elat), "lng": float(_elng),
                            "rating": 0.0, "review_count": 0, "price_level": 0,
                            "business_status": "Active", "category": _cat,
                            "annual_sales_usd": 0.0, "lines_per_store": 0,
                            "covered": False, "source": "scraped",
                            "phone": _tags.get("phone",""), "opening_hours": _tags.get("opening_hours",""),
                            "website": _tags.get("website",""), "poi_count": 0,
                        })
                    if _osm_topup or _osm_els:
                        _scrape_status.info(f"OSM top-up: {len(_osm_topup)} additional stores not in Google results.")
                    break
                except Exception:
                    pass

            _osm_shops.extend(_osm_topup)
            _scrape_bar.progress(30)
            _all_universe = _portfolio_stores + _osm_shops

            # ── Save scrape checkpoint (crash recovery) ──────────────────
            import datetime as _dt_ckpt
            if "universe_cache" not in st.session_state:
                st.session_state["universe_cache"] = {}
            st.session_state["_scrape_checkpoint"] = {
                "universe": list(_all_universe),
                "step": "scrape_done",
                "saved_at": _dt_ckpt.datetime.now().strftime("%d %b %Y %H:%M"),
            }

            # ── Step C: Google enrichment — ONLY stores missing data ─────────
            # Skip stores already enriched by Google Places scraping (have rating > 0
            # AND review_count > 0) — these already got their data in Step B.
            _need_enrich = [s for s in _all_universe
                           if not (s.get("rating", 0) > 0 and s.get("review_count", 0) > 0)]
            _already_ok  = len(_all_universe) - len(_need_enrich)
            _scrape_status.info(
                f"Step C: Enriching {len(_need_enrich):,} stores missing data "
                f"(skipping {_already_ok:,} already enriched by Google Places)..."
            )
            _mkt_lat = (cfg["lat_min"] + cfg["lat_max"]) / 2
            _mkt_lng = (cfg["lng_min"] + cfg["lng_max"]) / 2
            _enriched_g = 0
            # Cancel support
            if "_cancel_scrape" not in st.session_state:
                st.session_state["_cancel_scrape"] = False

            _enrich_start_c = time.time()
            for _ei, _s in enumerate(_need_enrich):
                # Check cancel flag
                if st.session_state.get("_cancel_scrape"):
                    _scrape_status.warning(f"Step C: Cancelled at {_ei}/{len(_need_enrich)}. Saving progress...")
                    break
                try:
                    _sname = str(_s.get("store_name","")).strip()
                    _scity = str(_s.get("city","")).strip()
                    _query = f"{_sname} {_scity}".strip() if _scity else _sname
                    if not _query: continue
                    _slat  = _s.get("lat") or _mkt_lat
                    _slng  = _s.get("lng") or _mkt_lng
                    _gr    = _api_retry(
                        requests.get,
                        "https://maps.googleapis.com/maps/api/place/textsearch/json",
                        params={"query":_query,"location":f"{_slat},{_slng}","radius":"2000","key":_scrape_api_key},
                        timeout=8
                    )
                    _gdata = _gr.json() if _gr else {}
                    if _gdata.get("status") == "OK" and _gdata.get("results"):
                        for _res in _gdata["results"]:
                            _rloc = _res.get("geometry",{}).get("location",{})
                            _rlat,_rlng = _rloc.get("lat",0),_rloc.get("lng",0)
                            if _s.get("lat") and haversine_m(_s["lat"],_s["lng"],_rlat,_rlng) > 1500:
                                continue
                            if _res.get("rating") and float(_res["rating"]) > 0:
                                _s["rating"] = float(_res["rating"])
                            if _res.get("user_ratings_total") and int(_res["user_ratings_total"]) > 0:
                                _s["review_count"] = int(_res["user_ratings_total"])
                            if _res.get("price_level") is not None:
                                _s["price_level"] = int(_res["price_level"])
                            _pid = _res.get("place_id","")
                            if _pid and not _s.get("place_id"):
                                _s["place_id"] = _pid
                            if not _s.get("lat") and _rlat:
                                _s["lat"] = _rlat; _s["lng"] = _rlng
                            _enriched_g += 1
                            break
                    time.sleep(0.05)
                except Exception:
                    pass

                # Batch checkpoint — save progress every 100 stores
                if (_ei + 1) % CHECKPOINT_BATCH_SIZE == 0:
                    st.session_state["_scrape_checkpoint"] = {
                        "universe": list(_all_universe),
                        "step": f"enrich_c_{_ei+1}",
                        "saved_at": time.strftime("%d %b %Y %H:%M"),
                    }

                if (_ei+1) % 20 == 0 or _ei == len(_need_enrich)-1:
                    _elapsed_c = time.time() - _enrich_start_c
                    _rem     = (_elapsed_c/(_ei+1))*(len(_need_enrich)-_ei-1) if _ei > 0 else 0
                    _pct     = 30 + int((_ei+1)/max(len(_need_enrich),1)*55)
                    _scrape_status.info(
                        f"Step C: {_ei+1}/{len(_need_enrich)} · {_enriched_g} enriched · "
                        f"skipped {_already_ok:,} · "
                        f"  {fmt_time(_rem).replace('~','')} remaining"
                    )
                    _scrape_bar.progress(min(_pct, 85))

            # ── Step D: Phone & hours (optional) ─────────────────────────────
            if _run_phone_s2:
                _need_det = [s for s in _all_universe if s.get("place_id") and not s.get("phone")]
                _scrape_status.info(f"Step D: Phone & hours for {len(_need_det):,} stores...")
                _det_start = time.time()
                for _di, _s in enumerate(_need_det):
                    if st.session_state.get("_cancel_scrape"):
                        _scrape_status.warning(f"Step D: Cancelled at {_di}/{len(_need_det)}. Saving progress...")
                        break
                    _det = fetch_place_details(_s["place_id"], _scrape_api_key)
                    if _det:
                        _s["phone"]   = _det.get("formatted_phone_number","")
                        _s["website"] = _det.get("website","")
                        _wt = _det.get("opening_hours",{}).get("weekday_text",[])
                        _s["opening_hours"] = " | ".join(_wt) if _wt else ""
                        if _det.get("price_level") is not None:
                            _s["price_level"] = int(_det["price_level"])
                        if _det.get("rating") and float(_det["rating"]) > _s.get("rating",0):
                            _s["rating"] = float(_det["rating"])
                        if _det.get("user_ratings_total") and int(_det["user_ratings_total"]) > _s.get("review_count",0):
                            _s["review_count"] = int(_det["user_ratings_total"])
                    _scrape_bar.progress(85 + int((_di+1)/max(len(_need_det),1)*14))
                    # Batch checkpoint every 100 stores
                    if (_di + 1) % CHECKPOINT_BATCH_SIZE == 0:
                        st.session_state["_scrape_checkpoint"] = {
                            "universe": list(_all_universe),
                            "step": f"phone_{_di+1}",
                            "saved_at": time.strftime("%d %b %Y %H:%M"),
                        }
                    if (_di+1) % 50 == 0 or _di == len(_need_det)-1:
                        _det_elapsed = time.time() - _det_start
                        _det_rem = (_det_elapsed/(_di+1))*(len(_need_det)-_di-1) if _di > 0 else 0
                        _scrape_status.info(
                            f"Step D: {_di+1}/{len(_need_det)} · "
                            f"  {fmt_time(_det_rem).replace('~','')} remaining"
                        )
                    time.sleep(0.05)

            # ── Step E: POI enrichment (always done at cache time) ────────────
            _poi_radius_use = st.session_state.get("admin_enrichment",{}).get("poi_radius_m", 500)
            _poi_api_key    = _scrape_api_key
            _need_poi = [s for s in _all_universe if s.get("lat") and s.get("lng") and not s.get("poi_count",0)]
            if _need_poi and _poi_api_key:
                _scrape_status.info(f"Step E: POI count for {len(_need_poi):,} stores...")
                _poi_done = 0
                _poi_start = time.time()
                for _pi, _s in enumerate(_need_poi):
                    if st.session_state.get("_cancel_scrape"):
                        _scrape_status.warning(f"Step E: Cancelled at {_pi}/{len(_need_poi)}. Saving progress...")
                        break
                    try:
                        _pr = _api_retry(
                            requests.get,
                            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                            params={"location":f"{_s['lat']},{_s['lng']}",
                                    "radius":_poi_radius_use,"key":_poi_api_key},
                            timeout=8)
                        _s["poi_count"] = len(_pr.json().get("results",[])) if _pr else 0
                        _poi_done += 1
                    except Exception:
                        _s["poi_count"] = 0
                    if (_pi+1) % 20 == 0 or _pi == len(_need_poi)-1:
                        _scrape_bar.progress(min(85 + int((_pi+1)/len(_need_poi)*14), 99))
                    # Batch checkpoint every 100 stores
                    if (_pi + 1) % CHECKPOINT_BATCH_SIZE == 0:
                        st.session_state["_scrape_checkpoint"] = {
                            "universe": list(_all_universe),
                            "step": f"poi_{_pi+1}",
                            "saved_at": time.strftime("%d %b %Y %H:%M"),
                        }
                    if (_pi+1) % 50 == 0 or _pi == len(_need_poi)-1:
                        _poi_elapsed = time.time() - _poi_start
                        _poi_rem = (_poi_elapsed/(_pi+1))*(len(_need_poi)-_pi-1) if _pi > 0 else 0
                        _scrape_status.info(
                            f"Step E: {_pi+1}/{len(_need_poi)} · {_poi_done} updated · "
                            f"  {fmt_time(_poi_rem).replace('~','')} remaining"
                        )
                    time.sleep(0.05)
                _scrape_status.info(f"Step E: POI enrichment complete — {_poi_done} stores updated.")

            # ── Save cache ────────────────────────────────────────────────────
            import datetime as _dt
            if "universe_cache" not in st.session_state:
                st.session_state["universe_cache"] = {}
            _n_port  = sum(1 for s in _all_universe if s.get("source")=="portfolio")
            _n_osm   = sum(1 for s in _all_universe if s.get("source")=="scraped")
            _n_rated = sum(1 for s in _all_universe if s.get("rating",0) > 0)
            _n_poi   = sum(1 for s in _all_universe if s.get("poi_count",0) > 0)
            st.session_state["universe_cache"][_cache_key] = {
                "universe":    _all_universe,
                "market_name": cfg.get("market_name",""),
                "scraped_at":  _dt.datetime.now().strftime("%d %b %Y %H:%M"),
                "categories":  cfg.get("categories",[]),
                "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
            }
            _scrape_bar.progress(100)
            # Clear checkpoint on successful completion
            if "_scrape_checkpoint" in st.session_state:
                del st.session_state["_scrape_checkpoint"]
            if "_cancel_scrape" in st.session_state:
                del st.session_state["_cancel_scrape"]
            _elapsed_total = time.time() - _scrape_t0
            _scrape_status.success(
                f"  Universe built: {len(_all_universe):,} stores total · "
                f"{_n_port} portfolio · {_n_osm} gap stores · "
                f"{_n_rated:,} with ratings · {_n_poi:,} with POI · "
                f"completed in {fmt_time(_elapsed_total)} · ready for pipeline runs."
            )
            st.rerun()

st.markdown("---")

# ── Derive enrich_scope from session (set in Step 2) ─────────────────────────
_run_enrich_cfg = st.session_state.get("admin_enrichment", {
    "run_place_details": True, "run_poi": True, "poi_radius_m": 500})
enrich_scope = "all" if _run_enrich_cfg.get("run_place_details", True) else "none"
st.session_state["enrich_scope"] = enrich_scope
enrich_count = 0  # enrichment done at scrape time

# ── STEP 3: RUN ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">3. Run the agent</div>', unsafe_allow_html=True)

# Inline readiness summary
_run_cache_check = st.session_state.get("universe_cache", {}).get(_scrape_cache_key(cfg))
_portfolio_ready = st.session_state.get("portfolio_df") is not None
_n_portfolio     = len(st.session_state["portfolio_df"]) if _portfolio_ready else 0
_geocode_cost    = round(_n_portfolio * PRICE_GEOCODE_PER_CALL, 2)

if _run_cache_check and _portfolio_ready:
    _cached_n_run = len(_run_cache_check["universe"])
    st.success(



        f"  Ready — **{_n_portfolio}** portfolio stores · "
        f"**{_cached_n_run:,}** universe stores cached · "
        f"estimated geocoding cost ~**${_geocode_cost}**"
    )
elif not _run_cache_check:
    st.warning("  Universe not scraped yet — go to Step 2 to scrape first. The pipeline will scrape on run if you proceed.")
elif not _portfolio_ready:
    st.warning("  No portfolio uploaded — go to Step 1.")

dry_run = st.checkbox(
    "Dry run mode — no API calls, generates sample data for testing",
    value=False
)
if not dry_run:
    _cached_check = st.session_state.get("universe_cache", {}).get(_scrape_cache_key(cfg))
    if _cached_check:
        st.info("  Live mode — universe cached, only geocoding costs apply.")
    else:
        st.warning("  Live mode will call Google APIs for scraping and geocoding.")

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

        if has_coords and not needs_geocode:
            status.info(f"Stage 1/{total_steps} — All {len(has_coords)} portfolio stores have coordinates — geocoding skipped.")
        elif has_coords:
            status.info(f"Stage 1/{total_steps} — {len(has_coords)} stores have coordinates · {len(needs_geocode)} need geocoding...")
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

        # Stage 2: Universe — use cache if available, scrape if not
        _run_cache_key  = _scrape_cache_key(cfg)
        _run_cache      = st.session_state.get("universe_cache", {}).get(_run_cache_key)

        if _run_cache:
            _cache_all = [dict(s) for s in _run_cache["universe"]]  # deep copy
            # Cache contains portfolio + gap stores combined (built in Step 2)
            # Split back: gap stores go to universe, portfolio stores already in portfolio var
            universe = [s for s in _cache_all if s.get("source") != "portfolio"]
            # Also update portfolio store ratings/coords from cache if enriched in Step 2
            _cache_port = {s.get("store_id","") or s.get("store_name",""): s
                           for s in _cache_all if s.get("source") == "portfolio"}
            for p in portfolio:
                _key = p.get("store_id","") or p.get("store_name","")
                if _key in _cache_port:
                    _cp = _cache_port[_key]
                    # Bring enriched fields back from cache into live portfolio
                    for _f in ["rating","review_count","price_level","place_id",
                               "phone","opening_hours","website","lat","lng"]:
                        if _cp.get(_f) and not p.get(_f):
                            p[_f] = _cp[_f]
                        elif _f in ["rating","review_count"] and _cp.get(_f,0) > p.get(_f,0):
                            p[_f] = _cp[_f]
            _n_port_cache = len(_cache_port)
            _n_gap_cache  = len(universe)
            status.info(
                f"Stage 2/{total_steps} — Cache loaded: "
                f"{_n_port_cache} portfolio + {_n_gap_cache} gap stores "
                f"(scraped {_run_cache.get('scraped_at','')}) — skipping API scrape."
            )
            bar.progress(45)
        else:



            # No cache — scrape now (and save to cache for future runs)
            status.warning(
                "No cached universe found. Scraping now — "
                "consider using the 'Scrape market universe' button above to pre-cache."
            )
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



                                "phone":"","opening_hours":"","website":"",
                            })
                        token = data.get("next_page_token")
                        if not token: break
                    done_tiles += 1
                    pct     = 15 + int(done_tiles/total_tiles*30)
                    elapsed = time.time()-scrape_start
                    rem     = (elapsed/done_tiles)*(total_tiles-done_tiles) if done_tiles>0 else 0
                    status.info(f"Stage 2/{total_steps} — Scraping {cat}... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores |  {fmt_time(rem).replace('~','')} remaining")
                    bar.progress(pct)

            # Apply relevance filter

            # ── Relevance filter — replaces crude substring matching ──────────
            import re as _re

            # Exclusion: whole-word match only — avoids "hotel" hitting "chocolate"
            # These are standalone business types, not retail grocery
            _EXCL_WORDS = {
                # Food service (not retail)
                "cafe","café","coffee","karak","restaurant","pizzeria","pizza",
                "burger","grill","bbq","barbeque","shawarma","bakery","canteen",
                "cafeteria","cafè","eatery","diner","bistro","steakhouse",
                # Mobile & telecom
                "mobile","telecom","telephone","atm","exchange","forex",
                # Health
                "pharmacy","clinic","hospital","polyclinic","dispensary","dental",
                # Services
                "barber","salon","spa","gym","laundry","tailor","garage",
                # Non-retail
                "hotel","motel","hostel","resort","camp","desert camp",
                "school","nursery","mosque","church","temple","bank","insurance",
                "petrol","fuel","station","carwash",
            }

            def _is_relevant(store_name):
                name = str(store_name).strip()
                if not name or len(name) < 3:
                    return False

                name_lower = name.lower()
                # Split into words for whole-word matching
                words = set(_re.findall(r'[a-z]+', name_lower))

                # Reject if any exclusion word is a whole word in the name
                if words & _EXCL_WORDS:
                    return False



                # Reject obvious non-store codes: e.g. JBA29, C-45, plot numbers
                # Pattern: starts with 1-4 letters followed immediately by digits
                if _re.match(r'^[A-Z]{1,4}[0-9]+', name) and len(name) < 8:
                    return False

                # Reject names that are purely numeric or single characters
                if _re.match(r'^[0-9 \-]+$', name):
                    return False

                # Reject very short all-caps codes with no vowels (e.g. "WTRST", "JBLT")
                if (name.isupper() and len(name) <= 6
                        and not any(v in name.lower() for v in 'aeiou')):
                    return False

                return True
            _before  = len(universe)
            universe = [s for s in universe if _is_relevant(s.get("store_name",""))]
            if _before - len(universe) > 0:
                status.info(f"Stage 2/{total_steps} — Filtered {_before-len(universe)} irrelevant stores")

            # Auto-save to cache
            import datetime as _dt2
            if "universe_cache" not in st.session_state:
                st.session_state["universe_cache"] = {}
            st.session_state["universe_cache"][_run_cache_key] = {
                "universe":    universe,
                "market_name": cfg.get("market_name",""),
                "scraped_at":  _dt2.datetime.now().strftime("%d %b %Y %H:%M"),
                "categories":  cfg.get("categories",[]),
                "bbox":        [cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"]],
            }
            status.info(f"Stage 2/{total_steps} — Found {len(universe):,} stores (auto-saved to cache)")
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
        # Cap direct lookup at 200 stores — prioritise by score desc to get most value
        # Full lookup of 1000+ stores takes 20+ minutes — not worth it
        no_rating_port = sorted(
            [p for p in portfolio
             if p.get("lat") and p.get("lng")
             and not (p.get("rating") and float(p.get("rating") or 0) > 0)
             and p.get("store_name")],
            key=lambda x: float(x.get("score", 0) or 0), reverse=True



        )[:200]
        if no_rating_port and api_key:
            status.info(f"Stage 4/{total_steps} — Fetching Google data for {len(no_rating_port)} priority portfolio stores (top 200 by score)...")
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

        # ── Cluster assignment + filtering ───────────────────────────────────
        # Assign cluster_id to every store by nearest centroid (geocoord-based)
        _country_clusters = st.session_state.get("country_clusters", [])
        _selected_cids    = cfg.get("selected_cluster_ids", [])
        _lv_rule          = st.session_state.get("admin_low_value", {"min_stores":3,"max_score":30})

        if _country_clusters:
            all_stores = assign_cluster_to_stores(all_stores, _country_clusters)

            # Filter to selected clusters only
            if _selected_cids:
                all_stores = [s for s in all_stores if s.get("cluster_id") in _selected_cids]
                status.info(f"Cluster filter: {len(_selected_cids)} cluster(s) selected — "
                            f"{len(all_stores):,} stores in scope.")

            # Apply low-value area exclusion within each cluster
            # Group stores by cluster, check rule per cluster
            from collections import defaultdict as _dd
            cluster_groups = _dd(list)
            for s in all_stores:
                cluster_groups[s.get("cluster_id", 0)].append(s)

            excluded_ids = set()
            for cid, cstores in cluster_groups.items():
                if should_exclude_low_value_area(
                        cstores,
                        _lv_rule.get("min_stores", 3),



                        _lv_rule.get("max_score", 30)):
                    for s in cstores:
                        excluded_ids.add(id(s))

            if excluded_ids:
                n_excl = len(excluded_ids)
                all_stores = [s for s in all_stores if id(s) not in excluded_ids]
                status.info(f"Low-value exclusion: {n_excl} stores removed "
                            f"(areas with < {_lv_rule.get('min_stores',3)} stores "
                            f"AND avg score < {_lv_rule.get('max_score',30)}).")
        else:
            # No clusters defined — assign all to cluster 0
            for s in all_stores:
                s["cluster_id"]   = 0
                s["cluster_name"] = "All"

        # Update gap_stores after filtering
        gap_stores = [s for s in all_stores if s.get("coverage_status") == "gap"]

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
                status.info(f"Stage 6/{total_steps} — Building geographic rep territories...")
                # Geographic k-means: k = optimal_reps, one cluster per rep.
                # No city grouping, no supercities — pure geographic split.
                zone_centres, actual_reps = plan_reps_by_supercity(
                    None, priority,
                    daily_minutes=daily_minutes,
                    working_days=working_days,
                    avg_speed_kmh=avg_speed,
                    all_stores_ref=all_stores,
                )

                min_util_pct = 40  # informational only for merging

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

                # ── GUARANTEE exactly rep_count non-empty zones ──────────────
                # K-means can produce empty clusters when stores are
                # geographically concentrated. Force-split the largest
                # cluster until we have exactly rep_count non-empty zones.
                _actual_zones = len(set(labels))
                while _actual_zones < rep_count and len(priority) >= rep_count:
                    # Find the largest cluster
                    from collections import Counter as _Counter
                    _counts = _Counter(labels)
                    _biggest_lbl = max(_counts, key=lambda x: _counts[x])
                    if _counts[_biggest_lbl] < 2:
                        break  # can't split a single-store cluster

                    # Find an unused label
                    _used = set(labels)
                    _new_lbl = None
                    for _candidate in range(rep_count):
                        if _candidate not in _used:
                            _new_lbl = _candidate
                            break
                    if _new_lbl is None:
                        break

                    # Split: take the half of the biggest cluster that is
                    # furthest from the cluster centroid
                    _big_indices = [i for i, l in enumerate(labels) if l == _biggest_lbl]
                    _c_lat = sum(pts[i][0] for i in _big_indices) / len(_big_indices)
                    _c_lng = sum(pts[i][1] for i in _big_indices) / len(_big_indices)
                    _big_indices.sort(
                        key=lambda i: haversine_m(pts[i][0], pts[i][1], _c_lat, _c_lng),
                        reverse=True
                    )
                    # Move the furthest half to the new label
                    _half = len(_big_indices) // 2
                    for _idx in _big_indices[:_half]:
                        labels[_idx] = _new_lbl

                    _actual_zones = len(set(labels))

                # Remap labels to contiguous 0..N-1 so rep_ids are 1..N
                _unique_labels = sorted(set(labels))
                _label_map     = {old: new for new, old in enumerate(_unique_labels)}
                labels         = [_label_map[l] for l in labels]

                for s, lbl in zip(priority, labels):
                    s["rep_id"] = int(lbl) + 1

                # Calculate time utilisation per rep
                zone_centres = []
                monthly_cap  = effective_daily * working_days
                for zone in range(len(_unique_labels)):
                    zone_stores = [priority[i] for i in range(len(priority)) if labels[i] == zone]
                    if not zone_stores:
                        continue
                    centre_lat  = sum(s["lat"] for s in zone_stores) / len(zone_stores)
                    centre_lng  = sum(s["lng"] for s in zone_stores) / len(zone_stores)
                    zone_mins   = calculate_rep_time_budget(zone_stores, avg_speed)
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

                # Fixed mode: respect the user's configured rep count — do NOT
                # remove under-utilised zones. The user explicitly chose this count.
                #
                # Rebalance: ensure no rep is below 65% utilisation by moving
                # stores from neighbouring over-65% zones. Stores only move
                # to geographically close zones (never across the city).
                min_util_pct   = 65
                status.info(f"Stage 6/{total_steps} — Rebalancing zones to ≥{min_util_pct}% utilisation...")
                _n_moved = rebalance_zones_65pct(
                    all_stores, zone_centres,
                    daily_minutes=daily_minutes,
                    working_days=working_days,
                    avg_speed_kmh=avg_speed,
                    min_util_pct=min_util_pct,
                    max_passes=5,
                )
                if _n_moved > 0:
                    status.info(f"Stage 6/{total_steps} — Rebalanced: moved {_n_moved} stores to raise under-utilised zones.")

                min_util_mins  = (daily_minutes - break_minutes) * working_days * min_util_pct / 100
                under_util     = [z for z in zone_centres if z.get("time_needed_min",0) < min_util_mins]
                kept_zones_f   = zone_centres  # keep ALL zones in fixed mode

                rep_recommendation = {
                    "mode":                "fixed",
                    "rep_count":           rep_count,  # always the user's configured value
                    "daily_minutes":       daily_minutes,
                    "working_days":        working_days,
                    "avg_speed_kmh":       avg_speed,
                    "break_minutes":       break_minutes,
                    "monthly_cap_per_rep": effective_daily * working_days,
                    "min_utilisation_pct": min_util_pct,
                    "under_utilised_zones": [z["zone"] for z in under_util],
                    "zone_centres":        kept_zones_f,
                    "stores_rebalanced":   _n_moved,
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

        # In fixed mode, if all_rep_ids is fewer than configured, log a warning
        _cfg_rep_count = cfg.get("rep_count", 0)
        if rep_recommendation and rep_recommendation.get("mode") == "fixed" and len(all_rep_ids) < _cfg_rep_count:
            status.warning(
                f"Zone assignment produced {len(all_rep_ids)} rep IDs but {_cfg_rep_count} were configured. "
                f"Rep IDs found: {all_rep_ids}. Zone centres: {len(zone_centres)}."
            )

        _total_route_stores = sum(
            1 for s in all_stores
            if s.get("rep_id", 0) > 0 and s.get("size_tier") in ("Large", "Medium", "Small")
        )
        status.info(
            f"Stage 6b — Building {plan_period}-month route plan for "
            f"{len(all_rep_ids)} reps · {_total_route_stores:,} stores..."
        )

        # Clear ALL route fields BEFORE building routes
        for s in all_stores:
            s["assigned_day"]    = ""
            s["day_visit_order"] = 0
            for mk in plan_month_keys:
                s[f"{mk}_weeks"]  = []
                s[f"{mk}_visits"] = 0
            s["plan_visits"] = 0

        # Build day assignments
        _route_t0 = time.time()
        for _ri, rep_id in enumerate(all_rep_ids):
            try:
                rep_stores = [s for s in all_stores
                    if s.get("rep_id") == rep_id
                    and s.get("size_tier") in ("Large","Medium","Small")]
                if rep_stores:
                    status.info(
                        f"Stage 6b — Rep {_ri+1}/{len(all_rep_ids)} "
                        f"({len(rep_stores)} stores)..."
                    )
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

        # Convert abstract week labels → real calendar dates using get_month_weekdays
        # e.g. "Week 1 - Monday" → "07 Apr" for April 2026
        _month_calendars = {}
        for mk, (yr, mo) in zip(plan_month_keys, plan_months_ym):
            _month_calendars[mk] = get_month_weekdays(yr, mo)

        WEEK_NUM_MAP = {"Week 1": 0, "Week 2": 1, "Week 3": 2, "Week 4": 3, "Week 5": 4}

        for s in all_stores:
            for mk in plan_month_keys:
                raw_weeks = s.get(f"{mk}_weeks", [])
                real_dates = []
                cal = _month_calendars.get(mk, {})
                for wk_label in raw_weeks:
                    # wk_label format: "Week 1 - Monday"
                    parts = wk_label.split(" - ")
                    if len(parts) == 2:
                        wk_part  = parts[0].strip()   # "Week 1"
                        day_part = parts[1].strip()    # "Monday"
                        wk_idx   = WEEK_NUM_MAP.get(wk_part, 0)
                        day_dates = cal.get(day_part, [])
                        if wk_idx < len(day_dates):
                            real_dates.append(day_dates[wk_idx].strftime("%d %b"))
                s[f"{mk}_dates"] = real_dates

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
        # ── Post-route rebalancing loop ─────────────────────────────────────
        # For each rep, look at every actual calendar date they have stores on.
        # If a date has > 538 min (exec + inter-store travel + break):
        #   → move stores to dates where the same rep has < 450 min
        #   → travel cap (25%) is relaxed here — day window (420-550) is the hard rule
        # Loop until no day exceeds 538 min or no improvement is possible (max 50 passes).
        # All moves stay within the same rep.

        REBAL_MAX   = 538   # trigger move if day exceeds this
        REBAL_MIN   = 450   # target days below this to receive stores
        HARD_MAX    = 550   # absolute ceiling
        HARD_MIN    = 420   # absolute floor
        BREAK_MIN   = 30    # fixed break

        all_rep_ids_post = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0)>0))
        min_exec_month   = 6500

        def _day_len(stores_list):
            """exec + inter-store travel + break. First/last leg excluded."""
            if not stores_list:



                return BREAK_MIN
            exec_t   = sum(s.get("visit_duration_min", 25) for s in stores_list)
            travel_t = sum(
                travel_time_minutes(
                    stores_list[i-1]["lat"], stores_list[i-1]["lng"],
                    stores_list[i]["lat"],   stores_list[i]["lng"],
                    avg_speed
                )
                for i in range(1, len(stores_list))
                if stores_list[i-1].get("lat") and stores_list[i].get("lat")
            )
            return exec_t + travel_t + BREAK_MIN

        def _nn_reseq(stores):
            """Re-sequence a list of stores using nearest-neighbour from centroid."""
            if len(stores) <= 1:
                return stores[:]
            c_lat = sum(s["lat"] for s in stores if s.get("lat")) / max(1, sum(1 for s in stores if s.get("lat")))
            c_lng = sum(s["lng"] for s in stores if s.get("lng")) / max(1, sum(1 for s in stores if s.get("lng")))
            result, remaining = [], stores[:]
            cur_lat, cur_lng  = c_lat, c_lng
            while remaining:
                nn = min(remaining, key=lambda s: haversine_m(
                    cur_lat, cur_lng, s.get("lat", cur_lat), s.get("lng", cur_lng)))
                result.append(nn)
                cur_lat, cur_lng = nn.get("lat", cur_lat), nn.get("lng", cur_lng)
                remaining.remove(nn)
            return result

        def _get_rep_day_map(rid):
            """
            Returns dict: {assigned_day: [sorted stores]}
            Uses assigned_day (weekday name) as the grouping key.
            """
            day_map = {}
            for s in all_stores:
                if (s.get("rep_id") == rid
                        and s.get("assigned_day")
                        and s.get("plan_visits", 0) > 0
                        and s.get("size_tier") in ("Large", "Medium", "Small")
                        and s.get("lat") and s.get("lng")):
                    d = s["assigned_day"]
                    day_map.setdefault(d, []).append(s)
            # Sort each day by visit order
            for d in day_map:
                day_map[d].sort(key=lambda s: s.get("day_visit_order", 99))
            return day_map



        for rid in all_rep_ids_post:
            # Loop until stable or max passes reached
            for _pass in range(50):
                day_map  = _get_rep_day_map(rid)
                if not day_map:
                    break

                # Find the most overloaded day (highest day_len above REBAL_MAX)
                over_days = {
                    d: _day_len(stores)
                    for d, stores in day_map.items()
                    if _day_len(stores) > REBAL_MAX
                }
                if not over_days:
                    break   # all days within target — done for this rep

                # Pick the worst overloaded day
                worst_day    = max(over_days, key=over_days.get)
                worst_stores = day_map[worst_day]

                # Find the lightest receiving day (day_len < REBAL_MIN)
                light_days = {
                    d: _day_len(stores)
                    for d, stores in day_map.items()
                    if d != worst_day and _day_len(stores) < REBAL_MIN
                }

                if not light_days:
                    # No day below 450 — try any day below HARD_MAX
                    light_days = {
                        d: _day_len(stores)
                        for d, stores in day_map.items()
                        if d != worst_day and _day_len(stores) < HARD_MAX
                    }

                if not light_days:
                    break   # nowhere to move stores — stop for this rep

                best_target = min(light_days, key=light_days.get)
                target_stores = day_map[best_target]

                # Find the store in worst_day that:
                #   1. When removed, reduces worst day length the most
                #   2. When added to target, keeps target <= HARD_MAX
                best_move_idx  = -1
                best_reduction = -1



                current_worst_len = over_days[worst_day]

                for idx, candidate in enumerate(worst_stores):
                    # Day length after removing this store
                    remaining     = worst_stores[:idx] + worst_stores[idx+1:]
                    remaining_seq = _nn_reseq(remaining) if remaining else []
                    new_worst_len = _day_len(remaining_seq) if remaining_seq else BREAK_MIN

                    # Day length after adding to target
                    target_seq    = _nn_reseq(target_stores + [candidate])
                    new_target_len = _day_len(target_seq)

                    reduction = current_worst_len - new_worst_len

                    # Only accept if:
                    #  - worst day actually gets shorter
                    #  - target day stays within hard max
                    #  - remaining worst day stays above hard min (if it still has stores)
                    if (reduction > 0.5
                            and new_target_len <= HARD_MAX
                            and (not remaining_seq or new_worst_len >= HARD_MIN)):
                        if reduction > best_reduction:
                            best_reduction = reduction
                            best_move_idx  = idx

                if best_move_idx < 0:
                    break   # no valid move found — stop

                # Execute the move
                moved = worst_stores.pop(best_move_idx)
                moved["assigned_day"] = best_target

                # Re-sequence both days and update visit orders
                new_worst_seq  = _nn_reseq(worst_stores)  if worst_stores  else []
                new_target_seq = _nn_reseq(target_stores + [moved])

                for i, s in enumerate(new_worst_seq):
                    s["assigned_day"]    = worst_day
                    s["day_visit_order"] = i + 1
                for i, s in enumerate(new_target_seq):
                    s["assigned_day"]    = best_target
                    s["day_visit_order"] = i + 1

            # end pass loop for this rep

        # Exec floor merge removed — rep count is fixed by plan_reps_by_supercity.



        # The rebalancing loop above handles redistributing stores within reps.

        # ── Final metrics recalculation ──────────────────────────────────────────
        # Use zone_centres as source of truth for time_needed (exec+travel, no break)
        # This is what drives rep count — must be consistent with what Results shows
        routed_stores = [s for s in all_stores if s.get("plan_visits",0) > 0 and s.get("rep_id",0) > 0]
        if routed_stores and rep_recommendation:
            # Count actual reps with routed stores
            kept_reps = sorted(set(s.get("rep_id",0) for s in routed_stores if s.get("rep_id",0)>0))
            n_kept    = len(kept_reps)

            # total exec+travel from zone_centres (already recalculated above)
            zc_total = sum(z.get("time_needed_min",0) for z in zone_centres)

            # Correct rep count = ceil(total_exec_travel / eff_cap_per_rep)
            # eff_cap = (daily_minutes - break) × working_days — exec+travel only
            _eff_cap = (daily_minutes - 30) * working_days  # 9,900
            correct_reps = max(1, math.ceil(zc_total / _eff_cap)) if zc_total > 0 else n_kept

            rep_recommendation["total_minutes_needed"] = round(zc_total)
            rep_recommendation["monthly_cap_per_rep"]  = round(_eff_cap)
            rep_recommendation["recommended_reps"]     = correct_reps
            # In fixed mode, preserve the user's configured rep count
            if rep_recommendation.get("mode") == "fixed":
                rep_recommendation["actual_routed_reps"] = rep_recommendation.get("rep_count", n_kept)
            else:
                rep_recommendation["actual_routed_reps"] = n_kept

        bar.progress(80)

        # Stage 7: Place Details enrichment
        # Skip entirely if cache was used — all enrichment done in Step 2
        enriched    = 0
        _used_cache = st.session_state.get("universe_cache", {}).get(_run_cache_key) is not None
        if enrich_scope != "none" and not _used_cache:
            status.info(f"Stage 7/{total_steps} — Enriching stores with phone & opening hours...")
            candidates   = [s for s in all_stores if s.get("place_id","")]
            enriched     = 0
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
                    if result.get("price_level") is not None:
                        store["price_level"] = int(result["price_level"])



                    if result.get("rating") and float(result["rating"]) > 0:
                        store["rating"] = float(result["rating"])
                    if result.get("user_ratings_total") and int(result["user_ratings_total"]) > 0:
                        store["review_count"] = int(result["user_ratings_total"])
                    enriched += 1
                pct = 80 + int((i+1)/max(len(candidates),1)*17)
                rem = (time.time()-enrich_start)/(i+1)*(len(candidates)-i-1) if i>0 else 0
                status.info(
                    f"Stage 7/{total_steps} — Enriching... {i+1}/{len(candidates)} | "
                    f"{enriched} updated |  {fmt_time(rem).replace('~','')} remaining"
                )
                bar.progress(min(pct,97))
                time.sleep(0.1)
        elif _used_cache:
            status.info(f"Stage 7/{total_steps} — Skipping place details enrichment (already done in Step 2 cache).")
            bar.progress(97)

        # Stage POI: Nearby POI enrichment
        # Skip if cache was used — POI is now done in Step 2 (cache build)
        if enrich_poi != "none":
            poi_stage = total_steps - (1 if enrich_scope == "none" else 0)
            if _used_cache:
                status.info(
                    f"Stage {poi_stage}/{total_steps} — POI enrichment skipped "
                    f"(already done in Step 2 cache)."
                )
                bar.progress(99)
            else:
                # Only runs when no cache — fallback live enrichment
                _already_has_poi = sum(1 for s in all_stores if s.get("poi_count",0) > 0)
                if _already_has_poi > len(all_stores) * 0.5:
                    status.info(f"Stage {poi_stage}/{total_steps} — POI already present for most stores — skipping.")
                    bar.progress(99)
                else:
                    status.info(f"Stage {poi_stage}/{total_steps} — Enriching stores with nearby POI count...")
                    poi_candidates = [s for s in all_stores if s.get("lat") and s.get("lng") and not s.get("poi_count",0)]
                    poi_enriched = 0
                    poi_start    = time.time()
                    for i, store in enumerate(poi_candidates):
                        try:
                            r = requests.get(PLACES_URL,
                                params={"location":f"{store['lat']},{store['lng']}",
                                        "radius":poi_radius,"key":api_key},
                                timeout=8)
                            store["poi_count"] = len(r.json().get("results",[]))
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

        if _used_cache:
            enrich_msg = " · enrichment already in cache (skipped)"
        elif enrich_scope != "none" and enriched > 0:
            enrich_msg = f" · {enriched} stores enriched with phone & hours"
        else:
            enrich_msg = ""
        status.success(
            f"  Pipeline complete in {actual_time} · actual cost ~${actual_cost:.2f} · "
            f"{len(all_stores):,} stores scored · {len(gap_stores):,} gaps found{enrich_msg}. "
            f"Open Results in the sidebar."
        )
