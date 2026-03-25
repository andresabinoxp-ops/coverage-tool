import streamlit as st
import pandas as pd
import time
import math
import requests
import random

st.set_page_config(page_title="Run Pipeline - Coverage Tool", page_icon="📤", layout="wide")
st.title("Run Pipeline")

if not st.session_state.get("market_config"):
    st.warning("No market configured. Please go to Configure in the sidebar first.")
    st.stop()

cfg = st.session_state["market_config"]

st.info(f"""
Market: **{cfg['market_name']}** |
Reps: **{cfg['rep_count']}** |
Scraping categories: **{', '.join(cfg['categories'])}**
""")

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL  = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
TIER_MULT   = {1: 1.0, 2: 0.8, 3: 0.55, 4: 0.30}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_api_key():
    if cfg.get("market_api_key"):
        return cfg["market_api_key"]
    try:
        key = st.secrets["GOOGLE_MAPS_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    st.error("No Google Maps API key found. Use Dry Run to test, or ask admin to set GOOGLE_MAPS_API_KEY in Secrets.")
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
                new_c.append((
                    sum(p[0] for p in cluster) / len(cluster),
                    sum(p[1] for p in cluster) / len(cluster)
                ))
            else:
                new_c.append(centroids[j])
        centroids = new_c
    return labels

def assign_freq(score, t):
    if score >= t["weekly"]:      return "weekly",      4.0
    if score >= t["fortnightly"]: return "fortnightly", 2.0
    if score >= t["monthly"]:     return "monthly",     1.0
    return "bi-weekly", 0.5

# ── PORTFOLIO UPLOAD ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("1. Upload your store portfolio CSV")
st.markdown("Required columns: `store_name`, `address`, `city` | Optional: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`")

# Check if already uploaded in Configure page
if st.session_state.get("portfolio_df") is not None:
    portfolio_df = st.session_state["portfolio_df"]
    st.success(f"Using portfolio uploaded in Configure — {len(portfolio_df)} stores")
    st.dataframe(portfolio_df.head(3), use_container_width=True)
    if st.checkbox("Upload a different portfolio file"):
        portfolio_df = None
        st.session_state["portfolio_df"] = None
else:
    portfolio_df = None

if portfolio_df is None:
    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])
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
                if "category" not in portfolio_df.columns:
                    portfolio_df["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"
                st.success(f"Loaded {len(portfolio_df)} stores")
                st.dataframe(portfolio_df.head(3), use_container_width=True)
                st.session_state["portfolio_df"] = portfolio_df
        except Exception as e:
            st.error(f"Error reading file: {e}")

sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Road","city":"Dubai","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Spinneys JBR",     "address":"Marina Walk",      "city":"Dubai","category":"supermarket","annual_sales_usd":87000, "lines_per_store":42},
    {"store_id":"S003","store_name":"Boots Pharmacy",   "address":"Business Bay",     "city":"Dubai","category":"pharmacy",   "annual_sales_usd":22000, "lines_per_store":12},
])
st.download_button("Download sample CSV template", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")
st.subheader("2. Run the coverage agent")

dry_run = st.checkbox("Dry run mode — no API calls, generates sample data for testing", value=True)
if not dry_run:
    st.warning("Live mode will call Google APIs and use your API credits.")

run_btn = st.button("Run Coverage Agent", type="primary")

if run_btn:
    status = st.empty()
    bar    = st.progress(0)

    weights    = cfg["weights"]
    thresholds = cfg["thresholds"]
    cat_tiers  = cfg["category_tiers"]

    # ── DRY RUN ───────────────────────────────────────────────────────────────
    if dry_run:
        status.info("Dry run — generating sample data...")

        base = portfolio_df.to_dict("records") if portfolio_df is not None else [
            {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Rd","city":"Dubai","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
            {"store_id":"S002","store_name":"Spinneys JBR",     "address":"Marina Walk",   "city":"Dubai","category":"supermarket","annual_sales_usd":87000, "lines_per_store":42},
            {"store_id":"S003","store_name":"Boots Pharmacy",   "address":"Business Bay",  "city":"Dubai","category":"pharmacy",   "annual_sales_usd":22000, "lines_per_store":12},
        ]

        all_stores = []

        # Portfolio stores (covered)
        for row in base:
            sc = random.randint(50, 100)
            freq, cpm = assign_freq(sc, thresholds)
            all_stores.append({
                "store_id":         row.get("store_id","S0"),
                "store_name":       row.get("store_name","Store"),
                "address":          row.get("address",""),
                "city":             row.get("city",""),
                "category":         row.get("category", cfg["categories"][0] if cfg["categories"] else "supermarket"),
                "lat":              cfg["lat_min"] + random.uniform(0.01, max(cfg["lat_max"]-cfg["lat_min"]-0.01, 0.02)),
                "lng":              cfg["lng_min"] + random.uniform(0.01, max(cfg["lng_max"]-cfg["lng_min"]-0.01, 0.02)),
                "rating":           round(random.uniform(3.5, 4.9), 1),
                "review_count":     random.randint(100, 3000),
                "annual_sales_usd": float(row.get("annual_sales_usd", 0)),
                "lines_per_store":  int(row.get("lines_per_store", 0)),
                "covered":          True,
                "source":           "portfolio",
                "score":            sc,
                "visit_frequency":  freq,
                "calls_per_month":  cpm,
                "rep_id":           random.randint(1, cfg["rep_count"]),
                "coverage_status":  "covered",
            })

        # Scraped universe (gaps) — use same categories as portfolio
        store_name_prefixes = ["Metro", "City", "Quick", "Fresh", "Express", "Central", "Star", "Royal", "Golden", "Prime"]
        for i in range(60):
            cat = random.choice(cfg["categories"])
            sc  = random.randint(10, 95)
            freq, cpm = assign_freq(sc, thresholds)
            all_stores.append({
                "store_id":         f"G{i:03d}",
                "store_name":       f"{random.choice(store_name_prefixes)} {cat.replace('_',' ').title()} {i+1}",
                "address":          f"{random.randint(1,200)} Sample Street",
                "city":             cfg["city"],
                "category":         cat,
                "lat":              cfg["lat_min"] + random.uniform(0.01, max(cfg["lat_max"]-cfg["lat_min"]-0.01, 0.02)),
                "lng":              cfg["lng_min"] + random.uniform(0.01, max(cfg["lng_max"]-cfg["lng_min"]-0.01, 0.02)),
                "rating":           round(random.uniform(2.8, 4.9), 1),
                "review_count":     random.randint(10, 5000),
                "annual_sales_usd": 0.0,
                "lines_per_store":  0,
                "covered":          False,
                "source":           "scraped",
                "score":            sc,
                "visit_frequency":  freq,
                "calls_per_month":  cpm,
                "rep_id":           random.randint(1, cfg["rep_count"]) if sc >= thresholds["monthly"] else 0,
                "coverage_status":  "gap",
            })

        bar.progress(100)
        gap_stores = sorted([s for s in all_stores if s["coverage_status"]=="gap"], key=lambda x: x["score"], reverse=True)
        covered_n  = sum(1 for s in all_stores if s["covered"])

        st.session_state["run_results"] = {
            "all_stores":             all_stores,
            "gap_stores":             gap_stores,
            "coverage_rate_before":   round(len(base)/max(len(all_stores),1)*100, 1),
            "coverage_rate_after":    round(covered_n/max(len(all_stores),1)*100, 1),
            "portfolio":              [s for s in all_stores if s["source"]=="portfolio"],
            "universe":               [s for s in all_stores if s["source"]=="scraped"],
        }
        st.session_state["last_market"] = cfg["market_name"]
        status.success(f"Dry run complete — {len(all_stores)} stores generated ({len(base)} portfolio + {len(all_stores)-len(base)} scraped). Open Results or Routes in the sidebar.")

    # ── LIVE RUN ──────────────────────────────────────────────────────────────
    else:
        api_key   = get_api_key()
        portfolio = portfolio_df.to_dict("records") if portfolio_df is not None else []

        for s in portfolio:
            s.update({
                "covered":      True,
                "source":       "portfolio",
                "lat":          None,
                "lng":          None,
                "rating":       0.0,
                "review_count": 0,
            })
            if "category" not in s:
                s["category"] = cfg["categories"][0] if cfg["categories"] else "supermarket"

        # Stage 2: Geocode
        status.info(f"Stage 2/7 — Geocoding {len(portfolio)} portfolio stores...")
        bar.progress(10)
        for s in portfolio:
            lat, lng = geocode_store(s.get("address",""), s.get("city",""), api_key)
            s["lat"], s["lng"] = lat, lng
            time.sleep(0.05)
        bar.progress(25)

        # Stage 3: Scrape — only the categories from portfolio
        status.info(f"Stage 3/7 — Scraping Google Places for: {', '.join(cfg['categories'])}...")
        centres   = grid_centres(cfg["lat_min"], cfg["lat_max"], cfg["lng_min"], cfg["lng_max"])
        seen_ids  = set()
        universe  = []
        total_tiles = max(len(centres) * len(cfg["categories"]), 1)
        done_tiles  = 0

        for cat in cfg["categories"]:
            for lat, lng in centres:
                token = None
                while True:
                    data = fetch_places(lat, lng, 2000, cat, api_key, token)
                    for place in data.get("results", []):
                        pid = place.get("place_id","")
                        if pid in seen_ids:
                            continue
                        seen_ids.add(pid)
                        loc = place.get("geometry",{}).get("location",{})
                        universe.append({
                            "store_id":         pid,
                            "place_id":         pid,
                            "store_name":       place.get("name",""),
                            "address":          place.get("vicinity",""),
                            "city":             cfg["city"],
                            "lat":              loc.get("lat"),
                            "lng":              loc.get("lng"),
                            "rating":           float(place.get("rating",0) or 0),
                            "review_count":     int(place.get("user_ratings_total",0) or 0),
                            "category":         cat,
                            "annual_sales_usd": 0.0,
                            "lines_per_store":  0,
                            "covered":          False,
                            "source":           "scraped",
                        })
                    token = data.get("next_page_token")
                    if not token:
                        break
                done_tiles += 1
                bar.progress(25 + int(done_tiles/total_tiles*25))

        status.info(f"Stage 3/7 — Found {len(universe)} stores in universe")
        bar.progress(50)

        # Stage 4: Score
        status.info("Stage 4/7 — Scoring all stores...")
        all_stores = portfolio + universe
        max_rev    = max((s.get("review_count",0) for s in all_stores), default=1) or 1
        max_sales  = max((s.get("annual_sales_usd",0) for s in portfolio), default=1) or 1
        max_lines  = max((s.get("lines_per_store",0) for s in portfolio), default=1) or 1

        for s in all_stores:
            tier  = cat_tiers.get(s.get("category",""), 4)
            cat_n = TIER_MULT.get(tier, 0.30)
            r_n   = (s.get("rating",0) or 0) / 5
            rv_n  = math.log1p(s.get("review_count",0) or 0) / math.log1p(max_rev)
            sal_n = (s.get("annual_sales_usd",0) or 0) / max_sales if s.get("covered") else 0.0
            lin_n = (s.get("lines_per_store",0) or 0) / max_lines if s.get("covered") else 0.0
            s["score"] = min(100, round((
                r_n   * weights["rating"]   +
                rv_n  * weights["reviews"]  +
                cat_n * weights["category"] +
                sal_n * weights["sales"]    +
                lin_n * weights["lines"]
            ) * 100))
        bar.progress(65)

        # Stage 5: Gap match
        status.info("Stage 5/7 — Matching coverage gaps (50m radius)...")
        covered_p = [s for s in portfolio if s.get("lat") and s.get("lng")]
        for u in universe:
            if not (u.get("lat") and u.get("lng")):
                u["coverage_status"] = "no_coords"
                continue
            matched = any(haversine_m(u["lat"],u["lng"],p["lat"],p["lng"]) <= 50 for p in covered_p)
            u["covered"]         = matched
            u["coverage_status"] = "covered" if matched else "gap"
        for p in portfolio:
            p["coverage_status"] = "covered"
        bar.progress(75)

        # Stage 6: Frequency
        status.info("Stage 6/7 — Assigning visit frequencies...")
        for s in all_stores:
            freq, cpm = assign_freq(s.get("score",0), thresholds)
            s["visit_frequency"] = freq
            s["calls_per_month"] = cpm
        bar.progress(82)

        # Stage 7: Routes
        status.info("Stage 7/7 — Allocating rep routes...")
        priority = [s for s in all_stores if s.get("score",0) >= thresholds["monthly"] and s.get("lat") and s.get("lng")]
        if priority:
            pts    = [(s["lat"],s["lng"]) for s in priority]
            labels = kmeans_simple(pts, cfg["rep_count"])
            for s, lbl in zip(priority, labels):
                s["rep_id"] = int(lbl) + 1
        for s in all_stores:
            if "rep_id" not in s:
                s["rep_id"] = 0
        bar.progress(95)

        gap_stores = sorted([s for s in universe if s.get("coverage_status")=="gap"], key=lambda x: x.get("score",0), reverse=True)
        covered_n  = sum(1 for s in all_stores if s.get("covered"))

        st.session_state["run_results"] = {
            "all_stores":           all_stores,
            "gap_stores":           gap_stores,
            "coverage_rate_before": round(len(covered_p)/max(len(universe),1)*100, 1),
            "coverage_rate_after":  round(covered_n/max(len(all_stores),1)*100, 1),
            "portfolio":            portfolio,
            "universe":             universe,
        }
        st.session_state["last_market"] = cfg["market_name"]
        bar.progress(100)
        status.success(f"Pipeline complete — {len(all_stores):,} stores scored, {len(gap_stores):,} gaps found. Open Results in the sidebar.")
