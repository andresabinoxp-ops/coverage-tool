import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Configure - Coverage Tool", page_icon="⚙️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Sidebar navy blue ── */
/* ── Sidebar navy blue ── */
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #FFFFFF !important; }
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

# Hardcoded category tier multipliers — not editable by users
TIER_MULT = {1:1.0, 2:0.80, 3:0.55, 4:0.30}
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
        df = None
        for _enc in ["utf-8","utf-8-sig","latin-1","cp1252","cp1256","iso-8859-1"]:
            try:
                uploaded.seek(0)
                df = pd.read_csv(uploaded, encoding=_enc)
                break
            except (UnicodeDecodeError, Exception):
                continue
        if df is None:
            st.error("Could not read the file — please save as UTF-8 CSV.")
            st.stop()
        df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
        # Drop blank rows
        df = df.dropna(subset=["store_name","address","city"], how="all").reset_index(drop=True)
        df = df[df["store_name"].fillna("").str.strip() != ""].reset_index(drop=True)
        if "lat" not in df.columns: df["lat"] = None
        if "lng" not in df.columns: df["lng"] = None
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

# Template download
st.markdown("""
<div style="background:#F0F4FF;border:1px solid #C7D7F5;border-radius:8px;padding:1rem 1.2rem;margin-bottom:0.8rem;font-size:0.85rem;line-height:1.7">
<strong>📋 Template column guide</strong><br><br>
<strong>Required columns:</strong><br>
• <code>store_name</code> — the store name as you know it<br>
• <code>address</code> — street address (e.g. "Rua das Flores, 123")<br>
• <code>city</code> — city name (e.g. "Recife", "Cairo", "Dubai") — used for geocoding<br><br>
<strong>Optional location columns</strong> — add whichever apply to your market. You can use different column names — the tool auto-detects common variants:<br>
• <strong>Sub-city area</strong>: <code>district</code>, <code>area</code>, <code>neighbourhood</code>, <code>bairro</code>, <code>zone</code>, <code>suburb</code> — e.g. "Boa Viagem", "Maadi", "Deira"<br>
• <strong>Region/State</strong>: <code>region</code>, <code>state</code>, <code>governorate</code>, <code>province</code>, <code>county</code>, <code>wilaya</code> — e.g. "Pernambuco", "Cairo Governorate", "Dubai Emirate"<br>
• <strong>Coordinates</strong>: <code>lat</code> and <code>lng</code> — if you already have GPS coordinates, the tool will skip geocoding for those stores and save API cost<br><br>
<strong>Optional data columns:</strong><br>
• <code>store_id</code> — your internal ID (auto-generated if missing)<br>
• <code>category</code> — store type (e.g. "supermarket", "pharmacy") — used for scraping and scoring<br>
• <code>annual_sales_usd</code> — your sales at this store — used in scoring<br>
• <code>lines_per_store</code> — number of your SKUs listed at this store — used in scoring<br>
</div>
""", unsafe_allow_html=True)

sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Av. Conselheiro Aguiar, 2500","city":"Recife","district":"Boa Viagem","region":"Pernambuco","lat":"","lng":"","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Atacadão Recife",  "address":"Av. Caxangá, 2900",          "city":"Recife","district":"Iputinga",  "region":"Pernambuco","lat":"","lng":"","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
    {"store_id":"S003","store_name":"Farmácia Pague Menos","address":"Rua da Aurora, 500",      "city":"Recife","district":"Boa Vista", "region":"Pernambuco","lat":"","lng":"","category":"pharmacy",   "annual_sales_usd":22000, "lines_per_store":12},
    {"store_id":"S004","store_name":"Posto Ipiranga",   "address":"Av. Agamenon Magalhães, 100","city":"Recife","district":"Derby",     "region":"Pernambuco","lat":"","lng":"","category":"gas station","annual_sales_usd":18000, "lines_per_store":8},
])
st.download_button("⬇️ Download portfolio template", sample.to_csv(index=False), "portfolio_template.csv", "text/csv")

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
col1, col2 = st.columns(2)
with col1:
    market_name = st.text_input("Market name", value=f"{country_name} - {final_scope}" if final_scope else country_name)
with col2:
    market_api_key = st.text_input(
        "Market-specific Google API key (optional)",
        type="password",
        placeholder="Leave blank to use global admin key",
    )

import datetime as _dt
_today = _dt.date.today()
col_rm1, col_rm2, col_rm3 = st.columns(3)
with col_rm1:
    route_month1 = st.selectbox("Route start month",
        options=list(range(1,13)),
        index=_today.month - 1,
        format_func=lambda m: _dt.date(2025,m,1).strftime("%B"),
        help="The agent builds routes for this month and the following month."
    )
with col_rm2:
    route_year = st.number_input("Year", min_value=2024, max_value=2030, value=_today.year)
with col_rm3:
    _m2 = route_month1 % 12 + 1
    _y2 = int(route_year) + (1 if _m2 == 1 else 0)
    m1_label = _dt.date(int(route_year), route_month1, 1).strftime("%B %Y")
    m2_label = _dt.date(_y2, _m2, 1).strftime("%B %Y")
    st.metric("2-month plan", f"{m1_label} + {m2_label}")
st.caption("Day-of-week assignments are fixed across both months. Occasional stores (0.5 visits/month) get 1 visit in this 2-month window.")

st.markdown("---")
st.subheader("5b. Rep planning mode")
st.caption("Choose how you want to handle rep allocation — fixed headcount or let the agent recommend.")

rep_mode = st.radio(
    "Rep planning approach",
    options=["Fixed — I know how many reps I have",
             "Recommended — tell me how many reps I need"],
    index=0,
    horizontal=True,
)

rep_count     = 6
rep_mode_key  = "fixed"
calls_per_day = 10
working_days  = 22

if rep_mode == "Fixed — I know how many reps I have":
    rep_mode_key = "fixed"
    rep_count    = st.number_input(
        "Number of field reps",
        min_value=1, max_value=200, value=6,
        help="The pipeline will assign stores to exactly this many reps."
    )
    st.markdown("**Time parameters** — required for daily route building and utilisation calculation")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        daily_minutes = st.number_input("Total working day (min)", min_value=240, max_value=600, value=480,
            help="Full working day including travel and breaks.")
    with col2:
        break_minutes = st.number_input("Break time (min/day)",    min_value=0,   max_value=120, value=30,
            help="Lunch and rest breaks deducted from selling time.")
    with col3:
        working_days  = st.number_input("Working days per month",  min_value=15,  max_value=26,  value=22)
    with col4:
        avg_speed_kmh = st.number_input("Avg travel speed (km/h)", min_value=10,  max_value=80,  value=30)
else:
    rep_mode_key = "recommended"
    st.info(
        "The agent will calculate how many reps you need based on total store workload "
        "divided by your rep capacity. It will also show where to base each rep geographically."
    )

    st.markdown("**Rep capacity**")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        daily_minutes = st.number_input(
            "Total working day (min)", min_value=240, max_value=600, value=480,
            help="Full working day including travel and breaks. Default 480 = 8 hours."
        )
    with col2:
        break_minutes = st.number_input(
            "Break time (min/day)", min_value=0, max_value=120, value=30,
            help="Lunch and rest breaks. Deducted from daily capacity."
        )
    with col3:
        working_days = st.number_input(
            "Working days per month", min_value=15, max_value=26, value=22,
            help="Selling days per month after weekends and holidays."
        )
    with col4:
        avg_speed_kmh = st.number_input(
            "Avg travel speed (km/h)", min_value=10, max_value=80, value=30,
            help="30 km/h for city · 50 for suburban."
        )
    with col5:
        effective_daily = daily_minutes - break_minutes
        monthly_cap     = effective_daily * working_days
        st.metric("Effective capacity / month", f"{monthly_cap:,} min",
            help=f"({daily_minutes} - {break_minutes} break) × {working_days} days")
    st.caption(
        f"({daily_minutes} min/day − {break_minutes} min break) × {working_days} days = "
        f"{monthly_cap:,} min/month per rep available for visits and travel."
    )

    st.markdown("**Current headcount (optional)**")
    st.caption("Only used to compare against the recommendation — does not affect the calculation. Leave at 0 if unknown.")
    rep_count = st.number_input(
        "How many reps do you currently have?",
        min_value=0, max_value=200, value=0,
        help="Enter 0 to skip comparison. If you enter a number the Results page will show whether you are over or under-resourced."
    )
    if rep_count == 0:
        st.caption("No current headcount entered — the Results page will show the recommendation only, without a comparison.")
    else:
        st.caption(f"After the run the agent will compare its recommendation against your current {rep_count} reps and show the shortfall or surplus.")

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
# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: SCORING WEIGHTS
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7: VISIT BENCHMARKS PER CATEGORY
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("7. Visit benchmarks per category")
st.caption("""
Set how many times per month a rep should visit each store size tier, and how long each visit takes.
Store size is determined by score percentile within each category — e.g. top 20% of pharmacies = Large pharmacy.
Defaults come from Admin Settings. You can adjust per category here.
""")

# Pull admin defaults from session state if available
admin_defaults = st.session_state.get("admin_benchmarks", {
    "large_pct": 20, "medium_pct": 60, "small_pct": 20,
    "large_visits": 4, "medium_visits": 2, "small_visits": 1,
    "large_duration": 40, "medium_duration": 25, "small_duration": 15,
})

# Percentile splits (shown as info, configurable in Admin)
st.markdown("""
<div style="background:#E3F2FD;border:1px solid #90CAF9;border-left:4px solid #1565C0;
border-radius:8px;padding:0.8rem 1.2rem;margin:0.5rem 0;font-size:0.88rem;color:#0D47A1">
Store size percentile splits are set in <strong>Admin Settings</strong>.
Current splits: <strong>Large = top {large_pct}%</strong> &nbsp;·&nbsp;
<strong>Medium = middle {medium_pct}%</strong> &nbsp;·&nbsp;
<strong>Small = bottom {small_pct}%</strong> of each category by score.
</div>
""".format(
    large_pct=admin_defaults["large_pct"],
    medium_pct=admin_defaults["medium_pct"],
    small_pct=admin_defaults["small_pct"],
), unsafe_allow_html=True)

# Per-category benchmark table
visit_benchmarks = {}
if final_categories:
    st.markdown("**Set visits per month and visit duration (minutes) per category:**")
    # Header row
    hc0, hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([2,1,1,1,1,1,1])
    hc0.markdown("**Category**")
    hc1.markdown("**Large visits/mo**")
    hc2.markdown("**Large duration**")
    hc3.markdown("**Medium visits/mo**")
    hc4.markdown("**Medium duration**")
    hc5.markdown("**Small visits/mo**")
    hc6.markdown("**Small duration**")

    for cat in final_categories:
        cat_label = cat.replace("_"," ").title()
        c0,c1,c2,c3,c4,c5,c6 = st.columns([2,1,1,1,1,1,1])
        with c0:
            st.markdown(f"<div style='padding-top:8px;font-weight:600'>{cat_label}</div>", unsafe_allow_html=True)
        with c1:
            lv = st.number_input("", min_value=1, max_value=20,
                value=admin_defaults["large_visits"], key=f"lv_{cat}", label_visibility="collapsed")
        with c2:
            ld = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults["large_duration"], key=f"ld_{cat}", label_visibility="collapsed")
        with c3:
            mv = st.number_input("", min_value=1, max_value=20,
                value=admin_defaults["medium_visits"], key=f"mv_{cat}", label_visibility="collapsed")
        with c4:
            md = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults["medium_duration"], key=f"md_{cat}", label_visibility="collapsed")
        with c5:
            sv = st.number_input("", min_value=1, max_value=20,
                value=admin_defaults["small_visits"], key=f"sv_{cat}", label_visibility="collapsed")
        with c6:
            sd = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults["small_duration"], key=f"sd_{cat}", label_visibility="collapsed")
        visit_benchmarks[cat] = {
            "large_visits": int(lv), "large_duration": int(ld),
            "medium_visits": int(mv), "medium_duration": int(md),
            "small_visits": int(sv), "small_duration": int(sd),
        }
else:
    st.info("Select scraping categories first (Step 6).")
    visit_benchmarks = {}

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("8. Scoring weights — must sum to 100%")
st.caption("Each store receives a score 0-100 based on six signals. Gap stores score 0 on sales and lines. Affluence uses Google price level. POI requires optional enrichment after run.")

col1, col2 = st.columns(2)
with col1:
    w_rating    = st.slider("Rating — Google star rating (0-5)",       0, 50, 20)
    w_reviews   = st.slider("Reviews — footfall proxy (log-normalised)",0, 50, 25)
    w_affluence = st.slider("Affluence — Google price level (0-4)",    0, 50, 10,
        help="Higher price level = more premium store. Google captures this automatically during scraping.")
with col2:
    w_poi   = st.slider("Nearby POI — location quality (optional enrichment)", 0, 50, 15,
        help="Count of points of interest within radius. Requires POI enrichment step after pipeline run. Scores 0 if enrichment not run.")
    w_sales = st.slider("Current sales — your revenue at this store",  0, 50, 15)
    w_lines = st.slider("Lines per store — SKUs you sell there",       0, 50, 15)

total = w_rating + w_reviews + w_affluence + w_poi + w_sales + w_lines
if total == 100:
    st.success(f"Total: {total}% — valid")
else:
    st.error(f"Total: {total}% — must equal exactly 100%")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: SAVE
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("9. Save configuration")

# Validation checks
issues = []
if not st.session_state.get("country_name"):
    issues.append("Search and confirm a country first.")
if not final_bbox:
    issues.append("Add at least one city or region.")
if total != 100:
    issues.append("Fix scoring weights to equal 100% in Step 7.")
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
            "route_year":              int(route_year),
            "route_month1":            int(route_month1),
            "regions":                 [e["name"] for e in st.session_state["region_entries"]],
            "cities":                  [e["name"] for e in st.session_state["city_entries"]],
            "city":                    final_scope,
            "lat_min":                 lat_min,
            "lat_max":                 lat_max,
            "lng_min":                 lng_min,
            "lng_max":                 lng_max,
            "rep_count":               int(rep_count),
            "rep_mode":                rep_mode_key,
            "daily_minutes":           int(daily_minutes) if rep_mode_key == "recommended" else 480,
            "break_minutes":           int(break_minutes) if rep_mode_key == "recommended" else 30,
            "working_days":            int(working_days)  if rep_mode_key == "recommended" else 22,
            "avg_speed_kmh":           int(avg_speed_kmh) if rep_mode_key == "recommended" else 30,
            "categories":              final_categories,
            "market_api_key":          market_api_key,
            "detected_from_portfolio": detected_categories,
            "visit_benchmarks":          visit_benchmarks,
            "size_percentiles":           admin_defaults,
            "weights": {
                "rating":     w_rating    / 100,
                "reviews":    w_reviews   / 100,
                "affluence":  w_affluence / 100,
                "poi":        w_poi       / 100,
                "sales":      w_sales     / 100,
                "lines":      w_lines     / 100,
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
