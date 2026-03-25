import streamlit as st
import pandas as pd

st.set_page_config(page_title="Configure - Coverage Tool", page_icon="⚙️", layout="wide")
st.title("Configure Market")

# ── LOCATION DATA ─────────────────────────────────────────────────────────────
# Country → Region → City → bounding box
LOCATIONS = {
    "United Arab Emirates": {
        "Dubai": {
            "Dubai City":    (25.10, 25.30, 55.20, 55.40),
            "Deira":         (25.25, 25.32, 55.28, 55.38),
            "Marina":        (25.07, 25.13, 55.12, 55.18),
            "Business Bay":  (25.17, 25.22, 55.27, 55.33),
        },
        "Abu Dhabi": {
            "Abu Dhabi City": (24.40, 24.55, 54.30, 54.55),
            "Al Reem Island": (24.49, 24.53, 54.38, 54.43),
        },
        "Sharjah": {
            "Sharjah City":  (25.32, 25.42, 55.37, 55.47),
        },
    },
    "Saudi Arabia": {
        "Riyadh": {
            "Riyadh City":   (24.55, 24.85, 46.55, 46.85),
            "Al Olaya":      (24.68, 24.73, 46.67, 46.73),
            "Al Malaz":      (24.66, 24.71, 46.74, 46.80),
        },
        "Jeddah": {
            "Jeddah City":   (21.40, 21.65, 39.10, 39.30),
            "Al Hamra":      (21.53, 21.58, 39.13, 39.18),
        },
        "Dammam": {
            "Dammam City":   (26.38, 26.48, 49.97, 50.12),
        },
    },
    "United Kingdom": {
        "London": {
            "Greater London": (51.38, 51.62, -0.28, 0.08),
            "Central London": (51.48, 51.52, -0.18, -0.05),
            "East London":    (51.50, 51.55, -0.05, 0.08),
            "West London":    (51.48, 51.53, -0.28, -0.18),
        },
        "Manchester": {
            "Manchester City": (53.44, 53.52, -2.28, -2.17),
        },
        "Birmingham": {
            "Birmingham City": (52.43, 52.52, -1.98, -1.82),
        },
    },
    "South Africa": {
        "Gauteng": {
            "Johannesburg":  (-26.30, -26.00, 27.90, 28.20),
            "Sandton":       (-26.12, -26.08, 28.04, 28.09),
            "Pretoria":      (-25.78, -25.70, 28.17, 28.26),
        },
        "Western Cape": {
            "Cape Town":     (-33.98, -33.85, 18.40, 18.58),
            "Stellenbosch":  (-33.96, -33.92, 18.84, 18.88),
        },
    },
    "Philippines": {
        "NCR": {
            "Manila":        (14.50, 14.70, 120.95, 121.15),
            "Makati":        (14.54, 14.57, 121.01, 121.04),
            "BGC":           (14.54, 14.56, 121.04, 121.06),
        },
        "Cebu": {
            "Cebu City":     (10.28, 10.36, 123.87, 123.93),
        },
    },
    "Custom": {
        "Custom Region": {
            "Custom City": (0.0, 0.0, 0.0, 0.0),
        }
    }
}

# ── CATEGORY MAPPING ──────────────────────────────────────────────────────────
# Maps portfolio category names → Google Places API type
CATEGORY_MAP = {
    "supermarket":         "supermarket",
    "hypermarket":         "supermarket",
    "convenience store":   "convenience_store",
    "convenience_store":   "convenience_store",
    "pharmacy":            "pharmacy",
    "chemist":             "pharmacy",
    "drugstore":           "pharmacy",
    "gas station":         "gas_station",
    "petrol station":      "gas_station",
    "gas_station":         "gas_station",
    "off licence":         "liquor_store",
    "liquor store":        "liquor_store",
    "liquor_store":        "liquor_store",
    "grocery":             "grocery_or_supermarket",
    "grocery store":       "grocery_or_supermarket",
    "grocery_or_supermarket": "grocery_or_supermarket",
    "dollar store":        "convenience_store",
    "variety store":       "convenience_store",
    "newsagent":           "convenience_store",
    "minimarket":          "convenience_store",
    "mini market":         "convenience_store",
}

TIER_LABELS = {
    1: "Tier 1 - 100% fit",
    2: "Tier 2 - 80% fit",
    3: "Tier 3 - 55% fit",
    4: "Tier 4 - 30% fit",
}

TIER_DEFAULTS = {
    "supermarket": 1, "hypermarket": 1, "convenience_store": 1,
    "grocery_or_supermarket": 1, "pharmacy": 2, "gas_station": 2,
    "liquor_store": 2, "convenience store": 1, "petrol station": 2,
}

# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("1. Upload your portfolio CSV first")
st.markdown("""
Upload your current store portfolio. The app will **automatically detect the store categories**
in your file and use them to scrape the matching universe from Google Places.

Required columns: `store_name`, `address`, `city`
Optional columns: `store_id`, `annual_sales_usd`, `lines_per_store`, `category`
""")

uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"], key="config_upload")
portfolio_df = None
detected_categories = []
google_categories   = []

if uploaded:
    try:
        portfolio_df = pd.read_csv(uploaded)
        portfolio_df.columns = [c.strip().lower().replace(" ", "_") for c in portfolio_df.columns]
        missing = [c for c in ["store_name", "address", "city"] if c not in portfolio_df.columns]
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

            # Auto-detect categories from portfolio
            if "category" in portfolio_df.columns:
                raw_cats = portfolio_df["category"].dropna().str.lower().str.strip().unique().tolist()
                detected_categories = raw_cats
                # Map to Google Places types
                mapped = set()
                for cat in raw_cats:
                    gcat = CATEGORY_MAP.get(cat)
                    if gcat:
                        mapped.add(gcat)
                    else:
                        # try partial match
                        for key, val in CATEGORY_MAP.items():
                            if key in cat or cat in key:
                                mapped.add(val)
                                break
                google_categories = list(mapped)

                if google_categories:
                    st.info(f"Categories detected in your portfolio: **{', '.join(detected_categories)}**\n\nWill scrape Google Places for: **{', '.join(google_categories)}**")
                else:
                    st.warning("Could not auto-detect categories from your portfolio. You will select them manually below.")
            else:
                st.warning("No 'category' column found in your CSV. You will select scraping categories manually below.")

            # Save portfolio to session
            st.session_state["portfolio_df"] = portfolio_df

    except Exception as e:
        st.error(f"Error reading file: {e}")

# Sample CSV download
sample = pd.DataFrame([
    {"store_id":"S001","store_name":"Carrefour Express","address":"Sheikh Zayed Road","city":"Dubai","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
    {"store_id":"S002","store_name":"Spinneys JBR",     "address":"Marina Walk",      "city":"Dubai","category":"supermarket","annual_sales_usd":87000, "lines_per_store":42},
    {"store_id":"S003","store_name":"Boots Pharmacy",   "address":"Business Bay",     "city":"Dubai","category":"pharmacy",    "annual_sales_usd":22000, "lines_per_store":12},
    {"store_id":"S004","store_name":"ENOC Station",     "address":"Al Barsha",        "city":"Dubai","category":"gas station", "annual_sales_usd":18000, "lines_per_store":8},
])
st.download_button("Download sample CSV template", sample.to_csv(index=False), "sample_portfolio.csv", "text/csv")

st.markdown("---")

# ── LOCATION ──────────────────────────────────────────────────────────────────
st.subheader("2. Select market location")
st.caption("Select country, then region, then city. The bounding box fills automatically. You can fine-tune it manually.")

col1, col2, col3 = st.columns(3)

with col1:
    country = st.selectbox("Country", list(LOCATIONS.keys()))

with col2:
    regions = list(LOCATIONS[country].keys())
    region  = st.selectbox("Region / State", regions)

with col3:
    cities   = list(LOCATIONS[country][region].keys())
    city_sel = st.selectbox("City / Area", cities)

# Get bounding box from selection
bbox = LOCATIONS[country][region][city_sel]
lat_min_def, lat_max_def, lng_min_def, lng_max_def = bbox

# Allow custom if Custom selected or manual override
if country == "Custom" or city_sel == "Custom City":
    st.info("Enter your custom bounding box coordinates below. Find them at bboxfinder.com")

col1, col2, col3, col4 = st.columns(4)
with col1:
    lat_min = st.number_input("Lat min", value=float(lat_min_def), format="%.4f")
with col2:
    lat_max = st.number_input("Lat max", value=float(lat_max_def), format="%.4f")
with col3:
    lng_min = st.number_input("Lng min", value=float(lng_min_def), format="%.4f")
with col4:
    lng_max = st.number_input("Lng max", value=float(lng_max_def), format="%.4f")

st.caption("Fine-tune the bounding box if needed. Find coordinates at bboxfinder.com")

# Market name auto-filled
market_name = st.text_input("Market name", value=f"{country} - {region} - {city_sel}")

col1, col2 = st.columns(2)
with col1:
    rep_count = st.number_input("Number of field reps", min_value=1, max_value=100, value=6)
with col2:
    market_api_key = st.text_input(
        "Market-specific Google API key (optional)",
        type="password",
        placeholder="Leave blank to use the global key set by admin",
    )

st.markdown("---")

# ── CATEGORIES ────────────────────────────────────────────────────────────────
st.subheader("3. Scraping categories")

if google_categories:
    st.success(f"Auto-detected from your portfolio — will scrape: **{', '.join(google_categories)}**")
    st.caption("These match the categories in your uploaded CSV. You can add more below if needed.")
    extra_cats = st.multiselect(
        "Add extra categories to scrape (optional)",
        options=[c for c in ["supermarket","convenience_store","pharmacy","gas_station","liquor_store","grocery_or_supermarket","hypermarket"] if c not in google_categories],
        default=[],
    )
    final_categories = google_categories + extra_cats
else:
    st.warning("No categories auto-detected. Select manually:")
    final_categories = st.multiselect(
        "Select categories to scrape from Google Places",
        options=["supermarket","convenience_store","pharmacy","gas_station","liquor_store","grocery_or_supermarket","hypermarket","dollar_store","variety_store"],
        default=["supermarket","convenience_store","pharmacy","gas_station"],
    )

st.markdown("---")

# ── CATEGORY TIERS ────────────────────────────────────────────────────────────
st.subheader("4. Category tier multipliers")
st.caption("Tier 1 = highest FMCG fit (1.0 score multiplier). Tier 4 = lowest (0.30 multiplier).")

cat_tiers = {}
if final_categories:
    cols = st.columns(2)
    for i, cat in enumerate(final_categories):
        with cols[i % 2]:
            default_tier = TIER_DEFAULTS.get(cat, 2)
            cat_tiers[cat] = st.selectbox(
                cat.replace("_", " ").title(),
                options=[1, 2, 3, 4],
                index=default_tier - 1,
                format_func=lambda x: TIER_LABELS[x],
                key=f"tier_{cat}",
            )

st.markdown("---")

# ── SCORING WEIGHTS ───────────────────────────────────────────────────────────
st.subheader("5. Scoring weights — must sum to 100%")
st.caption("""
- Rating: how highly Google users rate the store
- Reviews / footfall: how many reviews the store has (more reviews = busier store)
- Category fit: how relevant the store type is for your FMCG products
- Current sales: how much revenue you already generate there (only for your covered stores)
- Lines per store: how many of your products the store stocks (only for your covered stores)
""")

col1, col2 = st.columns(2)
with col1:
    w_rating   = st.slider("Rating (Google 0-5 stars)",         0, 50, 20)
    w_reviews  = st.slider("Reviews / footfall (store traffic)", 0, 50, 25)
    w_category = st.slider("Category fit (store type)",         0, 50, 20)
with col2:
    w_sales    = st.slider("Current sales (your revenue there)", 0, 50, 20)
    w_lines    = st.slider("Lines per store (products stocked)", 0, 50, 15)

total = w_rating + w_reviews + w_category + w_sales + w_lines
if total == 100:
    st.success(f"Total: {total}% — valid")
else:
    st.error(f"Total: {total}% — must equal exactly 100%")

st.markdown("---")

# ── FREQUENCY THRESHOLDS ──────────────────────────────────────────────────────
st.subheader("6. Visit frequency thresholds")
st.caption("Based on the store score, the agent decides how often a rep should visit.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    f_weekly      = st.number_input("Weekly (score >=)",      min_value=1, max_value=99, value=80)
    st.caption("4 calls per month — your most important stores")
with col2:
    f_fortnightly = st.number_input("Fortnightly (score >=)", min_value=1, max_value=99, value=60)
    st.caption("2 calls per month")
with col3:
    f_monthly     = st.number_input("Monthly (score >=)",     min_value=1, max_value=99, value=40)
    st.caption("1 call per month")
with col4:
    st.markdown("**Bi-weekly**")
    st.caption(f"Score below {f_monthly} → 0.5 calls per month — lowest priority")

st.markdown("---")

# ── SAVE ──────────────────────────────────────────────────────────────────────
st.subheader("7. Save configuration")

can_save = total == 100 and len(final_categories) > 0

if not can_save:
    if total != 100:
        st.warning("Fix scoring weights to equal 100% before saving.")
    if not final_categories:
        st.warning("Select at least one category to scrape.")
else:
    if st.button("Save market configuration", type="primary"):
        st.session_state["market_config"] = {
            "market_name":    market_name,
            "country":        country,
            "region":         region,
            "city":           city_sel,
            "lat_min":        lat_min,
            "lat_max":        lat_max,
            "lng_min":        lng_min,
            "lng_max":        lng_max,
            "rep_count":      int(rep_count),
            "categories":     final_categories,
            "category_tiers": cat_tiers,
            "market_api_key": market_api_key,
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
        st.success(f"Configuration saved for {market_name}. Go to Run Pipeline in the sidebar.")
        st.balloons()

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
