import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Configure - Coverage Tool", page_icon="⚙️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1B4F9B; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.page-header { background: linear-gradient(135deg, #1B4F9B 0%, #2563C0 100%); padding: 28px 36px; border-radius: 12px; margin-bottom: 28px; }
.page-header h1 { color: white !important; font-size: 1.8rem !important; font-weight: 700 !important; margin: 0 0 4px 0 !important; }
.page-header p  { color: rgba(255,255,255,0.85) !important; font-size: 0.95rem !important; margin: 0 !important; }
hr { border: none; border-top: 1px solid #E2E8F0; margin: 20px 0; }
div.stButton > button { border-radius: 6px; font-weight: 600; border: 2px solid #1B4F9B; background: #1B4F9B; color: white; padding: 8px 24px; }
div.stButton > button:hover { background: #2563C0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>⚙️ Configure Market</h1>
    <p>Set up market location, scoring weights and pipeline parameters</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE GEOCODING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_api_key():
    try:
        key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
        return key if key else None
    except Exception:
        return None

def geocode_lookup(query, api_key):
    """Returns list of results from Google Geocoding API for a query."""
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query, "key": api_key},
            timeout=10
        )
        data = r.json()
        if data.get("status") == "OK":
            return data["results"]
    except Exception:
        pass
    return []

def extract_bbox(result):
    """Extract bounding box from a geocoding result."""
    vp = result.get("geometry", {}).get("viewport", {})
    sw = vp.get("southwest", {})
    ne = vp.get("northeast", {})
    if sw and ne:
        return (
            round(sw["lat"], 4),
            round(ne["lat"], 4),
            round(sw["lng"], 4),
            round(ne["lng"], 4),
        )
    # fallback to location point with small buffer
    loc = result.get("geometry", {}).get("location", {})
    if loc:
        lat, lng = loc["lat"], loc["lng"]
        return (round(lat-0.1,4), round(lat+0.1,4), round(lng-0.1,4), round(lng+0.1,4))
    return None

def extract_component(result, component_type):
    """Extract a specific address component from a geocoding result."""
    for comp in result.get("address_components", []):
        if component_type in comp.get("types", []):
            return comp.get("long_name", "")
    return ""

def search_location(query, api_key, restrict_type=None):
    """
    Search for a location. Returns list of (display_name, bbox, full_address).
    restrict_type: 'country', 'region', 'city' to help filter results.
    """
    results = geocode_lookup(query, api_key)
    if not results:
        return []

    options = []
    for r in results[:5]:  # top 5 results
        bbox         = extract_bbox(r)
        full_address = r.get("formatted_address", "")
        if bbox:
            options.append((full_address, bbox))
    return options


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY MAP & TIERS
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "supermarket":            "supermarket",
    "hypermarket":            "supermarket",
    "convenience store":      "convenience_store",
    "convenience_store":      "convenience_store",
    "minimarket":             "convenience_store",
    "mini market":            "convenience_store",
    "pharmacy":               "pharmacy",
    "chemist":                "pharmacy",
    "drugstore":              "pharmacy",
    "gas station":            "gas_station",
    "petrol station":         "gas_station",
    "gas_station":            "gas_station",
    "off licence":            "liquor_store",
    "liquor store":           "liquor_store",
    "liquor_store":           "liquor_store",
    "grocery":                "grocery_or_supermarket",
    "grocery store":          "grocery_or_supermarket",
    "grocery_or_supermarket": "grocery_or_supermarket",
    "dollar store":           "convenience_store",
    "variety store":          "convenience_store",
    "newsagent":              "convenience_store",
}

TIER_LABELS   = {1:"Tier 1 - 100% fit", 2:"Tier 2 - 80% fit", 3:"Tier 3 - 55% fit", 4:"Tier 4 - 30% fit"}
TIER_DEFAULTS = {
    "supermarket":1, "hypermarket":1, "convenience_store":1,
    "grocery_or_supermarket":1, "pharmacy":2, "gas_station":2, "liquor_store":2,
}

def merge_bboxes(boxes):
    return (
        min(b[0] for b in boxes),
        max(b[1] for b in boxes),
        min(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )

# ─────────────────────────────────────────────────────────────────────────────
# INITIALISE SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for key in ["country_name","country_bbox","region_entries","city_entries","portfolio_df"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "region_entries" not in st.session_state or st.session_state["region_entries"] is None:
    st.session_state["region_entries"] = []   # list of {name, bbox}

if "city_entries" not in st.session_state or st.session_state["city_entries"] is None:
    st.session_state["city_entries"] = []     # list of {name, bbox}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: PORTFOLIO UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("1. Upload your portfolio CSV")
st.markdown("""
Required columns: `store_name`, `address`, `city`
Optional columns: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`

The app reads the `category` column and automatically sets the scraping categories to match.
""")

uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"], key="config_upload")
portfolio_df       = None
detected_categories = []
google_categories  = []

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
        missing = [c for c in ["store_name","address","city"] if c not in df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
        else:
            if "store_id" not in df.columns:
                df["store_id"] = [f"S{i+1:03d}" for i in range(len(df))]
            if "annual_sales_usd" not in df.columns:
                df["annual_sales_usd"] = 0
            if "lines_per_store" not in df.columns:
                df["lines_per_store"] = 0
            portfolio_df = df
            st.success(f"Loaded {len(df)} stores")
            st.dataframe(df.head(5), use_container_width=True)

            if "category" in df.columns:
                raw_cats = df["category"].dropna().str.lower().str.strip().unique().tolist()
                detected_categories = raw_cats
                mapped = set()
                for cat in raw_cats:
                    gcat = CATEGORY_MAP.get(cat)
                    if gcat:
                        mapped.add(gcat)
                    else:
                        for key, val in CATEGORY_MAP.items():
                            if key in cat or cat in key:
                                mapped.add(val)
                                break
                google_categories = list(mapped)
                if google_categories:
                    st.info(f"Portfolio categories: **{', '.join(detected_categories)}**  →  Will scrape: **{', '.join(google_categories)}**")
                else:
                    st.warning("Could not match categories automatically. Select them manually in Step 4.")
            else:
                st.warning("No category column found. Select scraping categories manually in Step 4.")

            st.session_state["portfolio_df"] = portfolio_df
    except Exception as e:
        st.error(f"Error reading file: {e}")

# Sample download
sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Qurum","city":"Muscat","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Lulu Hypermarket", "address":"Al Khuwair","city":"Muscat","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
    {"store_id":"S003","store_name":"Pharmacy One",     "address":"Ruwi","city":"Muscat","category":"pharmacy","annual_sales_usd":22000,"lines_per_store":12},
    {"store_id":"S004","store_name":"Shell Station",    "address":"Ghubra","city":"Muscat","category":"gas station","annual_sales_usd":18000,"lines_per_store":8},
])
st.download_button("Download sample CSV template", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: COUNTRY
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("2. Select country")

api_key = get_api_key()
if not api_key:
    st.warning("Google Maps API key not set. Ask your admin to set GOOGLE_MAPS_API_KEY in Streamlit Secrets. Location search will not work until this is set.")

col1, col2 = st.columns([3, 1])
with col1:
    country_input = st.text_input(
        "Type country name",
        placeholder="e.g. Oman, Morocco, Pakistan, Ghana...",
        value=st.session_state.get("country_name") or "",
        key="country_input_field"
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_country_btn = st.button("Search country", type="primary", key="btn_country")

if search_country_btn and country_input:
    if not api_key:
        st.error("Cannot search — API key not set.")
    else:
        with st.spinner(f"Searching for {country_input}..."):
            results = search_location(f"{country_input} country", api_key)
        if results:
            # Try to find a result that is actually a country
            country_results = geocode_lookup(country_input, api_key)
            country_result  = None
            for r in country_results:
                types = r.get("types", [])
                if "country" in types:
                    country_result = r
                    break
            if not country_result and country_results:
                country_result = country_results[0]

            if country_result:
                bbox = extract_bbox(country_result)
                name = extract_component(country_result, "country") or country_input
                st.session_state["country_name"]    = name
                st.session_state["country_bbox"]    = bbox
                st.session_state["region_entries"]  = []
                st.session_state["city_entries"]    = []
                st.rerun()
            else:
                st.error(f"Could not find country: {country_input}")
        else:
            st.error(f"No results for {country_input}. Check spelling.")

if st.session_state.get("country_name"):
    st.success(f"Country set: **{st.session_state['country_name']}**")
    if st.button("Clear country and start over", key="clear_country"):
        st.session_state["country_name"]   = None
        st.session_state["country_bbox"]   = None
        st.session_state["region_entries"] = []
        st.session_state["city_entries"]   = []
        st.rerun()

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: REGIONS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("3. Add regions / governorates / states")
st.caption("Add one or more regions. Leave empty to cover the whole country.")

if not st.session_state.get("country_name"):
    st.info("Search and confirm a country first.")
else:
    country_name = st.session_state["country_name"]

    col1, col2 = st.columns([3, 1])
    with col1:
        region_input = st.text_input(
            "Type region / governorate / state name",
            placeholder=f"e.g. Muscat Governorate, Al Batinah, Dhofar...",
            key="region_input_field"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        add_region_btn = st.button("Add region", key="btn_region")

    if add_region_btn and region_input:
        if not api_key:
            st.error("Cannot search — API key not set.")
        else:
            with st.spinner(f"Searching for {region_input}..."):
                query   = f"{region_input}, {country_name}"
                results = geocode_lookup(query, api_key)
            if results:
                r    = results[0]
                bbox = extract_bbox(r)
                name = r.get("formatted_address", region_input).split(",")[0].strip()
                existing_names = [e["name"] for e in st.session_state["region_entries"]]
                if name in existing_names:
                    st.warning(f"{name} is already added.")
                else:
                    st.session_state["region_entries"].append({"name": name, "bbox": bbox})
                    st.rerun()
            else:
                st.error(f"Could not find {region_input} in {country_name}. Try a different spelling.")

    # Show added regions
    if st.session_state["region_entries"]:
        st.markdown("**Added regions:**")
        for i, entry in enumerate(st.session_state["region_entries"]):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"📍 {entry['name']}")
            with col_b:
                if st.button("Remove", key=f"remove_region_{i}"):
                    st.session_state["region_entries"].pop(i)
                    st.rerun()
    else:
        st.info("No regions added — the pipeline will cover the whole country bounding box.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: CITIES
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("4. Add cities / areas")
st.caption("Add one or more cities or specific areas to scrape. Be as granular as you need.")

if not st.session_state.get("country_name"):
    st.info("Search and confirm a country first.")
else:
    country_name = st.session_state["country_name"]

    col1, col2 = st.columns([3, 1])
    with col1:
        city_input = st.text_input(
            "Type city or area name",
            placeholder="e.g. Muscat, Salalah, Sohar, Al Seeb...",
            key="city_input_field"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        add_city_btn = st.button("Add city", key="btn_city")

    if add_city_btn and city_input:
        if not api_key:
            st.error("Cannot search — API key not set.")
        else:
            # Search with region context if available
            region_context = st.session_state["region_entries"][0]["name"] if st.session_state["region_entries"] else ""
            query = f"{city_input}, {region_context}, {country_name}" if region_context else f"{city_input}, {country_name}"
            with st.spinner(f"Searching for {city_input}..."):
                results = geocode_lookup(query, api_key)
            if results:
                r    = results[0]
                bbox = extract_bbox(r)
                name = r.get("formatted_address", city_input).split(",")[0].strip()
                existing_names = [e["name"] for e in st.session_state["city_entries"]]
                if name in existing_names:
                    st.warning(f"{name} is already added.")
                else:
                    st.session_state["city_entries"].append({"name": name, "bbox": bbox})
                    st.rerun()
            else:
                st.error(f"Could not find {city_input} in {country_name}. Try a different spelling.")

    # Show added cities
    if st.session_state["city_entries"]:
        st.markdown("**Added cities:**")
        for i, entry in enumerate(st.session_state["city_entries"]):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"🏙️ {entry['name']}")
            with col_b:
                if st.button("Remove", key=f"remove_city_{i}"):
                    st.session_state["city_entries"].pop(i)
                    st.rerun()
    else:
        st.info("No cities added — the pipeline will use the region or country bounding box.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# CALCULATE FINAL BOUNDING BOX
# ─────────────────────────────────────────────────────────────────────────────
final_bbox   = None
final_scope  = ""

if st.session_state["city_entries"]:
    boxes       = [e["bbox"] for e in st.session_state["city_entries"]]
    final_bbox  = merge_bboxes(boxes)
    final_scope = ", ".join(e["name"] for e in st.session_state["city_entries"])
elif st.session_state["region_entries"]:
    boxes       = [e["bbox"] for e in st.session_state["region_entries"]]
    final_bbox  = merge_bboxes(boxes)
    final_scope = ", ".join(e["name"] for e in st.session_state["region_entries"])
elif st.session_state.get("country_bbox"):
    final_bbox  = st.session_state["country_bbox"]
    final_scope = st.session_state["country_name"]

if final_bbox:
    st.success(f"Coverage area confirmed: **{final_scope}**")
elif st.session_state.get("country_name"):
    st.warning("Add at least one city or region to define the scraping area.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: MARKET DETAILS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("5. Market details")

country_name = st.session_state.get("country_name", "")
col1, col2, col3 = st.columns(3)
with col1:
    market_name = st.text_input("Market name", value=f"{country_name} - {final_scope}" if final_scope else country_name)
with col2:
    rep_count = st.number_input("Number of field reps", min_value=1, max_value=100, value=6)
with col3:
    market_api_key = st.text_input(
        "Market-specific Google API key (optional)",
        type="password",
        placeholder="Leave blank to use global admin key",
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6: SCRAPING CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("6. Scraping categories")

if google_categories:
    st.success(f"Auto-detected from portfolio — scraping: **{', '.join(google_categories)}**")
    extra = st.multiselect(
        "Add extra categories (optional)",
        options=[c for c in ["supermarket","convenience_store","pharmacy","gas_station",
                              "liquor_store","grocery_or_supermarket","hypermarket"]
                 if c not in google_categories],
        default=[]
    )
    final_categories = google_categories + extra
else:
    final_categories = st.multiselect(
        "Select categories to scrape from Google Places",
        options=["supermarket","convenience_store","pharmacy","gas_station",
                 "liquor_store","grocery_or_supermarket","hypermarket",
                 "dollar_store","variety_store"],
        default=["supermarket","convenience_store","pharmacy","gas_station"]
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: CATEGORY TIERS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("7. Category tier multipliers")
st.caption("Tier 1 = highest FMCG relevance (1.0 multiplier). Tier 4 = lowest (0.30).")

cat_tiers = {}
if final_categories:
    cols = st.columns(2)
    for i, cat in enumerate(final_categories):
        with cols[i % 2]:
            cat_tiers[cat] = st.selectbox(
                cat.replace("_"," ").title(),
                options=[1, 2, 3, 4],
                index=TIER_DEFAULTS.get(cat, 2) - 1,
                format_func=lambda x: TIER_LABELS[x],
                key=f"tier_{cat}"
            )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("8. Scoring weights — must sum to 100%")
st.caption("""
Each store gets a score 0-100 based on these five signals.
Gap stores score 0 on sales and lines — their upside is what you are discovering.
""")

col1, col2 = st.columns(2)
with col1:
    w_rating   = st.slider("Rating — Google star rating",           0, 50, 20)
    w_reviews  = st.slider("Reviews / footfall — store traffic",    0, 50, 25)
    w_category = st.slider("Category fit — store type relevance",   0, 50, 20)
with col2:
    w_sales    = st.slider("Current sales — your revenue there",    0, 50, 20)
    w_lines    = st.slider("Lines per store — products you stock",   0, 50, 15)

total = w_rating + w_reviews + w_category + w_sales + w_lines
if total == 100:
    st.success(f"Total: {total}% — valid")
else:
    st.error(f"Total: {total}% — must equal exactly 100%")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: FREQUENCY THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("9. Visit frequency thresholds")
st.caption("The agent assigns a visit tier to every store based on its score.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    f_weekly      = st.number_input("Weekly (score >=)",      min_value=1, max_value=99, value=80)
    st.caption("4 calls per month — anchor stores")
with col2:
    f_fortnightly = st.number_input("Fortnightly (score >=)", min_value=1, max_value=99, value=60)
    st.caption("2 calls per month")
with col3:
    f_monthly     = st.number_input("Monthly (score >=)",     min_value=1, max_value=99, value=40)
    st.caption("1 call per month")
with col4:
    st.markdown("**Bi-weekly**")
    st.caption(f"Score below {f_monthly} — 0.5 calls per month")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10: SAVE
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("10. Save configuration")

# Validation checks
issues = []
if not st.session_state.get("country_name"):
    issues.append("Search and confirm a country first.")
if not final_bbox:
    issues.append("Add at least one city or region.")
if total != 100:
    issues.append("Fix scoring weights to equal 100%.")
if not final_categories:
    issues.append("Select at least one scraping category.")

if issues:
    for issue in issues:
        st.warning(issue)
else:
    if st.button("Save market configuration", type="primary"):
        lat_min, lat_max, lng_min, lng_max = final_bbox
        st.session_state["market_config"] = {
            "market_name":             market_name,
            "country":                 st.session_state["country_name"],
            "regions":                 [e["name"] for e in st.session_state["region_entries"]],
            "cities":                  [e["name"] for e in st.session_state["city_entries"]],
            "city":                    final_scope,
            "lat_min":                 lat_min,
            "lat_max":                 lat_max,
            "lng_min":                 lng_min,
            "lng_max":                 lng_max,
            "rep_count":               int(rep_count),
            "categories":              final_categories,
            "category_tiers":          cat_tiers,
            "market_api_key":          market_api_key,
            "detected_from_portfolio": detected_categories,
            "weights": {
                "rating":   w_rating   / 100,
                "reviews":  w_reviews  / 100,
                "category": w_category / 100,
                "sales":    w_sales    / 100,
                "lines":    w_lines    / 100,
            },
            "thresholds": {
                "weekly":       f_weekly,
                "fortnightly":  f_fortnightly,
                "monthly":      f_monthly,
            },
        }
        st.markdown(f"""
        <div style="background:#E8F5E9;border:1.5px solid #66BB6A;border-left:5px solid #2E7D32;
        border-radius:8px;padding:1rem 1.4rem;margin:0.5rem 0">
            <div style="font-weight:700;color:#1B5E20;font-size:1rem;margin-bottom:4px">
                ✅ Configuration saved — {market_name}
            </div>
            <div style="color:#2E7D32;font-size:0.87rem">
                Market area, scoring weights, categories and frequency thresholds have been saved.
                Go to <strong>Run Pipeline</strong> in the sidebar to upload your portfolio and start the agent.
            </div>
        </div>
        """, unsafe_allow_html=True)

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
