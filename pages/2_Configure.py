import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Configure - Coverage Tool", page_icon="⚙️", layout="wide")
st.title("Configure Market")

LOCATIONS = {
    "United Arab Emirates": {
        "Dubai": {
            "Dubai City":        (25.10, 25.30, 55.20, 55.40),
            "Deira":             (25.25, 25.32, 55.28, 55.38),
            "Marina":            (25.07, 25.13, 55.12, 55.18),
            "Business Bay":      (25.17, 25.22, 55.27, 55.33),
            "Jumeirah":          (25.19, 25.24, 55.22, 55.28),
            "Al Barsha":         (25.10, 25.14, 55.18, 55.23),
            "Downtown Dubai":    (25.18, 25.21, 55.27, 55.30),
            "Al Quoz":           (25.14, 25.18, 55.21, 55.26),
        },
        "Abu Dhabi": {
            "Abu Dhabi City":    (24.40, 24.55, 54.30, 54.55),
            "Al Reem Island":    (24.49, 24.53, 54.38, 54.43),
            "Khalidiyah":        (24.47, 24.50, 54.34, 54.38),
            "Musaffah":          (24.34, 24.40, 54.47, 54.55),
        },
        "Sharjah": {
            "Sharjah City":      (25.32, 25.42, 55.37, 55.47),
            "Al Nahda":          (25.30, 25.34, 55.39, 55.43),
        },
        "Ajman": {
            "Ajman City":        (25.39, 25.44, 55.43, 55.50),
        },
        "Ras Al Khaimah": {
            "RAK City":          (25.77, 25.83, 55.93, 56.02),
        },
    },
    "Saudi Arabia": {
        "Riyadh": {
            "Riyadh City":       (24.55, 24.85, 46.55, 46.85),
            "Al Olaya":          (24.68, 24.73, 46.67, 46.73),
            "Al Malaz":          (24.66, 24.71, 46.74, 46.80),
            "Diplomatic Quarter":(24.70, 24.74, 46.60, 46.65),
        },
        "Jeddah": {
            "Jeddah City":       (21.40, 21.65, 39.10, 39.30),
            "Al Hamra":          (21.53, 21.58, 39.13, 39.18),
            "Al Balad":          (21.48, 21.52, 39.18, 39.22),
        },
        "Dammam": {
            "Dammam City":       (26.38, 26.48, 49.97, 50.12),
            "Al Khobar":         (26.26, 26.32, 50.19, 50.25),
            "Dhahran":           (26.27, 26.32, 50.10, 50.16),
        },
        "Mecca": {
            "Mecca City":        (21.37, 21.45, 39.81, 39.89),
        },
        "Medina": {
            "Medina City":       (24.44, 24.52, 39.57, 39.65),
        },
    },
    "Kuwait": {
        "Kuwait City": {
            "Kuwait City Centre": (29.34, 29.40, 47.95, 48.02),
            "Salmiya":            (29.32, 29.36, 48.07, 48.12),
            "Hawalli":            (29.32, 29.36, 48.01, 48.07),
            "Farwaniya":          (29.27, 29.33, 47.95, 48.01),
        },
    },
    "Qatar": {
        "Doha": {
            "Doha City":         (25.24, 25.35, 51.49, 51.58),
            "West Bay":          (25.32, 25.36, 51.52, 51.56),
            "Al Sadd":           (25.27, 25.30, 51.50, 51.54),
            "The Pearl":         (25.36, 25.39, 51.54, 51.57),
        },
    },
    "Bahrain": {
        "Manama": {
            "Manama City":       (26.20, 26.25, 50.57, 50.62),
            "Seef":              (26.22, 26.25, 50.54, 50.58),
            "Adliya":            (26.21, 26.23, 50.59, 50.62),
        },
    },
    "Egypt": {
        "Cairo": {
            "Cairo City":        (30.00, 30.12, 31.20, 31.35),
            "Heliopolis":        (30.08, 30.12, 31.32, 31.37),
            "Maadi":             (29.95, 29.99, 31.25, 31.29),
            "Zamalek":           (30.05, 30.07, 31.21, 31.23),
            "New Cairo":         (30.00, 30.06, 31.40, 31.50),
        },
        "Alexandria": {
            "Alexandria City":   (31.17, 31.25, 29.90, 30.05),
        },
        "Giza": {
            "Giza City":         (29.98, 30.05, 31.10, 31.22),
        },
    },
    "United Kingdom": {
        "London": {
            "Greater London":    (51.38, 51.62, -0.28,  0.08),
            "Central London":    (51.48, 51.52, -0.18, -0.05),
            "East London":       (51.50, 51.55, -0.05,  0.08),
            "West London":       (51.48, 51.53, -0.28, -0.18),
            "North London":      (51.54, 51.60, -0.15,  0.00),
            "South London":      (51.43, 51.48, -0.15,  0.05),
        },
        "Manchester": {
            "Manchester City":   (53.44, 53.52, -2.28, -2.17),
            "Salford":           (53.47, 53.51, -2.30, -2.24),
        },
        "Birmingham": {
            "Birmingham City":   (52.43, 52.52, -1.98, -1.82),
        },
        "Leeds": {
            "Leeds City":        (53.78, 53.84, -1.60, -1.52),
        },
        "Glasgow": {
            "Glasgow City":      (55.83, 55.88, -4.31, -4.22),
        },
    },
    "South Africa": {
        "Gauteng": {
            "Johannesburg":      (-26.30, -26.00, 27.90, 28.20),
            "Sandton":           (-26.12, -26.08, 28.04, 28.09),
            "Pretoria":          (-25.78, -25.70, 28.17, 28.26),
            "Soweto":            (-26.28, -26.22, 27.84, 27.93),
        },
        "Western Cape": {
            "Cape Town":         (-33.98, -33.85, 18.40, 18.58),
            "Stellenbosch":      (-33.96, -33.92, 18.84, 18.88),
        },
        "KwaZulu-Natal": {
            "Durban":            (-29.92, -29.82, 30.98, 31.08),
        },
    },
    "Nigeria": {
        "Lagos": {
            "Lagos Island":      (6.42, 6.47, 3.38, 3.44),
            "Victoria Island":   (6.42, 6.45, 3.41, 3.45),
            "Lekki":             (6.43, 6.47, 3.47, 3.58),
            "Ikeja":             (6.58, 6.62, 3.33, 3.37),
        },
        "Abuja": {
            "Abuja City":        (9.02, 9.10, 7.44, 7.52),
            "Wuse":              (9.06, 9.09, 7.46, 7.50),
        },
    },
    "Kenya": {
        "Nairobi": {
            "Nairobi City":      (-1.32, -1.24, 36.78, 36.88),
            "Westlands":         (-1.27, -1.24, 36.80, 36.83),
            "Karen":             (-1.35, -1.31, 36.68, 36.73),
        },
    },
    "Philippines": {
        "NCR": {
            "Manila":            (14.50, 14.70, 120.95, 121.15),
            "Makati":            (14.54, 14.57, 121.01, 121.04),
            "BGC":               (14.54, 14.56, 121.04, 121.06),
            "Quezon City":       (14.62, 14.73, 121.02, 121.10),
        },
        "Cebu": {
            "Cebu City":         (10.28, 10.36, 123.87, 123.93),
        },
        "Davao": {
            "Davao City":        (7.05, 7.13, 125.58, 125.65),
        },
    },
    "Indonesia": {
        "Jakarta": {
            "Central Jakarta":   (-6.20, -6.15, 106.82, 106.87),
            "South Jakarta":     (-6.30, -6.22, 106.78, 106.86),
            "North Jakarta":     (-6.15, -6.10, 106.83, 106.90),
        },
        "Surabaya": {
            "Surabaya City":     (-7.30, -7.22, 112.70, 112.78),
        },
    },
}

CATEGORY_MAP = {
    "supermarket":"supermarket","hypermarket":"supermarket",
    "convenience store":"convenience_store","convenience_store":"convenience_store",
    "minimarket":"convenience_store","mini market":"convenience_store",
    "pharmacy":"pharmacy","chemist":"pharmacy","drugstore":"pharmacy",
    "gas station":"gas_station","petrol station":"gas_station","gas_station":"gas_station",
    "off licence":"liquor_store","liquor store":"liquor_store","liquor_store":"liquor_store",
    "grocery":"grocery_or_supermarket","grocery store":"grocery_or_supermarket",
    "grocery_or_supermarket":"grocery_or_supermarket",
    "dollar store":"convenience_store","variety store":"convenience_store","newsagent":"convenience_store",
}
TIER_LABELS   = {1:"Tier 1 - 100% fit",2:"Tier 2 - 80% fit",3:"Tier 3 - 55% fit",4:"Tier 4 - 30% fit"}
TIER_DEFAULTS = {"supermarket":1,"hypermarket":1,"convenience_store":1,"grocery_or_supermarket":1,"pharmacy":2,"gas_station":2,"liquor_store":2}

def merge_bboxes(boxes):
    return min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes)

def geocode_city(city_name, country_name, api_key):
    try:
        r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": f"{city_name}, {country_name}", "key": api_key}, timeout=10)
        data = r.json()
        if data.get("status") == "OK":
            vp = data["results"][0].get("geometry", {}).get("viewport", {})
            sw = vp.get("southwest", {})
            ne = vp.get("northeast", {})
            if sw and ne:
                return (round(sw["lat"],4), round(ne["lat"],4), round(sw["lng"],4), round(ne["lng"],4))
    except Exception:
        pass
    return None

# ── STEP 1: PORTFOLIO ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("1. Upload your portfolio CSV")
st.markdown("Required: `store_name`, `address`, `city` | Optional: `store_id`, `category`, `annual_sales_usd`, `lines_per_store`")

uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"], key="config_upload")
portfolio_df = None
detected_categories = []
google_categories = []

if uploaded:
    try:
        portfolio_df = pd.read_csv(uploaded)
        portfolio_df.columns = [c.strip().lower().replace(" ","_") for c in portfolio_df.columns]
        missing = [c for c in ["store_name","address","city"] if c not in portfolio_df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
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
            if "category" in portfolio_df.columns:
                raw_cats = portfolio_df["category"].dropna().str.lower().str.strip().unique().tolist()
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
                    st.info(f"Portfolio categories: **{', '.join(detected_categories)}** — Will scrape: **{', '.join(google_categories)}**")
                else:
                    st.warning("Could not match categories automatically. Select them manually below.")
            else:
                st.warning("No category column found. Select scraping categories manually below.")
            st.session_state["portfolio_df"] = portfolio_df
    except Exception as e:
        st.error(f"Error: {e}")

sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Road","city":"Dubai","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Spinneys JBR","address":"Marina Walk","city":"Dubai","category":"supermarket","annual_sales_usd":87000,"lines_per_store":42},
    {"store_id":"S003","store_name":"Boots Pharmacy","address":"Business Bay","city":"Dubai","category":"pharmacy","annual_sales_usd":22000,"lines_per_store":12},
    {"store_id":"S004","store_name":"ENOC Station","address":"Al Barsha","city":"Dubai","category":"gas station","annual_sales_usd":18000,"lines_per_store":8},
])
st.download_button("Download sample CSV template", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")

# ── STEP 2: LOCATION ──────────────────────────────────────────────────────────
st.subheader("2. Select market location")
st.caption("Select country, then one or more regions, then one or more cities. Coverage area is calculated automatically.")

country = st.selectbox("Country", list(LOCATIONS.keys()))
all_regions = list(LOCATIONS[country].keys())

st.markdown(" ")
col_r1, col_r2 = st.columns([4, 1])
with col_r1:
    selected_regions = st.multiselect(
        "Region / State — select one or more",
        options=all_regions,
        default=[all_regions[0]],
        key="region_ms"
    )
with col_r2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("All regions"):
        st.session_state["region_ms"] = all_regions
        st.rerun()

if not selected_regions:
    st.warning("Select at least one region.")
    st.stop()

all_cities = {}
for reg in selected_regions:
    for city, bbox in LOCATIONS[country][reg].items():
        all_cities[city] = bbox
city_options = list(all_cities.keys())

col_c1, col_c2 = st.columns([4, 1])
with col_c1:
    selected_cities = st.multiselect(
        "City / Area — select one or more",
        options=city_options,
        default=[city_options[0]],
        key="city_ms"
    )
with col_c2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("All cities"):
        st.session_state["city_ms"] = city_options
        st.rerun()

if not selected_cities:
    st.warning("Select at least one city.")
    st.stop()

selected_boxes = [all_cities[c] for c in selected_cities]
lat_min, lat_max, lng_min, lng_max = merge_bboxes(selected_boxes)
market_display = ", ".join(selected_cities)
st.success(f"Coverage area: **{market_display}**")

st.markdown(" ")
with st.expander("My city is not listed — search for it"):
    st.markdown("Type your city and the agent will find the correct coordinates using Google Geocoding.")
    col1, col2 = st.columns([3, 1])
    with col1:
        custom_city_input = st.text_input("City name", placeholder="e.g. Casablanca")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", type="secondary"):
            try:
                api_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
            except Exception:
                api_key = ""
            if not api_key:
                st.error("Google API key not set. Ask admin to set GOOGLE_MAPS_API_KEY in Secrets.")
            elif not custom_city_input:
                st.warning("Enter a city name first.")
            else:
                with st.spinner(f"Searching for {custom_city_input}..."):
                    bbox = geocode_city(custom_city_input, country, api_key)
                if bbox:
                    st.session_state["custom_city"] = {"name": custom_city_input, "bbox": bbox}
                    st.success(f"Found {custom_city_input}. Coordinates set automatically.")
                    st.rerun()
                else:
                    st.error(f"Could not find {custom_city_input}. Check spelling or try adding the country name.")

if st.session_state.get("custom_city"):
    cc = st.session_state["custom_city"]
    lat_min, lat_max, lng_min, lng_max = cc["bbox"]
    market_display = cc["name"]
    st.info(f"Using custom city: **{cc['name']}**")
    if st.button("Clear custom city"):
        st.session_state["custom_city"] = None
        st.rerun()

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    market_name = st.text_input("Market name", value=f"{country} - {market_display}")
with col2:
    rep_count = st.number_input("Number of field reps", min_value=1, max_value=100, value=6)
with col3:
    market_api_key = st.text_input("Market-specific Google API key (optional)", type="password", placeholder="Leave blank to use global admin key")

st.markdown("---")

# ── STEP 3: CATEGORIES ────────────────────────────────────────────────────────
st.subheader("3. Scraping categories")
if google_categories:
    st.success(f"Auto-detected from portfolio — scraping: **{', '.join(google_categories)}**")
    extra = st.multiselect("Add extra categories (optional)",
        options=[c for c in ["supermarket","convenience_store","pharmacy","gas_station","liquor_store","grocery_or_supermarket","hypermarket"] if c not in google_categories],
        default=[])
    final_categories = google_categories + extra
else:
    final_categories = st.multiselect("Select categories to scrape",
        options=["supermarket","convenience_store","pharmacy","gas_station","liquor_store","grocery_or_supermarket","hypermarket","dollar_store","variety_store"],
        default=["supermarket","convenience_store","pharmacy","gas_station"])

st.markdown("---")

# ── STEP 4: TIERS ─────────────────────────────────────────────────────────────
st.subheader("4. Category tier multipliers")
st.caption("Tier 1 = highest FMCG relevance (1.0 multiplier). Tier 4 = lowest (0.30).")
cat_tiers = {}
if final_categories:
    cols = st.columns(2)
    for i, cat in enumerate(final_categories):
        with cols[i % 2]:
            cat_tiers[cat] = st.selectbox(
                cat.replace("_"," ").title(), options=[1,2,3,4],
                index=TIER_DEFAULTS.get(cat,2)-1,
                format_func=lambda x: TIER_LABELS[x], key=f"tier_{cat}")

st.markdown("---")

# ── STEP 5: WEIGHTS ───────────────────────────────────────────────────────────
st.subheader("5. Scoring weights — must sum to 100%")
st.caption("Each store gets a score 0-100. Gap stores score 0 on sales and lines — their upside is what you are discovering.")
col1, col2 = st.columns(2)
with col1:
    w_rating   = st.slider("Rating — Google star rating",    0, 50, 20)
    w_reviews  = st.slider("Reviews / footfall",             0, 50, 25)
    w_category = st.slider("Category fit",                   0, 50, 20)
with col2:
    w_sales    = st.slider("Current sales",                  0, 50, 20)
    w_lines    = st.slider("Lines per store",                0, 50, 15)
total = w_rating + w_reviews + w_category + w_sales + w_lines
if total == 100:
    st.success(f"Total: {total}% — valid")
else:
    st.error(f"Total: {total}% — must equal exactly 100%")

st.markdown("---")

# ── STEP 6: FREQUENCY ─────────────────────────────────────────────────────────
st.subheader("6. Visit frequency thresholds")
col1, col2, col3, col4 = st.columns(4)
with col1:
    f_weekly      = st.number_input("Weekly (score >=)",      min_value=1, max_value=99, value=80)
    st.caption("4 calls per month")
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

# ── STEP 7: SAVE ──────────────────────────────────────────────────────────────
st.subheader("7. Save configuration")
if total != 100:
    st.warning("Fix weights to equal 100% before saving.")
elif not final_categories:
    st.warning("Select at least one category.")
else:
    if st.button("Save market configuration", type="primary"):
        st.session_state["market_config"] = {
            "market_name":             market_name,
            "country":                 country,
            "regions":                 selected_regions,
            "cities":                  selected_cities,
            "city":                    market_display,
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
        st.success(f"Configuration saved for **{market_name}**. Go to Run Pipeline in the sidebar.")
        st.balloons()

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
