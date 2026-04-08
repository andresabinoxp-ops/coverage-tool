import streamlit as st
import pandas as pd
import time
import math
import requests
import random

st.set_page_config(page_title="Run Pipeline — Coverage Tool", page_icon=" ", layout="wide")
st.title("Run Pipeline")

if not st.session_state.get("market_config"):
    st.warning("No market configured. Please go to Configure in the sidebar first.")
    st.stop()

cfg = st.session_state["market_config"]
st.info(f"Market: {cfg['market_name']} | Reps: {cfg['rep_count']} | Categories: {len(cfg['categories'])}")

# ── Session state init ────────────────────────────────────────────────────────
if "scraped_universe" not in st.session_state:
    st.session_state["scraped_universe"] = None
if "scrape_market" not in st.session_state:
    st.session_state["scrape_market"] = None

# ── Constants ─────────────────────────────────────────────────────────────────
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL  = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
TIER_MULT   = {1: 1.0, 2: 0.8, 3: 0.55, 4: 0.30}

def get_api_key():
    if cfg.get("market_api_key"):
        return cfg["market_api_key"]
    try:
        key = st.secrets["GOOGLE_MAPS_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    st.error("No Google Maps API key found. Use Dry Run mode or ask admin to set the key in Secrets.")
    st.stop()

def geocode_store(address, city, api_key):
    try:
        r = requests.get(GEOCODE_URL, params={"address": f"{address}, {city}", "key": api_key}, timeout=10)
        data = r.json()



        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception:
        pass
    return None, None

def grid_centres(lat_min, lat_max, lng_min, lng_max, radius_m=2000):
    dlat = (radius_m * 2) / 111320
    mid  = (lat_min + lat_max) / 2
    dlng = (radius_m * 2) / (111320 * math.cos(math.radians(mid)))
    centres = []
    lat = lat_min + dlat / 2
    while lat < lat_max:
        lng = lng_min + dlng / 2
        while lng < lng_max:
            centres.append((round(lat, 5), round(lng, 5)))
            lng += dlng
        lat += dlat
    return centres

def fetch_places(lat, lng, radius, place_type, api_key, token=None):
    try:
        if token:
            time.sleep(2)
            params = {"pagetoken": token, "key": api_key}
        else:
            params = {"location": f"{lat},{lng}", "radius": radius, "type": place_type, "key": api_key}
        r = requests.get(PLACES_URL, params=params, timeout=15)
        return r.json()
    except Exception:
        return {}

def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def kmeans_simple(points, k, iterations=20):
    if len(points) <= k:
        return list(range(len(points)))
    centroids = random.sample(points, k)
    labels = [0] * len(points)
    for _ in range(iterations):



        for i, p in enumerate(points):
            dists = [haversine_m(p[0], p[1], c[0], c[1]) for c in centroids]
            labels[i] = dists.index(min(dists))
        new_c = []
        for j in range(k):
            cluster = [points[i] for i in range(len(points)) if labels[i] == j]
            if cluster:
                new_c.append((sum(p[0] for p in cluster)/len(cluster), sum(p[1] for p in cluster)/len(cluster)))
            else:
                new_c.append(centroids[j])
        centroids = new_c
    return labels

def assign_freq(score, t):
    if score >= t["weekly"]:      return "weekly",      4.0
    if score >= t["fortnightly"]: return "fortnightly", 2.0
    if score >= t["monthly"]:     return "monthly",     1.0
    return "bi-weekly", 0.5

def run_scoring(portfolio, universe, cfg):
    weights    = cfg["weights"]
    thresholds = cfg["thresholds"]
    cat_tiers  = cfg["category_tiers"]
    all_stores = portfolio + universe

    max_rev   = max((s.get("review_count", 0) for s in all_stores), default=1) or 1
    max_sales = max((s.get("annual_sales_usd", 0) for s in portfolio), default=1) or 1
    max_lines = max((s.get("lines_per_store", 0) for s in portfolio), default=1) or 1

    for s in all_stores:
        tier  = cat_tiers.get(s.get("category", ""), 4)
        cat_n = TIER_MULT.get(tier, 0.30)
        r_n   = (s.get("rating", 0) or 0) / 5
        rv_n  = math.log1p(s.get("review_count", 0) or 0) / math.log1p(max_rev)
        sal_n = (s.get("annual_sales_usd", 0) or 0) / max_sales if s.get("covered") else 0.0
        lin_n = (s.get("lines_per_store", 0) or 0) / max_lines if s.get("covered") else 0.0
        s["score"] = min(100, round((r_n*weights["rating"] + rv_n*weights["reviews"] + cat_n*weights["category"] + sal_n*weights["sales"] + lin_n*weights["lines"]) * 100))

    covered_p = [s for s in portfolio if s.get("lat") and s.get("lng")]
    for u in universe:
        if not (u.get("lat") and u.get("lng")):
            u["coverage_status"] = "no_coords"
            u["covered"] = False
            continue
        matched = any(haversine_m(u["lat"], u["lng"], p["lat"], p["lng"]) <= 50 for p in covered_p)
        u["covered"] = matched
        u["coverage_status"] = "covered" if matched else "gap"



    for p in portfolio:
        p["coverage_status"] = "covered"

    for s in all_stores:
        freq, cpm = assign_freq(s.get("score", 0), thresholds)
        s["visit_frequency"]  = freq
        s["calls_per_month"]  = cpm

    priority = [s for s in all_stores if s.get("score", 0) >= thresholds["monthly"] and s.get("lat") and s.get("lng")]
    if priority:
        pts    = [(s["lat"], s["lng"]) for s in priority]
        labels = kmeans_simple(pts, cfg["rep_count"])
        for s, lbl in zip(priority, labels):
            s["rep_id"] = int(lbl) + 1
    for s in all_stores:
        if "rep_id" not in s:
            s["rep_id"] = 0

    gap_stores = sorted([s for s in universe if s.get("coverage_status") == "gap"], key=lambda x: x.get("score", 0), reverse=True)
    covered_n  = sum(1 for s in all_stores if s.get("covered"))

    return {
        "all_stores": all_stores,
        "gap_stores": gap_stores,
        "coverage_rate_before": round(len(covered_p) / max(len(universe), 1) * 100, 1),
        "coverage_rate_after":  round(covered_n / max(len(all_stores), 1) * 100, 1),
        "portfolio": portfolio,
        "universe":  universe,
    }

# ── Mode ──────────────────────────────────────────────────────────────────────
st.markdown("---")
dry_run = st.checkbox("Dry run mode — no API calls, uses sample data to test the app", value=False)
st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# STAGE A — Scrape (run once per market, result saved in session)
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Stage A — Scrape universe")
st.caption("Run once per market. Result is saved — you will not need to scrape again unless you want fresh data.")

already_scraped = (
    st.session_state["scraped_universe"] is not None and
    st.session_state["scrape_market"] == cfg["market_name"]
)

if already_scraped:



    n = len(st.session_state["scraped_universe"])
    st.success(f"Already scraped {n:,} stores for {cfg['market_name']} — ready to use.")
    btn_scrape_label = "Re-Scrape (refresh Google Places data)"
    btn_scrape_type  = "secondary"
else:
    st.warning("No scraped data yet. Click Scrape Universe to fetch stores from Google Places.")
    btn_scrape_label = "Scrape Universe"
    btn_scrape_type  = "primary"

if st.button(btn_scrape_label, type=btn_scrape_type):
    status = st.empty()
    bar    = st.progress(0)

    if dry_run:
        status.info("Dry run — generating sample universe...")
        store_names = ["Carrefour", "Spinneys", "Nesto", "Waitrose", "Choithrams",
                       "West Zone", "Geant", "Zoom", "Aster Pharmacy", "Al Maya",
                       "Lulu", "Union Coop", "Viva", "Day to Day", "Grandiose"]
        universe = []
        for i in range(60):
            universe.append({
                "store_id": f"P{i:03d}", "place_id": f"P{i:03d}",
                "store_name": random.choice(store_names) + f" {i+1}",
                "address": "Sample street", "city": cfg["market_name"],
                "lat": cfg["lat_min"] + random.uniform(0.01, max(cfg["lat_max"]-cfg["lat_min"]-0.01, 0.02)),
                "lng": cfg["lng_min"] + random.uniform(0.01, max(cfg["lng_max"]-cfg["lng_min"]-0.01, 0.02)),
                "rating": round(random.uniform(2.8, 4.9), 1),
                "review_count": random.randint(10, 5000),
                "category": random.choice(cfg["categories"]),
                "annual_sales_usd": 0.0, "lines_per_store": 0,
                "covered": False, "source": "scraped",
            })
        bar.progress(100)
        st.session_state["scraped_universe"] = universe
        st.session_state["scrape_market"]    = cfg["market_name"]
        status.success(f"Done — {len(universe)} sample stores generated.")
        st.rerun()

    else:
        api_key     = get_api_key()
        centres     = grid_centres(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"])
        seen_ids    = set()
        universe    = []
        total_tiles = max(len(centres) * len(cfg["categories"]), 1)
        done_tiles  = 0

        for cat in cfg["categories"]:



            for lat, lng in centres:
                token = None
                while True:
                    data = fetch_places(lat, lng, 2000, cat, api_key, token)
                    for place in data.get("results", []):
                        pid = place.get("place_id", "")
                        if pid in seen_ids: continue
                        seen_ids.add(pid)
                        loc = place.get("geometry", {}).get("location", {})
                        universe.append({
                            "store_id": pid, "place_id": pid,
                            "store_name": place.get("name", ""),
                            "address": place.get("vicinity", ""),
                            "city": cfg["market_name"],
                            "lat": loc.get("lat"), "lng": loc.get("lng"),
                            "rating": float(place.get("rating", 0) or 0),
                            "review_count": int(place.get("user_ratings_total", 0) or 0),
                            "category": cat,
                            "annual_sales_usd": 0.0, "lines_per_store": 0,
                            "covered": False, "source": "scraped",
                        })
                    token = data.get("next_page_token")
                    if not token: break
                done_tiles += 1
                bar.progress(int(done_tiles / total_tiles * 100))
                status.info(f"Scraping... {done_tiles}/{total_tiles} tiles | {len(universe):,} stores found")

        st.session_state["scraped_universe"] = universe
        st.session_state["scrape_market"]    = cfg["market_name"]
        status.success(f"Scrape complete — {len(universe):,} stores found. Now upload your portfolio and run Stage B.")
        st.rerun()

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# STAGE B — Portfolio upload + Score + Gap + Routes
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Stage B — Upload portfolio and run agent")
st.caption("Fast — geocodes your stores, scores everything, finds gaps and allocates routes. Re-run anytime.")

if not already_scraped:
    st.warning("Complete Stage A first.")
else:
    st.markdown("**Upload your store portfolio CSV**")
    st.markdown("Required columns: `store_name`, `address`, `city` | Optional: `store_id`, `annual_sales_usd`, `lines_per_store`")

    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])



    portfolio_df = None

    if uploaded:
        try:
            portfolio_df = pd.read_csv(uploaded)
            portfolio_df.columns = [c.strip().lower().replace(" ", "_") for c in portfolio_df.columns]
            missing = [c for c in ["store_name", "address", "city"] if c not in portfolio_df.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
                portfolio_df = None
            else:
                if "store_id" not in portfolio_df.columns:
                    portfolio_df["store_id"] = [f"S{i+1:03d}" for i in range(len(portfolio_df))]
                if "annual_sales_usd" not in portfolio_df.columns:
                    portfolio_df["annual_sales_usd"] = 0
                if "lines_per_store" not in portfolio_df.columns:
                    portfolio_df["lines_per_store"] = 0
                st.success(f"Loaded {len(portfolio_df)} stores")
                st.dataframe(portfolio_df.head(5), use_container_width=True)
        except Exception as e:
            st.error(f"Error reading file: {e}")

    sample = pd.DataFrame([
        {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Road","city":"Dubai","annual_sales_usd":125000,"lines_per_store":54},
        {"store_id":"S002","store_name":"Spinneys JBR",     "address":"Marina Walk",      "city":"Dubai","annual_sales_usd":87000, "lines_per_store":42},
    ])
    st.download_button("Download sample CSV template", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

    st.markdown(" ")

    if st.button("Run Coverage Agent", type="primary"):
        status = st.empty()
        bar    = st.progress(0)
        universe = list(st.session_state["scraped_universe"])

        if dry_run:
            base = portfolio_df.to_dict("records") if portfolio_df is not None else [
                {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Rd","city":"Dubai","annual_sales_usd":125000,"lines_per_store":54},
                {"store_id":"S002","store_name":"Spinneys JBR","address":"Marina Walk","city":"Dubai","annual_sales_usd":87000,"lines_per_store":42},
            ]
            portfolio = []
            for row in base:
                portfolio.append({
                    "store_id": row.get("store_id","S0"),
                    "store_name": row.get("store_name","Store"),
                    "address": row.get("address",""),
                    "city": row.get("city",""),



                    "lat": cfg["lat_min"] + random.uniform(0.01, max(cfg["lat_max"]-cfg["lat_min"]-0.01, 0.02)),
                    "lng": cfg["lng_min"] + random.uniform(0.01, max(cfg["lng_max"]-cfg["lng_min"]-0.01, 0.02)),
                    "rating": round(random.uniform(3.5, 4.9), 1),
                    "review_count": random.randint(100, 3000),
                    "category": random.choice(cfg["categories"]),
                    "annual_sales_usd": float(row.get("annual_sales_usd", 0)),
                    "lines_per_store": int(row.get("lines_per_store", 0)),
                    "covered": True, "source": "portfolio",
                })
            bar.progress(50)
            status.info("Scoring and matching gaps...")

        else:
            if portfolio_df is None:
                st.error("Please upload a portfolio CSV first.")
                st.stop()
            api_key   = get_api_key()
            portfolio = portfolio_df.to_dict("records")
            for s in portfolio:
                s.update({"covered":True,"source":"portfolio","lat":None,"lng":None,"rating":0.0,"review_count":0,"category":"portfolio"})
            status.info(f"Geocoding {len(portfolio)} portfolio stores...")
            for i, s in enumerate(portfolio):
                lat, lng = geocode_store(s.get("address",""), s.get("city",""), api_key)
                s["lat"], s["lng"] = lat, lng
                time.sleep(0.05)
                bar.progress(int((i+1)/len(portfolio)*50))
            status.info("Scoring, gap matching and allocating routes...")

        results = run_scoring(portfolio, universe, cfg)
        bar.progress(100)
        st.session_state["run_results"]  = results
        st.session_state["last_market"]  = cfg["market_name"]
        status.success(f"Complete — {len(results['all_stores']):,} stores scored, {len(results['gap_stores']):,} gaps found. Open Results in the sidebar.")
