import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Configure - Coverage Tool", page_icon=" ", layout="wide")

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

st.html("""
<div class="page-header">
    <h1>  Configure Market</h1>
    <p>Set up market location, scoring weights and pipeline parameters</p>
</div>
""")

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
    """Extract bounding box from a geocoding result.
    Uses viewport if available. Applies minimum buffer based on place type
    so governorates/states get a larger area than individual cities."""
    types  = result.get("types", [])
    # Determine minimum buffer in degrees based on place type
    # governorate/state/region → ~50km buffer (0.45°), city → ~15km (0.13°), town → ~8km (0.07°)
    if any(t in types for t in ["administrative_area_level_1","administrative_area_level_2","sublocality"]):
        min_buf = 0.45  # ~50km — governorate / state
    elif any(t in types for t in ["locality","postal_town"]):
        min_buf = 0.13  # ~15km — city
    else:
        min_buf = 0.25  # ~28km — unknown / be generous

    vp = result.get("geometry", {}).get("viewport", {})
    sw = vp.get("southwest", {})
    ne = vp.get("northeast", {})
    loc = result.get("geometry", {}).get("location", {})

    if sw and ne:
        lat_min = sw["lat"]; lat_max = ne["lat"]
        lng_min = sw["lng"]; lng_max = ne["lng"]
        # Ensure minimum size
        lat_span = lat_max - lat_min
        lng_span = lng_max - lng_min
        if lat_span < min_buf * 2:
            mid_lat  = (lat_min + lat_max) / 2
            lat_min  = mid_lat - min_buf
            lat_max  = mid_lat + min_buf
        if lng_span < min_buf * 2:
            mid_lng  = (lng_min + lng_max) / 2
            lng_min  = mid_lng - min_buf



            lng_max  = mid_lng + min_buf
        return (round(lat_min,4), round(lat_max,4), round(lng_min,4), round(lng_max,4))

    # Fallback to location point with buffer
    if loc:
        lat, lng = loc["lat"], loc["lng"]
        return (round(lat-min_buf,4), round(lat+min_buf,4),
                round(lng-min_buf,4), round(lng+min_buf,4))
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



st.subheader("1. Upload your Current Coverage CSV")
st.markdown("""
Required columns: `store_name`, `address`, `city`
Optional columns: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`

The app reads the `category` column and automatically sets the scraping categories to match.
""")

uploaded = st.file_uploader("Upload Current Coverage CSV", type=["csv"], key="config_upload")
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
                    st.info(f"Current Coverage categories: **{', '.join(detected_categories)}**  →  Will scrape: **{', '.join(google_categories)}**")
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
<strong>  Template column guide</strong><br><br>
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
st.download_button("  Download current_coverage_template", sample.to_csv(index=False), "current_coverage_template.csv", "text/csv")

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
                st.write(f"  {entry['name']}")
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
                r     = results[0]
                bbox  = extract_bbox(r)
                name  = r.get("formatted_address", city_input).split(",")[0].strip()
                types = r.get("types", [])
                # Warn user if Google returned a very different place type
                type_label = ""
                if "administrative_area_level_1" in types: type_label = "State/Province"
                elif "administrative_area_level_2" in types: type_label = "Governorate/County"
                elif "locality" in types: type_label = "City"
                elif "postal_town" in types: type_label = "Town"
                elif "country" in types: type_label = "  Country (too broad — try a more specific name)"
                full_name = r.get("formatted_address", city_input)
                existing_names = [e["name"] for e in st.session_state["city_entries"]]
                if name in existing_names:
                    st.warning(f"{name} is already added.")
                else:
                    st.session_state["city_entries"].append({"name": name, "bbox": bbox})
                    if type_label:
                        st.info(f"Found: **{full_name}** ({type_label})")
                    st.rerun()
            else:
                st.error(
                    f"Could not find '{city_input}' in {country_name}. "
                    f"Try adding the full name — e.g. 'Al Kamil wal Wafi Governorate' or "
                    f"'Al Kamil, South Al Batinah' — or search at region level instead."
                )

    # Show added cities



    if st.session_state["city_entries"]:
        st.markdown("**Added cities:**")
        for i, entry in enumerate(st.session_state["city_entries"]):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                st.write(f"  {entry['name']}")
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
st.info(
    "  **Route plan period is set automatically** by the lowest visit frequency across your tiers. "
    "Example: if Small = 0.5 visits/month → 2-month plan (Month 1 + Month 2). "
    "If Small = 0.33 → 3-month plan. Routes use Month 1, Month 2 etc — no fixed calendar dates."
)

st.markdown("---")
st.subheader("5a. Route plan start month")
st.caption("The plan period length is set automatically by the lowest visit frequency. Select which month the plan starts from.")

import datetime as _dt
_today = _dt.date.today()
_col_m, _col_y = st.columns(2)
with _col_m:
    route_month = st.selectbox(
        "Start month",
        options=list(range(1, 13)),
        index=_today.month - 1,
        format_func=lambda m: _dt.date(2025, m, 1).strftime("%B"),
        key="route_month_sel"
    )
with _col_y:
    route_year = st.number_input(
        "Start year",
        min_value=2024, max_value=2030,
        value=_today.year,
        key="route_year_sel"
    )

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
    hc0,hc1,hc2,hc3,hc4,hc5,hc6 = st.columns([2,1,1,1,1,1,1])
    hc0.markdown("**Sub-channel**")
    hc1.markdown("**Large visits/mo**")
    hc2.markdown("**Large duration**")
    hc3.markdown("**Medium visits/mo**")
    hc4.markdown("**Medium duration**")
    hc5.markdown("**Small visits/mo**")
    hc6.markdown("**Small duration**")
    st.caption("Use decimals for less-than-monthly: 0.5 = every 2 months · 0.33 = every 3 months · 0.25 = quarterly")

    _all_min_freq = []
    for cat in final_categories:
        cat_label = cat.replace("_"," ").title()
        c0,c1,c2,c3,c4,c5,c6 = st.columns([2,1,1,1,1,1,1])
        with c0:
            st.markdown(f"<div style='padding-top:8px;font-weight:600'>{cat_label}</div>", unsafe_allow_html=True)
        with c1:
            lv = st.number_input("", min_value=0.1, max_value=20.0, step=0.01,
                value=float(admin_defaults.get("large_visits",4)), key=f"lv_{cat}", label_visibility="collapsed")
        with c2:
            ld = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults.get("large_duration",40), key=f"ld_{cat}", label_visibility="collapsed")
        with c3:
            mv = st.number_input("", min_value=0.1, max_value=20.0, step=0.01,
                value=float(admin_defaults.get("medium_visits",2)), key=f"mv_{cat}", label_visibility="collapsed")
        with c4:
            md = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults.get("medium_duration",25), key=f"md_{cat}", label_visibility="collapsed")
        with c5:
            sv = st.number_input("", min_value=0.1, max_value=20.0, step=0.01,
                value=float(admin_defaults.get("small_visits",1)), key=f"sv_{cat}", label_visibility="collapsed")
        with c6:
            sd = st.number_input("", min_value=5, max_value=120,
                value=admin_defaults.get("small_duration",15), key=f"sd_{cat}", label_visibility="collapsed")
        visit_benchmarks[cat] = {
            "large_visits": lv, "large_duration": int(ld),
            "medium_visits": mv, "medium_duration": int(md),
            "small_visits": sv, "small_duration": int(sd),
        }



        _all_min_freq.append(min(lv, mv, sv))

    # Calculate and display plan period from minimum frequency
    if _all_min_freq:
        min_freq    = min(_all_min_freq)
        plan_period = max(1, round(1 / min_freq)) if min_freq < 1 else 1
        month_labels = [f"Month {i+1}" for i in range(plan_period)]
        st.info(
            f"  **Plan period: {plan_period} month{'s' if plan_period > 1 else ''}** "
            f"({' + '.join(month_labels)}) — "
            f"driven by minimum frequency {min_freq}/month across tiers"
        )
else:
    st.info("Select scraping categories first (Step 6).")
    visit_benchmarks = {}

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8: SALES FORCE STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("8. Sales force structure")
st.caption(
    "Define dedicated reps for specific accounts, channels, or store groups. "
    "Stores not matched by any rule are automatically assigned to mixed geographic reps."
)

# Initialise rules in session state
if "sf_rules" not in st.session_state:
    st.session_state["sf_rules"] = []

_sf_rules = st.session_state["sf_rules"]

# ── Auto-detect matchable columns + their unique values from portfolio ──────
_portfolio_for_rules = st.session_state.get("portfolio_df")
_STANDARD_COLS = {
    "store_id", "store_name", "address", "city", "lat", "lng",
    "annual_sales_usd", "lines_per_store", "category",
    "district", "area", "neighbourhood", "neighborhood", "bairro",
    "zone", "suburb", "quarter", "region", "state", "governorate",
    "province", "county", "wilaya", "emirate", "prefecture",
}

# Build "Match on" options: portfolio columns with their unique values
_match_options = {}  # display_name → {"column": col_name, "values": [unique_vals]}

# Always available: Store Name keyword (free text)
_match_options["Store name keyword"] = {"column": "store_name", "values": []}
# Always available: Scraping category
_match_options["Category"] = {"column": "category", "values": list(final_categories) if final_categories else []}

if _portfolio_for_rules is not None:
    _extra_cols = [c for c in _portfolio_for_rules.columns if c not in _STANDARD_COLS]
    for _col in _extra_cols:
        _display = _col.replace("_", " ").title()
        _unique_vals = sorted(
            _portfolio_for_rules[_col].dropna().astype(str).str.strip()
            .loc[lambda x: x != ""].unique().tolist()
        )
        if _unique_vals:  # only show columns that have data
            _match_options[_display] = {"column": _col, "values": _unique_vals}

# Collect city names for geography filter
_configured_cities = sorted(set(
    [e.get("name","") for e in st.session_state.get("city_entries", [])] +
    [e.get("name","") for e in st.session_state.get("region_entries", [])]
))
_configured_cities = [c for c in _configured_cities if c]
_geo_options = ["All"] + _configured_cities

# ── Display existing rules ──────────────────────────────────────────────────
if _sf_rules:
    st.markdown("**Current rules:**")
    for idx, rule in enumerate(_sf_rules):
        _geo_display = ", ".join(rule.get("geography", ["All"]))
        _match_on    = rule.get("match_field", "")
        _match_val   = rule.get("match_value", "")
        st.markdown(
            f'<div style="background:#F8F9FA;border:1px solid #E0E0E0;border-left:4px solid #1565C0;'
            f'border-radius:8px;padding:0.7rem 1rem;margin:0.4rem 0;font-size:0.88rem">'
            f'<strong>{rule.get("rule_name","")}</strong> — '
            f'{_match_on}: "<em>{_match_val}</em>" — '
            f'Geography: {_geo_display} — '
            f'<strong>{rule.get("dedicated_reps",1)} dedicated rep(s)</strong>'
            f'</div>',
            unsafe_allow_html=True
        )

    # Remove rule buttons
    _del_cols = st.columns(min(len(_sf_rules), 5))
    for idx, rule in enumerate(_sf_rules):
        with _del_cols[idx % 5]:
            if st.button(f"Remove: {rule.get('rule_name','')}", key=f"del_rule_{idx}"):
                _sf_rules.pop(idx)
                st.session_state["sf_rules"] = _sf_rules
                st.rerun()

    st.markdown("---")

# ── Add new rule form ────────────────────────────────────────────────────────
with st.expander("Add a dedicated rep rule", expanded=len(_sf_rules) == 0):
    st.caption(
        "Select what to match on — if your portfolio has columns like Account or Channel, "
        "their values will appear automatically. Matching is always flexible: "
        "typing \"Lulu\" will match \"Lulu Hypermarket\", \"lulu express\", \"LULU\" etc."
    )

    _ar1, _ar2 = st.columns(2)
    with _ar1:
        _new_rule_name = st.text_input(
            "Rule name", placeholder="e.g., Lulu Exclusive",
            key="new_rule_name"
        )
    with _ar2:
        _match_on_options = list(_match_options.keys())
        _new_match_on = st.selectbox(
            "Match on", _match_on_options, key="new_match_on",
            help="Select which field to match stores on. Portfolio columns like Account, Channel are auto-detected."
        )

    _ar3, _ar4, _ar5 = st.columns(3)

    # Get the values for the selected match field
    _selected_opt = _match_options.get(_new_match_on, {})
    _available_values = _selected_opt.get("values", [])

    with _ar3:
        if _available_values:
            # Show dropdown of actual values from the data
            _new_match_value = st.selectbox(
                "Select value", _available_values,
                key="new_match_value_select",
                help="Values detected from your uploaded portfolio."
            )
        else:
            # Free text input (for Store name keyword or empty columns)
            _new_match_value = st.text_input(
                "Enter keyword", placeholder="e.g., Lulu",
                key="new_match_value_text",
                help="Type a keyword — matching is flexible (case-insensitive, partial match)."
            )
    with _ar4:
        _new_geography = st.multiselect(
            "Geography", _geo_options, default=["All"],
            key="new_geography",
            help="Where does this rule apply? Select 'All' for everywhere."
        )
    with _ar5:
        _new_dedicated_reps = st.number_input(
            "Dedicated reps", min_value=1, max_value=50, value=1,
            key="new_dedicated_reps",
            help="How many reps for this group. System auto-adjusts if stores exceed capacity."
        )

    if st.button("Add rule", type="primary", key="btn_add_rule"):
        if not _new_rule_name.strip():
            st.error("Please enter a rule name.")
        elif not str(_new_match_value).strip():
            st.error("Please select or enter a match value.")
        else:
            _match_col = _selected_opt.get("column", "store_name")
            # Determine rule type: channel-like columns get higher priority
            _channel_cols = {"channel", "trade_channel", "sub_channel", "trade_type", "segment", "category"}
            _rule_type = "Channel" if _match_col in _channel_cols else "Customer"

            _new_rule = {
                "rule_name":      _new_rule_name.strip(),
                "rule_type":      _rule_type,
                "match_field":    _new_match_on,
                "match_column":   _match_col,
                "match_type":     "Contains",  # always flexible matching
                "match_value":    str(_new_match_value).strip(),
                "geography":      _new_geography if "All" not in _new_geography else ["All"],
                "dedicated_reps": _new_dedicated_reps,
            }
            _sf_rules.append(_new_rule)
            # Auto-sort: Channel rules first, then Customer
            _sf_rules.sort(key=lambda r: 0 if r.get("rule_type") == "Channel" else 1)
            st.session_state["sf_rules"] = _sf_rules
            st.success(f"Rule added: {_new_rule_name}")
            st.warning("  **Remember to click 'Save market configuration' below** for rules to take effect in the pipeline.")
            st.rerun()

# ── Numeric distribution % (recommended mode only) ──────────────────────────
if rep_mode_key == "recommended":
    st.markdown("---")
    st.markdown("**Numeric distribution cutoff**")
    st.caption(
        "In recommended mode, only the top N% of stores (by combined score ranking) "
        "are included in routing. A higher % means more stores routed and more reps needed. "
        "Lower % focuses reps on only the highest-value stores."
    )
    _store_select_pct = st.slider(
        "Store selection % for routing",
        min_value=10, max_value=100, value=60, step=5,
        key="store_select_pct_input",
        help="Top N% of stores by normalised score. Default 60%."
    )
else:
    _store_select_pct = 100  # fixed mode routes all stores

# ── Summary ─────────────────────────────────────────────────────────────────
_n_dedicated = sum(r.get("dedicated_reps", 1) for r in _sf_rules)
if _sf_rules:
    _mixed_label = ""
    if rep_mode_key == "fixed":
        _mixed_reps = max(0, int(rep_count) - _n_dedicated)
        _mixed_label = f" · **{_mixed_reps} mixed reps** remaining"
        if _mixed_reps <= 0:
            st.error(
                f"Dedicated rules require {_n_dedicated} reps but you only have {int(rep_count)} total. "
                "Increase total reps or reduce dedicated rules."
            )
        elif _mixed_reps < 2:
            st.warning(
                f"Only {_mixed_reps} rep(s) left for mixed stores. Consider increasing total reps."
            )
    st.info(
        f"**{len(_sf_rules)} rule(s)** · {_n_dedicated} dedicated rep(s)"
        f"{_mixed_label}"
        + (f" · Top **{_store_select_pct}%** of stores selected for routing" if rep_mode_key == "recommended" else "")
    )

total = 100  # weights managed in Admin Settings
# ─────────────────────────────────────────────────────────────────────────────
# STEP 9: SAVE
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("9. Save configuration")

# Validation checks
issues = []
if not st.session_state.get("country_name"):
    issues.append("Search and confirm a country first.")
if not final_bbox:
    issues.append("Add at least one city or region.")
if total != 100:
    pass  # weights managed in Admin Settings
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
            "country_name":            st.session_state.get("country_name",""),
            "lat_min":                 lat_min,
            "lat_max":                 lat_max,
            "lng_min":                 lng_min,
            "lng_max":                 lng_max,
            "rep_count":               int(rep_count),
            "rep_mode":                rep_mode_key,
            "daily_minutes":           int(daily_minutes),
            "break_minutes":           int(break_minutes),
            "working_days":            int(working_days),
            "avg_speed_kmh":           int(avg_speed_kmh),
            "categories":              final_categories,
            "market_api_key":          market_api_key,
            "detected_from_portfolio": detected_categories,
            "visit_benchmarks":          visit_benchmarks,
            "plan_period":             max(1, round(1/min(min(v.get("large_visits",4), v.get("medium_visits",2), v.get("small_visits",1)) for v in visit_benchmarks.values())) if visit_benchmarks else 1),
            "size_percentiles":           admin_defaults,
            "route_month": int(route_month),
            "route_year":  int(route_year),
            "weights": {k: v/100 for k,v in st.session_state.get("admin_scoring_weights",
                {"rating":20,"reviews":25,"affluence":15,"poi":15,"sales":15,"lines":10}).items()},
            "weights_gap": {k: v/100 for k,v in st.session_state.get("admin_scoring_weights_gap",
                {"rating":25,"reviews":25,"affluence":25,"poi":25}).items()},
            "sf_rules":                st.session_state.get("sf_rules", []),
            "store_select_pct":        _store_select_pct,
        }
        st.markdown(f"""
        <div style="background:#E8F5E9;border:1.5px solid #66BB6A;border-left:5px solid #2E7D32;
        border-radius:8px;padding:1rem 1.4rem;margin:0.5rem 0">
            <div style="font-weight:700;color:#1B5E20;font-size:1rem;margin-bottom:4px">
                 Configuration saved — {market_name}
            </div>
            <div style="color:#2E7D32;font-size:0.87rem">
                Market area, scoring weights, categories and frequency thresholds have been saved.
                Go to <strong>Run Pipeline</strong> in the sidebar to upload your Current Coverage CSV and start the pipeline.
            </div>
        </div>
        """, unsafe_allow_html=True)

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
