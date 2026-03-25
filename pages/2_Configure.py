import streamlit as st

st.set_page_config(page_title="Configure — Coverage Tool", page_icon="⚙️", layout="wide")
st.title("Configure Market")

PRESETS = {
    "Custom": None,
    "UAE - Dubai":          dict(lat_min=25.10, lat_max=25.30, lng_min=55.20, lng_max=55.40, w_rating=20, w_reviews=25, w_category=20, w_sales=20, w_lines=15, f_weekly=80, f_fortnightly=60, f_monthly=40),
    "KSA - Riyadh":         dict(lat_min=24.55, lat_max=24.85, lng_min=46.55, lng_max=46.85, w_rating=15, w_reviews=30, w_category=25, w_sales=20, w_lines=10, f_weekly=75, f_fortnightly=55, f_monthly=35),
    "UK - London":          dict(lat_min=51.40, lat_max=51.60, lng_min=-0.25, lng_max=0.05,  w_rating=20, w_reviews=20, w_category=20, w_sales=25, w_lines=15, f_weekly=80, f_fortnightly=65, f_monthly=45),
    "South Africa - JHB":   dict(lat_min=-26.30, lat_max=-26.00, lng_min=27.90, lng_max=28.20, w_rating=20, w_reviews=25, w_category=20, w_sales=20, w_lines=15, f_weekly=75, f_fortnightly=55, f_monthly=35),
    "Philippines - Manila": dict(lat_min=14.50, lat_max=14.70, lng_min=120.95, lng_max=121.15, w_rating=15, w_reviews=35, w_category=20, w_sales=15, w_lines=15, f_weekly=70, f_fortnightly=50, f_monthly=30),
}

CATEGORY_OPTIONS = [
    "supermarket", "convenience_store", "pharmacy",
    "gas_station", "liquor_store", "grocery_or_supermarket",
    "hypermarket", "dollar_store", "variety_store", "newsagent",
]

TIER_LABELS = {1: "Tier 1 - 100% fit", 2: "Tier 2 - 80% fit", 3: "Tier 3 - 55% fit", 4: "Tier 4 - 30% fit"}

st.subheader("1. Market preset")
preset_name = st.selectbox("Load a preset or choose Custom", list(PRESETS.keys()))
preset = PRESETS[preset_name]

def pv(key, default):
    return preset[key] if preset else default

st.markdown("---")
st.subheader("2. Market details")
col1, col2 = st.columns(2)
with col1:
    market_name = st.text_input("Market name", value=preset_name if preset else "My Market")
    rep_count = st.number_input("Number of field reps", min_value=1, max_value=100, value=6)
with col2:
    market_api_key = st.text_input(
        "Market-specific Google API key (optional)",
        type="password",
        placeholder="Leave blank to use the global key set by admin",
    )

col1, col2, col3, col4 = st.columns(4)
with col1:
    lat_min = st.number_input("Lat min", value=float(pv("lat_min", 25.10)), format="%.4f")
with col2:
    lat_max = st.number_input("Lat max", value=float(pv("lat_max", 25.30)), format="%.4f")
with col3:
    lng_min = st.number_input("Lng min", value=float(pv("lng_min", 55.20)), format="%.4f")
with col4:
    lng_max = st.number_input("Lng max", value=float(pv("lng_max", 55.40)), format="%.4f")

st.caption("Find bounding box coordinates at bboxfinder.com")
st.markdown("---")

st.subheader("3. Store categories to scrape")
selected_cats = st.multiselect(
    "Select categories",
    options=CATEGORY_OPTIONS,
    default=["supermarket", "convenience_store", "pharmacy", "gas_station", "liquor_store"],
)
st.markdown("---")

st.subheader("4. Category tier multipliers")
cat_tiers = {}
if selected_cats:
    cols = st.columns(2)
    for i, cat in enumerate(selected_cats):
        with cols[i % 2]:
            cat_tiers[cat] = st.selectbox(
                cat.replace("_", " ").title(),
                options=[1, 2, 3, 4],
                format_func=lambda x: TIER_LABELS[x],
                key=f"tier_{cat}",
            )
st.markdown("---")

st.subheader("5. Scoring weights — must sum to 100%")
col1, col2 = st.columns(2)
with col1:
    w_rating   = st.slider("Rating",    0, 50, pv("w_rating",   20))
    w_reviews  = st.slider("Reviews",   0, 50, pv("w_reviews",  25))
    w_category = st.slider("Category",  0, 50, pv("w_category", 20))
with col2:
    w_sales    = st.slider("Sales",     0, 50, pv("w_sales",    20))
    w_lines    = st.slider("Lines",     0, 50, pv("w_lines",    15))

total = w_rating + w_reviews + w_category + w_sales + w_lines
if total == 100:
    st.success(f"Total: {total}% — valid")
else:
    st.error(f"Total: {total}% — must equal 100%")

st.markdown("---")
st.subheader("6. Visit frequency thresholds")
col1, col2, col3 = st.columns(3)
with col1:
    f_weekly      = st.number_input("Weekly score >=",      min_value=1, max_value=99, value=pv("f_weekly",      80))
    st.caption("4 calls per month")
with col2:
    f_fortnightly = st.number_input("Fortnightly score >=", min_value=1, max_value=99, value=pv("f_fortnightly", 60))
    st.caption("2 calls per month")
with col3:
    f_monthly     = st.number_input("Monthly score >=",     min_value=1, max_value=99, value=pv("f_monthly",     40))
    st.caption("1 call per month — below this is bi-weekly")

st.markdown("---")
st.subheader("7. Save")

if total != 100:
    st.warning("Fix weights to equal 100% before saving.")
elif not selected_cats:
    st.warning("Select at least one category.")
else:
    if st.button("Save market configuration", type="primary"):
        st.session_state["market_config"] = {
            "market_name":    market_name,
            "lat_min":        lat_min,
            "lat_max":        lat_max,
            "lng_min":        lng_min,
            "lng_max":        lng_max,
            "rep_count":      int(rep_count),
            "categories":     selected_cats,
            "category_tiers": cat_tiers,
            "market_api_key": market_api_key,
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

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
