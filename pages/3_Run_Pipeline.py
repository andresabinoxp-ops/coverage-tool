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
.stat-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin-bottom: 1rem;
}
.stat-box {
    background: white; border-radius: 8px; padding: 0.8rem 1rem;
    text-align: center; border: 1px solid #E0E0E0;
}
.stat-val   { font-size: 1.5rem; font-weight: 800; color: #1A2B4A; line-height: 1; }
.stat-label { font-size: 0.72rem; color: #9E9E9E; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }
.suggestion-box {
    background: white; border-radius: 6px; padding: 0.7rem 1rem;
    border-left: 3px solid #FFA726; font-size: 0.85rem;
    color: #4A4A4A; margin-top: 0.5rem;
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
    <p>Upload your current store portfolio and execute the full 7-stage coverage agent</p>
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
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL  = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
TIER_MULT   = {1:1.0, 2:0.8, 3:0.55, 4:0.30}
MAX_TILES   = 400   # hard cap — never exceed this regardless of area size

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
    """
    Automatically choose the tile radius so the total tiles stay under max_tiles.
    Returns (radius_m, n_tiles, warning_msg).
    """
    mid  = (lat_min + lat_max) / 2
    lat_span_m = abs(lat_max - lat_min) * 111320
    lng_span_m = abs(lng_max - lng_min) * 111320 * math.cos(math.radians(mid))
    area_m2    = lat_span_m * lng_span_m

    for radius_m in [1000, 2000, 3000, 5000, 8000, 10000, 15000, 20000, 30000, 50000]:
        tile_area  = (radius_m * 2) ** 2
        n_tiles    = math.ceil(area_m2 / tile_area)
        if n_tiles <= max_tiles:
            return radius_m, n_tiles, None

    # Even 50km tiles won't fit — use 50km and warn
    tile_area = (50000 * 2) ** 2
    n_tiles   = math.ceil(area_m2 / tile_area)
    return 50000, min(n_tiles, max_tiles), "The selected area is very large. For best results go to Configure and select specific cities rather than the full country."

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
    return centres[:MAX_TILES]   # hard cap safety

def estimate_scraping(cfg):
    """
    Calculate time estimate before scraping. Safe against pandas DataFrame bool check.
    """
    radius_m, n_tiles, area_warning = smart_tile_radius(
        cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"]
    )
    n_categories = len(cfg["categories"])

    # Fix: safe portfolio count — avoids pandas bool ambiguity error
    pf = st.session_state.get("portfolio_df")
    n_portfolio = len(pf) if pf is not None and hasattr(pf, "__len__") else 0

    avg_pages       = 1.8
    total_api_calls = round(n_tiles * n_categories * avg_pages)
    pagination_time = round(n_tiles * n_categories * (avg_pages - 1) * 2)
    call_time       = total_api_calls * 0.35
    geocode_time    = n_portfolio * 0.15
    total_seconds   = call_time + pagination_time + geocode_time + 15
    total_minutes   = total_seconds / 60

    lat_span = abs(cfg["lat_max"] - cfg["lat_min"])
    lng_span = abs(cfg["lng_max"] - cfg["lng_min"])
    mid      = (cfg["lat_min"] + cfg["lat_max"]) / 2
    area_km2 = round(lat_span * 111 * lng_span * 111 * math.cos(math.radians(mid)))

    if total_minutes < 5:
        colour, icon, label = "green", "✅", "Quick run — ready to go"
    elif total_minutes < 15:
        colour, icon, label = "amber", "⚠️", "Moderate run — consider narrowing the area"
    else:
        colour, icon, label = "red",   "🔴", "Long run — recommend selecting specific cities in Configure"

    suggestions = []
    if area_warning:
        suggestions.append(area_warning)
    if total_minutes > 5 and n_categories > 3:
        suggestions.append(f"Reduce categories from {n_categories} to 2-3 most important to save ~{round(total_minutes*(1-2/n_categories))} minutes.")
    if total_minutes > 10 and len(cfg.get("cities",[])) > 2:
        suggestions.append(f"You have {len(cfg.get('cities',[]))} cities selected. Run one city at a time to keep each run under 5 minutes.")
    if total_minutes > 15 and not area_warning:
        suggestions.append("Go to Configure and select a specific neighbourhood or district instead of the full city.")
    if not suggestions and total_minutes > 3:
        suggestions.append("Tip: Use Dry Run mode first to test the full pipeline without using API credits.")

    return {
        "radius_m":        radius_m,
        "n_tiles":         n_tiles,
        "n_categories":    n_categories,
        "total_api_calls": total_api_calls,
        "total_minutes":   total_minutes,
        "total_seconds":   total_seconds,
        "area_km2":        area_km2,
        "n_portfolio":     n_portfolio,
        "colour":          colour,
        "icon":            icon,
        "label":           label,
        "suggestions":     suggestions,
        "area_warning":    area_warning,
    }

def geocode_store(address, city, api_key):
    try:
        r = requests.get(GEOCODE_URL, params={"address":f"{address}, {city}","key":api_key}, timeout=10)
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
            new_c.append((sum(p[0] for p in cluster)/len(cluster),sum(p[1] for p in cluster)/len(cluster)) if cluster else centroids[j])
        centroids = new_c
    return labels

def assign_freq(score, t):
    if score >= t["weekly"]:      return "weekly",      4.0
    if score >= t["fortnightly"]: return "fortnightly", 2.0
    if score >= t["monthly"]:     return "monthly",     1.0
    return "bi-weekly", 0.5

def fmt_time(seconds):
    mins = seconds / 60
    if mins < 1:
        return f"~{round(seconds)} seconds"
    elif mins < 60:
        m = int(mins); s = int((mins-m)*60)
        return f"~{m} min {s} sec" if s > 0 else f"~{m} minutes"
    else:
        h = int(mins//60); m = int(mins%60)
        return f"~{h}h {m}min"

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
                if "store_id" not in df.columns: df["store_id"] = [f"S{i+1:03d}" for i in range(len(df))]
                if "annual_sales_usd" not in df.columns: df["annual_sales_usd"] = 0
                if "lines_per_store" not in df.columns: df["lines_per_store"] = 0
                if "category" not in df.columns: df["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"
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

# ── STEP 2: PRE-FLIGHT CHECK ──────────────────────────────────────────────────
st.markdown('<div class="section-title">2. Pre-flight estimate</div>', unsafe_allow_html=True)
st.caption("Calculated before you run — shows time, API calls and recommendations.")

est          = estimate_scraping(cfg)
time_display = fmt_time(est["total_seconds"])
colour_class = f"preflight-{est['colour']}"

# Tile radius label
radius_labels = {1000:"1 km",2000:"2 km",3000:"3 km",5000:"5 km",8000:"8 km",
                 10000:"10 km",15000:"15 km",20000:"20 km",30000:"30 km",50000:"50 km"}
radius_label = radius_labels.get(est["radius_m"], f"{est['radius_m']//1000} km")

st.markdown(f"""
<div class="preflight-card {colour_class}">
    <div class="preflight-title">{est['icon']} {est['label']}</div>
    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-val">{time_display}</div>
            <div class="stat-label">Estimated time</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{est['total_api_calls']:,}</div>
            <div class="stat-label">API calls</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{est['n_tiles']:,}</div>
            <div class="stat-label">Grid tiles</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{est['n_categories']}</div>
            <div class="stat-label">Categories</div>
        </div>
    </div>
    <div style="font-size:0.8rem;color:#6B7280;margin-bottom:0.6rem">
        Coverage area: ~{est['area_km2']:,} km² &nbsp;·&nbsp;
        Auto tile radius: {radius_label} &nbsp;·&nbsp;
        Portfolio stores: {est['n_portfolio']}
    </div>
    {''.join(f'<div class="suggestion-box">💡 {s}</div>' for s in est["suggestions"])}
</div>
""", unsafe_allow_html=True)

if est["colour"] != "green":
    st.markdown("""
**To reduce run time — go back to Configure and:**
- Select a specific city or neighbourhood instead of a full country or region
- Reduce the number of scraping categories to 2-3 most important
- Or use **Dry Run** below to test without using any API credits
    """)

# ── STEP 3: RUN ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">3. Run the agent</div>', unsafe_allow_html=True)

dry_run = st.checkbox("Dry run mode — no API calls, generates sample data for testing", value=True)
if not dry_run:
    st.warning(f"⚠️ Live mode will call Google APIs — estimated **{time_display}** and **{est['total_api_calls']:,} API calls**.")

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
            s.update({"covered":True,"source":"portfolio","lat":None,"lng":None,"rating":0.0,"review_count":0})
            if "category" not in s: s["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"

        # Use smart radius — same as pre-flight estimate
        radius_m, _, _ = smart_tile_radius(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"])
        centres = grid_centres(cfg["lat_min"],cfg["lat_max"],cfg["lng_min"],cfg["lng_max"],radius_m)

        # Stage 1: Geocode
        status.info(f"Stage 1/7 — Geocoding {len(portfolio)} portfolio stores...")
        bar.progress(8)
        for s in portfolio:
            lat,lng = geocode_store(s.get("address",""),s.get("city",""),api_key)
            s["lat"],s["lng"] = lat,lng
            time.sleep(0.05)
        bar.progress(20)

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
                            "store_id":pid,"place_id":pid,"store_name":place.get("name",""),
                            "address":place.get("vicinity",""),"city":cfg.get("city",""),
                            "lat":loc.get("lat"),"lng":loc.get("lng"),
                            "rating":float(place.get("rating",0) or 0),
                            "review_count":int(place.get("user_ratings_total",0) or 0),
                            "category":cat,"annual_sales_usd":0.0,"lines_per_store":0,
                            "covered":False,"source":"scraped",
                        })
                    token = data.get("next_page_token")
                    if not token: break
                done_tiles += 1
                pct      = 20 + int(done_tiles/total_tiles*45)
                elapsed  = time.time() - scrape_start
                rem      = (elapsed/done_tiles)*(total_tiles-done_tiles) if done_tiles > 0 else 0
                rem_str  = fmt_time(rem).replace("~","")
                status.info(f"Stage 2/7 — Scraping {cat}... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores found | ⏱ {rem_str} remaining")
                bar.progress(pct)

        bar.progress(65)
        status.info(f"Stage 2/7 — Scraping complete: {len(universe):,} unique stores found")

        # Stage 3: Score
        status.info("Stage 3/7 — Scoring all stores...")
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
        bar.progress(72)

        # Stage 4: Gap match
        status.info("Stage 4/7 — Matching coverage gaps...")
        covered_p = [s for s in portfolio if s.get("lat") and s.get("lng")]
        for u in universe:
            if not (u.get("lat") and u.get("lng")): u["coverage_status"]="no_coords"; continue
            matched = any(haversine_m(u["lat"],u["lng"],p["lat"],p["lng"])<=50 for p in covered_p)
            u["covered"]         = matched
            u["coverage_status"] = "covered" if matched else "gap"
        for p in portfolio: p["coverage_status"] = "covered"
        bar.progress(80)

        # Stage 5: Frequency
        status.info("Stage 5/7 — Assigning visit frequencies...")
        for s in all_stores:
            freq,cpm = assign_freq(s.get("score",0),thresholds)
            s["visit_frequency"] = freq
            s["calls_per_month"] = cpm
        bar.progress(87)

        # Stage 6: Routes
        status.info("Stage 6/7 — Allocating rep routes...")
        priority = [s for s in all_stores if s.get("score",0)>=thresholds["monthly"] and s.get("lat") and s.get("lng")]
        if priority:
            pts    = [(s["lat"],s["lng"]) for s in priority]
            labels = kmeans_simple(pts,cfg["rep_count"])
            for s,lbl in zip(priority,labels): s["rep_id"] = int(lbl)+1
        for s in all_stores:
            if "rep_id" not in s: s["rep_id"] = 0
        bar.progress(95)

        # Stage 7: Package
        status.info("Stage 7/7 — Packaging results...")
        gap_stores  = sorted([s for s in universe if s.get("coverage_status")=="gap"],key=lambda x:x.get("score",0),reverse=True)
        covered_n   = sum(1 for s in all_stores if s.get("covered"))
        actual_time = fmt_time(time.time()-scrape_start).replace("~","")
        st.session_state["run_results"] = {
            "all_stores":all_stores,"gap_stores":gap_stores,
            "coverage_rate_before":round(len(covered_p)/max(len(universe),1)*100,1),
            "coverage_rate_after":round(covered_n/max(len(all_stores),1)*100,1),
            "portfolio":portfolio,"universe":universe,
        }
        st.session_state["last_market"] = cfg["market_name"]
        bar.progress(100)
        status.success(f"✅ Pipeline complete in {actual_time} — {len(all_stores):,} stores scored, {len(gap_stores):,} gaps found. Open Results in the sidebar.")

# ── PLACE DETAILS ENRICHMENT ─────────────────────────────────────────────────
if st.session_state.get("run_results"):
    st.markdown('<div class="section-title">Enrich stores with phone and opening hours (optional)</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    This step calls the Google Places Details API to fetch <strong>phone numbers</strong> and
    <strong>opening hours</strong> for your top stores. Each store requires one additional API call,
    so you can choose how many stores to enrich to manage costs.
    <br><br>
    <strong>Estimated cost:</strong> ~$0.017 per store (Google Places Details API pricing).
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])
    with col1:
        enrich_count = st.slider(
            "Number of top stores to enrich (sorted by score)",
            min_value=10, max_value=200, value=50, step=10
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        estimated_cost = enrich_count * 0.017
        st.metric("Estimated API cost", f"${estimated_cost:.2f}")

    enrich_filter = st.multiselect(
        "Enrich only these coverage types (optional)",
        options=["covered","gap"],
        default=["covered","gap"],
        help="Select gap to only enrich gap stores — useful for prospecting calls."
    )

    if st.button("Fetch phone & opening hours", type="primary", key="btn_enrich"):
        if dry_run:
            st.warning("Switch off Dry Run mode to use enrichment with real API calls.")
        else:
            api_key = get_api_key()
            all_stores = st.session_state["run_results"]["all_stores"]

            # Get top stores by score matching filter
            candidates = [s for s in all_stores
                if s.get("coverage_status","") in enrich_filter
                and s.get("place_id","")]
            candidates = sorted(candidates, key=lambda x: x.get("score",0), reverse=True)[:enrich_count]

            enrich_bar    = st.progress(0)
            enrich_status = st.empty()
            enriched      = 0
            failed        = 0

            for i, store in enumerate(candidates):
                place_id = store.get("place_id","")
                if not place_id:
                    failed += 1
                    continue
                try:
                    r = requests.get(
                        "https://maps.googleapis.com/maps/api/place/details/json",
                        params={
                            "place_id": place_id,
                            "fields": "formatted_phone_number,opening_hours,website,formatted_address",
                            "key": api_key
                        },
                        timeout=10
                    )
                    data = r.json()
                    if data.get("status") == "OK":
                        result = data.get("result", {})
                        store["phone"]   = result.get("formatted_phone_number","")
                        store["website"] = result.get("website","")
                        if result.get("formatted_address"):
                            store["full_address"] = result["formatted_address"]
                        # Opening hours — get weekday text
                        oh = result.get("opening_hours",{})
                        weekday_text = oh.get("weekday_text",[])
                        store["opening_hours"] = " | ".join(weekday_text) if weekday_text else ""
                        enriched += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

                enrich_bar.progress((i+1)/len(candidates))
                enrich_status.info(f"Enriching... {i+1}/{len(candidates)} stores | {enriched} succeeded | {failed} failed")
                time.sleep(0.1)

            # Update session state
            st.session_state["run_results"]["all_stores"] = all_stores
            enrich_status.success(f"✅ Enrichment complete — {enriched} stores updated with phone and opening hours. View in Routes page.")
