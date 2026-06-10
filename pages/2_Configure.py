import streamlit as st
import pandas as pd
import requests
import math


# ── Region boundary model ─────────────────────────────────────────────────────
# Builds an "invisible fence" per region from the coverage file's outlets.
# Scraped outlets are later classified by whether their lat/lng falls inside a
# fence — this removes the coverage-vs-scrape city-name mismatch.
def _hav_km(la1, ln1, la2, ln2):
    R = 6371.0
    p = math.pi / 180
    a = (math.sin((la2 - la1) * p / 2) ** 2 +
         math.cos(la1 * p) * math.cos(la2 * p) *
         math.sin((ln2 - ln1) * p / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(max(0, a)))


def _convex_hull(pts):
    """Andrew's monotone chain. pts = list of (lat, lng). Returns hull points."""
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _buffer_hull(hull, centroid, km):
    """Push every hull vertex outward from the centroid by ~km kilometres."""
    clat, clng = centroid
    buf_deg = km / 111.0  # ~111 km per degree
    out = []
    for la, ln in hull:
        dlat, dlng = la - clat, ln - clng
        dist = math.sqrt(dlat ** 2 + dlng ** 2)
        if dist == 0:
            out.append((la, ln))
            continue
        scale = (dist + buf_deg) / dist
        out.append((clat + dlat * scale, clng + dlng * scale))
    return out


def build_region_boundaries(rows, buffer_km=3.0):
    """rows = list of dicts with 'region', 'lat', 'lng'. Returns
    {region: {centroid, polygon, radius_km}}. polygon is the buffered hull
    (or None for sparse regions, which fall back to centroid + radius_km)."""
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        reg = str(r.get("region", "") or "").strip()
        try:
            la, ln = float(r.get("lat")), float(r.get("lng"))
        except (TypeError, ValueError):
            continue
        if not reg or la == 0 or ln == 0:
            continue
        groups[reg].append((la, ln))

    boundaries = {}
    for reg, pts in groups.items():
        if not pts:
            continue
        clat = sum(p[0] for p in pts) / len(pts)
        clng = sum(p[1] for p in pts) / len(pts)
        # Drop geographic outliers (beyond 2.5× median distance from centroid)
        dists = sorted(_hav_km(clat, clng, p[0], p[1]) for p in pts)
        median_d = dists[len(dists) // 2] if dists else 0
        if median_d > 0:
            pts = [p for p in pts if _hav_km(clat, clng, p[0], p[1]) <= 2.5 * median_d] or pts
            clat = sum(p[0] for p in pts) / len(pts)
            clng = sum(p[1] for p in pts) / len(pts)
        # Build the fence
        if len(pts) >= 3:
            hull = _convex_hull(pts)
            if len(hull) >= 3:
                boundaries[reg] = {
                    "centroid": (clat, clng),
                    "polygon": _buffer_hull(hull, (clat, clng), buffer_km),
                    "radius_km": None,
                }
                continue
        # Sparse region — centroid + radius circle
        max_d = max((_hav_km(clat, clng, p[0], p[1]) for p in pts), default=0)
        boundaries[reg] = {
            "centroid": (clat, clng),
            "polygon": None,
            "radius_km": max_d + buffer_km,
        }
    return boundaries


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

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE / LOAD FULL CONFIGURATION (JSON)
# ═══════════════════════════════════════════════════════════════════════════════
# Pure data persistence — no logic touched. Lets the user export every
# setting on the Configure page (country, regions, cities, scrape mode,
# selected cities, region filter, scrape categories, direct-accounts list,
# rep rules, visit playbook entries, route plan month/year, etc.) into a
# single JSON file, then re-import on a future session to restore everything
# in one click. Streamlit normally wipes session state on restart, so this
# is the cure for "I have to redo all the setup every time."
import json as _cfg_json

def _collect_config_snapshot():
    """Read every relevant Configure setting from session_state into a dict."""
    snap = {}
    # Direct session_state keys we write/manage from our own code
    for k in [
        "country_name", "country_bbox",
        "region_entries", "city_entries",
        "scrape_mode", "selected_cities", "region_filter",
        "region_city_list_cache",
        "direct_accounts", "sf_rules", "region_boundaries",
        "admin_benchmarks", "admin_scoring_weights", "admin_scoring_weights_gap",
        "enrich_all_portfolio", "market_config",
    ]:
        if k in st.session_state:
            snap[k] = st.session_state[k]
    # Streamlit widget keys whose values persist user choices in the UI but
    # which we don't otherwise own. Saving them lets a load restore the
    # widgets exactly as the user left them — including the categories
    # multiselect, rep mode radio, region-filter text, etc.
    for wk in [
        "cats_tab1", "extra_cats_tab1",
        "rep_mode_radio", "store_select_pct_input",
        "region_filter_input", "scrape_mode_radio",
        "cities_multiselect",
        "direct_accounts_input",
        "route_month_sel", "route_year_sel",
        "country_input_field", "region_input_field", "city_input_field",
    ]:
        if wk in st.session_state:
            snap[wk] = st.session_state[wk]
    # Visit playbook widget values (per category: lv_*, ld_*, mv_*, md_*, sv_*, sd_*)
    pb = {}
    for k, v in st.session_state.items():
        if isinstance(k, str) and any(k.startswith(p) for p in ("lv_", "ld_", "mv_", "md_", "sv_", "sd_")):
            pb[k] = v
    snap["_visit_playbook_widgets"] = pb
    return snap

def _apply_config_snapshot(snap):
    """Write a saved snapshot back into session_state. Widget keys are
    written BEFORE the widgets render on next rerun so Streamlit picks
    them up as defaults."""
    if not isinstance(snap, dict):
        return 0
    n = 0
    pb = snap.pop("_visit_playbook_widgets", {}) or {}
    for k, v in snap.items():
        st.session_state[k] = v
        n += 1
    for k, v in pb.items():
        st.session_state[k] = v
        n += 1
    return n

# Persistent banner that survives the rerun triggered by a successful load
# so the user actually sees what was restored.
_just_loaded = st.session_state.pop("_config_just_loaded", None)
if _just_loaded:
    _summary_bits = []
    if _just_loaded.get("country"):
        _summary_bits.append(f"Country: **{_just_loaded['country']}**")
    if _just_loaded.get("regions"):
        _summary_bits.append(f"{_just_loaded['regions']} region(s)")
    if _just_loaded.get("cities"):
        _summary_bits.append(f"{_just_loaded['cities']} city/area entry/entries")
    if _just_loaded.get("scrape_mode"):
        _summary_bits.append(f"scrape mode = **{_just_loaded['scrape_mode']}**")
    if _just_loaded.get("selected_cities"):
        _summary_bits.append(f"{_just_loaded['selected_cities']} cities selected")
    if _just_loaded.get("categories"):
        _summary_bits.append(f"{_just_loaded['categories']} scrape categories")
    if _just_loaded.get("playbook_entries"):
        _summary_bits.append(f"visit playbook for {_just_loaded['playbook_entries']} categories")
    if _just_loaded.get("sf_rules"):
        _summary_bits.append(f"{_just_loaded['sf_rules']} dedicated rep rule(s)")
    if _just_loaded.get("direct_accounts"):
        _summary_bits.append(f"{_just_loaded['direct_accounts']} direct-account banner(s)")
    _body = " · ".join(_summary_bits) if _summary_bits else f"{_just_loaded.get('total', 0)} settings"
    st.success(
        f"  Configuration restored — {_body}. "
        "Open each tab below to confirm everything is back as you saved it."
    )

with st.expander("  Save / load configuration", expanded=False):
    st.caption(
        "Save your current setup (country, regions, cities, scrape mode, categories, "
        "rep rules, direct-accounts list, visit playbook, route plan, etc.) to a JSON "
        "file. Upload it next session to restore everything in one click — no manual "
        "re-clicking required."
    )
    _save_col1, _save_col2 = st.columns(2)
    with _save_col1:
        _cfg_snap = _collect_config_snapshot()
        _cfg_json_str = _cfg_json.dumps(_cfg_snap, indent=2, default=str)
        _save_name = (st.session_state.get("country_name") or "config").replace(" ", "_")
        st.download_button(
            "  Save configuration (JSON)",
            _cfg_json_str,
            file_name=f"coverage_config_{_save_name}.json",
            mime="application/json",
            help="Downloads every Configure setting into a single file.",
            use_container_width=True,
        )
        st.caption("Tip: save after first setup, load on future sessions.")
    with _save_col2:
        # Use a rotating key so the uploader is "fresh" after each successful
        # apply — otherwise Streamlit keeps the file on every rerun, and the
        # apply block fires again, silently overwriting any edits the user
        # makes (so e.g. switching from Recommended to Fixed rep gets undone
        # on the next rerun).
        _upload_nonce = st.session_state.get("_cfg_upload_nonce", 0)
        _cfg_upload = st.file_uploader(
            "Load configuration (JSON)",
            type=["json"],
            key=f"cfg_upload_{_upload_nonce}",
        )
        if _cfg_upload is not None:
            try:
                _loaded = _cfg_json.load(_cfg_upload)
                _n = _apply_config_snapshot(_loaded)
                # Build a richer summary for the post-rerun banner so user knows
                # *what* came back, not just "115 things".
                _pb_count = sum(
                    1 for k in (_loaded.get("_visit_playbook_widgets") or {}).keys()
                    if k.startswith("lv_")
                )
                _just_loaded_payload = {
                    "total":            _n,
                    "country":          _loaded.get("country_name", ""),
                    "regions":          len(_loaded.get("region_entries") or []),
                    "cities":           len(_loaded.get("city_entries") or []),
                    "scrape_mode":      _loaded.get("scrape_mode", ""),
                    "selected_cities":  len(_loaded.get("selected_cities") or []),
                    "categories":       len((_loaded.get("market_config") or {}).get("categories") or []),
                    "playbook_entries": _pb_count,
                    "sf_rules":         len(_loaded.get("sf_rules") or []),
                    "direct_accounts":  len(_loaded.get("direct_accounts") or []),
                }
                st.session_state["_config_just_loaded"] = _just_loaded_payload
                # Rotate the nonce so the uploader is gone on rerun and the
                # apply block doesn't fire again on subsequent edits.
                st.session_state["_cfg_upload_nonce"] = _upload_nonce + 1
                st.rerun()
            except Exception as _e:
                st.error(f"Could not read configuration file: {_e}")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# THREE TABS: Market Area / My Team / Visit Playbook
# ═══════════════════════════════════════════════════════════════════════════════
tab_market, tab_team, tab_playbook = st.tabs(["Market Area", "My Team", "Visit Playbook"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: MARKET AREA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_market:
    st.markdown("**Upload your current store coverage**")
    st.caption("Required: Store Name, Address, City. Optional: Category, Sales, Coordinates.")

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

            # Fix double-encoded text (mojibake) — when a UTF-8 CSV has been
            # round-tripped through Excel, accented characters land in memory as
            # e.g. "Atacadão" instead of "Atacadão". Reverse the damage by
            # re-encoding as latin-1 and decoding as utf-8; only keep the
            # result when it strictly reduces the mojibake-marker count.
            def _fix_mojibake(text):
                if not isinstance(text, str) or not text:
                    return text
                if "Ã" not in text and "Â" not in text:
                    return text
                try:
                    fixed = text.encode("latin-1").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    return text
                before = text.count("Ã") + text.count("Â")
                after = fixed.count("Ã") + fixed.count("Â")
                return fixed if after < before else text
            for _col in df.columns:
                if df[_col].dtype == object:
                    df[_col] = df[_col].map(_fix_mojibake)

            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            df = df.dropna(subset=["store_name","address","city"], how="all").reset_index(drop=True)
            df = df[df["store_name"].fillna("").str.strip() != ""].reset_index(drop=True)
            if "lat" not in df.columns: df["lat"] = None
            if "lng" not in df.columns: df["lng"] = None
            missing = [c for c in ["store_name","address","city"] if c not in df.columns]
            if missing:
                st.error(f"Missing required columns: {', '.join(c.replace('_',' ').title() for c in missing)}")
            else:
                if "store_id" not in df.columns:
                    df["store_id"] = [f"S{i+1:03d}" for i in range(len(df))]
                if "annual_sales_usd" not in df.columns:
                    df["annual_sales_usd"] = 0
                if "lines_per_store" not in df.columns:
                    df["lines_per_store"] = 0
                portfolio_df = df
                st.success(f"Loaded **{len(df)} stores**")
                _preview = df.head(5).copy()
                _preview.columns = [c.replace("_"," ").title() for c in _preview.columns]
                st.dataframe(_preview, use_container_width=True, hide_index=True)

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
                        st.info(f"Categories detected: **{', '.join(c.replace('_',' ').title() for c in detected_categories)}**")

                st.session_state["portfolio_df"] = portfolio_df

                # Build region boundary model from coverage outlet coordinates
                if "region" in df.columns and "lat" in df.columns and "lng" in df.columns:
                    _bnd = build_region_boundaries(df.to_dict("records"), buffer_km=3.0)
                    st.session_state["region_boundaries"] = _bnd
                    if _bnd:
                        st.caption(
                            f"Region fences built from coverage outlets: "
                            f"{', '.join(sorted(_bnd.keys()))}"
                        )
                else:
                    st.session_state["region_boundaries"] = {}
        except Exception as e:
            st.error(f"Error reading file: {e}")

    with st.expander("Column guide & template"):
        st.markdown("**Required:** Store Name, Address, City\n\n**Optional:** Store ID, Category, Annual Sales, Lines Per Store, Lat, Lng, District, Region\n\nAny extra columns (Account, Channel, etc.) are auto-detected for rep rules.")
        sample = pd.DataFrame([
            {"store_id":"S001","store_name":"Carrefour Express","address":"Main St 100","city":"Muscat","category":"supermarket","annual_sales_usd":125000,"lines_per_store":54},
            {"store_id":"S002","store_name":"Lulu Hypermarket","address":"Al Khuwair","city":"Muscat","category":"hypermarket","annual_sales_usd":210000,"lines_per_store":72},
        ])
        st.download_button("Download template CSV", sample.to_csv(index=False), "coverage_template.csv", "text/csv")

    st.markdown("---")

    # ── Location search ──────────────────────────────────────────────────────
    st.markdown("**Define your market area**")

    api_key = get_api_key()
    if not api_key:
        st.warning("Google Maps API key not set. Set GOOGLE_MAPS_API_KEY in Streamlit Secrets.")

    col1, col2 = st.columns([3, 1])
    with col1:
        country_input = st.text_input("Country", placeholder="e.g. Oman, Morocco, Pakistan...",
            value=st.session_state.get("country_name") or "", key="country_input_field")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_country_btn = st.button("Search", type="primary", key="btn_country")

    if search_country_btn and country_input:
        if not api_key:
            st.error("Cannot search — API key not set.")
        else:
            with st.spinner(f"Searching for {country_input}..."):
                results = search_location(f"{country_input} country", api_key)
            if results:
                country_results = geocode_lookup(country_input, api_key)
                country_result = None
                for r in country_results:
                    if "country" in r.get("types", []):
                        country_result = r
                        break
                if not country_result and country_results:
                    country_result = country_results[0]
                if country_result:
                    bbox = extract_bbox(country_result)
                    name = extract_component(country_result, "country") or country_input
                    st.session_state["country_name"] = name
                    st.session_state["country_bbox"] = bbox
                    st.session_state["region_entries"] = []
                    st.session_state["city_entries"] = []
                    st.rerun()
                else:
                    st.error(f"Could not find country: {country_input}")
            else:
                st.error(f"No results for {country_input}. Check spelling.")

    if st.session_state.get("country_name"):
        st.success(f"Country: **{st.session_state['country_name']}**")
        if st.button("Clear and start over", key="clear_country"):
            st.session_state["country_name"] = None
            st.session_state["country_bbox"] = None
            st.session_state["region_entries"] = []
            st.session_state["city_entries"] = []
            st.rerun()

    # ── Regions ──────────────────────────────────────────────────────────────
    if st.session_state.get("country_name"):
        country_name = st.session_state["country_name"]
        st.caption("Add regions and/or cities to define the scraping area.")

        col1, col2 = st.columns([3, 1])
        with col1:
            region_input = st.text_input("Region / Governorate", placeholder="e.g. Muscat Governorate, Dhofar...", key="region_input_field")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            add_region_btn = st.button("Add region", key="btn_region")

        if add_region_btn and region_input:
            if not api_key:
                st.error("Cannot search — API key not set.")
            else:
                with st.spinner(f"Searching for {region_input}..."):
                    query = f"{region_input}, {country_name}"
                    results = geocode_lookup(query, api_key)
                if results:
                    r = results[0]
                    bbox = extract_bbox(r)
                    name = r.get("formatted_address", region_input).split(",")[0].strip()
                    existing_names = [e["name"] for e in st.session_state["region_entries"]]
                    if name in existing_names:
                        st.warning(f"{name} is already added.")
                    else:
                        st.session_state["region_entries"].append({"name": name, "bbox": bbox})
                        st.rerun()
                else:
                    st.error(f"Could not find {region_input} in {country_name}.")

        if st.session_state["region_entries"]:
            for i, entry in enumerate(st.session_state["region_entries"]):
                col_a, col_b = st.columns([5, 1])
                col_a.write(f"  {entry['name']}")
                if col_b.button("Remove", key=f"remove_region_{i}"):
                    st.session_state["region_entries"].pop(i)
                    st.rerun()

        # ── Cities ───────────────────────────────────────────────────────────
        col1, col2 = st.columns([3, 1])
        with col1:
            city_input = st.text_input("City / Area", placeholder="e.g. Muscat, Salalah, Sohar...", key="city_input_field")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            add_city_btn = st.button("Add city", key="btn_city")

        if add_city_btn and city_input:
            if not api_key:
                st.error("Cannot search — API key not set.")
            else:
                region_context = st.session_state["region_entries"][0]["name"] if st.session_state["region_entries"] else ""
                query = f"{city_input}, {region_context}, {country_name}" if region_context else f"{city_input}, {country_name}"
                with st.spinner(f"Searching for {city_input}..."):
                    results = geocode_lookup(query, api_key)
                if results:
                    r = results[0]
                    bbox = extract_bbox(r)
                    name = r.get("formatted_address", city_input).split(",")[0].strip()
                    existing_names = [e["name"] for e in st.session_state["city_entries"]]
                    if name in existing_names:
                        st.warning(f"{name} is already added.")
                    else:
                        st.session_state["city_entries"].append({"name": name, "bbox": bbox})
                        st.rerun()
                else:
                    st.error(f"Could not find '{city_input}' in {country_name}.")

        if st.session_state["city_entries"]:
            for i, entry in enumerate(st.session_state["city_entries"]):
                col_a, col_b = st.columns([5, 1])
                col_a.write(f"  {entry['name']}")
                if col_b.button("Remove", key=f"remove_city_{i}"):
                    st.session_state["city_entries"].pop(i)
                    st.rerun()

    # ── Bounding box ─────────────────────────────────────────────────────────
    final_bbox = None
    final_scope = ""
    if st.session_state.get("city_entries"):
        boxes = [e["bbox"] for e in st.session_state["city_entries"]]
        final_bbox = merge_bboxes(boxes)
        final_scope = ", ".join(e["name"] for e in st.session_state["city_entries"])
    elif st.session_state.get("region_entries"):
        boxes = [e["bbox"] for e in st.session_state["region_entries"]]
        final_bbox = merge_bboxes(boxes)
        final_scope = ", ".join(e["name"] for e in st.session_state["region_entries"])
    elif st.session_state.get("country_bbox"):
        final_bbox = st.session_state["country_bbox"]
        final_scope = st.session_state.get("country_name", "")

    if final_bbox:
        st.success(f"Coverage area: **{final_scope}**")

        # ── Region must appear in address (optional state/province filter) ───
        st.markdown("**Region must appear in address** *(optional)*")
        st.caption(
            "Bounding boxes are rectangles and inevitably overlap neighbouring states/provinces. "
            "Enter a state code or region name (e.g. `PE` for Pernambuco, `CA` for California, "
            "`Muscat`, `Dubai`, `MH` or `Maharashtra`) and any scraped store whose Google address "
            "doesn't mention it will be excluded from the universe. Leave blank to keep today's behaviour."
        )
        _region_filter_val = st.text_input(
            "Filter text",
            value=st.session_state.get("region_filter", ""),
            placeholder="e.g. PE",
            key="region_filter_input",
            label_visibility="collapsed",
        )
        st.session_state["region_filter"] = _region_filter_val.strip()
        if _region_filter_val.strip():
            st.caption(f"  Scraped stores whose address contains **'{_region_filter_val.strip()}'** will be kept; others dropped.")

        # ── Scrape mode (rectangle vs city-by-city) ──────────────────────────
        st.markdown("**Scrape mode**")
        st.caption(
            "**Rectangle** scrapes a tile grid across the bounding box — fast to configure but pulls "
            "in neighbouring states/provinces near borders. "
            "**Cities** loads the list of cities inside the bbox from OpenStreetMap; you pick which "
            "ones to scrape (all by default). Stores from outside your chosen cities are never even "
            "queried — no neighbour-state pollution by design."
        )
        _scrape_mode_default = st.session_state.get("scrape_mode", "rectangle")
        _scrape_mode = st.radio(
            "Mode",
            options=["rectangle", "cities"],
            format_func=lambda m: "Rectangle (default — today's behaviour)" if m == "rectangle" else "Cities (anchor scrape on each city in this region)",
            index=0 if _scrape_mode_default == "rectangle" else 1,
            key="scrape_mode_radio",
            label_visibility="collapsed",
        )
        st.session_state["scrape_mode"] = _scrape_mode

        if _scrape_mode == "cities":
            _cities_key = f"{final_bbox[0]:.3f},{final_bbox[1]:.3f},{final_bbox[2]:.3f},{final_bbox[3]:.3f}"
            _city_cache = st.session_state.get("region_city_list_cache", {})
            _city_list = _city_cache.get(_cities_key, [])
            _col_cm1, _col_cm2 = st.columns([1, 2])
            with _col_cm1:
                if st.button("  Load cities in this region", key="btn_load_cities"):
                    with st.spinner("Querying OpenStreetMap..."):
                        import requests as _req_osm
                        _lat_min, _lat_max, _lng_min, _lng_max = final_bbox
                        _headers = {
                            "User-Agent": "CoverageTool/1.0 (Streamlit app for FMCG sales planning)",
                            "Accept": "application/json",
                        }
                        _servers = [
                            "https://overpass-api.de/api/interpreter",
                            "https://overpass.kumi.systems/api/interpreter",
                            "https://overpass.osm.ch/api/interpreter",
                            "https://overpass.private.coffee/api/interpreter",
                        ]

                        # Build candidate region names to try as OSM admin areas.
                        # Bbox queries pull in neighbouring states; area queries
                        # restrict to the actual admin polygon. We try multiple
                        # name variants so OSM's local naming (e.g. "Pernambuco"
                        # rather than "State of Pernambuco") matches.
                        def _strip_admin_prefix(nm):
                            s = str(nm or "").strip()
                            for p in ("State of ", "Estado de ", "Estado do ",
                                      "Province of ", "Provincia de ", "Província de ",
                                      "Region of ", "Região de ",
                                      "Governorate of ", "Governorate ",
                                      "Department of ", "Departamento de ",
                                      "Wilaya of ", "Emirate of "):
                                if s.lower().startswith(p.lower()):
                                    return s[len(p):].strip()
                            return s
                        _region_names = []
                        for _re in (st.session_state.get("region_entries") or []):
                            _rn = _re.get("name", "").strip()
                            if not _rn: continue
                            for _v in (_rn, _strip_admin_prefix(_rn)):
                                if _v and _v not in _region_names:
                                    _region_names.append(_v)

                        _queries = []
                        # Preferred: actual municipalities (admin_level 7/8) inside
                        # the state polygon. For Brazil admin_level=8 is "município"
                        # (~185 in Pernambuco); most countries use 7 or 8 for the
                        # city/municipality level. This avoids pulling in hamlets
                        # tagged as place=village.
                        for _rn in _region_names:
                            _rn_esc = _rn.replace('"', '\\"')
                            _queries.append((f"area:{_rn} admin8", f"""
                            [out:json][timeout:90];
                            area["name"="{_rn_esc}"]["admin_level"~"^(4|5|6)$"]["boundary"="administrative"]->.searchArea;
                            (
                              relation["boundary"="administrative"]["admin_level"~"^(7|8)$"](area.searchArea);
                            );
                            out center;
                            """.strip()))
                        # Second choice: cities and towns only (skip villages) inside
                        # the polygon — gives ~50 entries for PE but they're the
                        # densely populated ones.
                        for _rn in _region_names:
                            _rn_esc = _rn.replace('"', '\\"')
                            _queries.append((f"area:{_rn} city+town", f"""
                            [out:json][timeout:90];
                            area["name"="{_rn_esc}"]["admin_level"~"^(4|5|6)$"]["boundary"="administrative"]->.searchArea;
                            (
                              node["place"~"^(city|town)$"](area.searchArea);
                            );
                            out body;
                            """.strip()))
                        # Third choice: include villages too (legacy, may over-return)
                        for _rn in _region_names:
                            _rn_esc = _rn.replace('"', '\\"')
                            _queries.append((f"area:{_rn} all places", f"""
                            [out:json][timeout:90];
                            area["name"="{_rn_esc}"]["admin_level"~"^(4|5|6)$"]["boundary"="administrative"]->.searchArea;
                            (
                              node["place"~"^(city|town|village)$"](area.searchArea);
                            );
                            out body;
                            """.strip()))
                        # Bbox fallbacks if no admin polygon matched
                        _queries.append(("bbox admin8", f"""
                        [out:json][timeout:90];
                        (
                          relation["boundary"="administrative"]["admin_level"~"^(7|8)$"]({_lat_min},{_lng_min},{_lat_max},{_lng_max});
                        );
                        out center;
                        """.strip()))
                        _queries.append(("bbox city+town", f"""
                        [out:json][timeout:90];
                        (
                          node["place"~"^(city|town)$"]({_lat_min},{_lng_min},{_lat_max},{_lng_max});
                        );
                        out body;
                        """.strip()))

                        _elements = []
                        _tried = []
                        _winning_query = ""
                        for _srv in _servers:
                            for _ql, _q in _queries:
                                try:
                                    _resp = _req_osm.post(_srv, data={"data": _q}, headers=_headers, timeout=100)
                                    _host = _srv.split('//')[1].split('/')[0]
                                    if _resp.status_code == 200:
                                        _els = _resp.json().get("elements", []) or []
                                        _tried.append(f"{_host} {_ql}: 200 → {len(_els)} elements")
                                        if _els:
                                            _elements = _els
                                            _winning_query = _ql
                                            break
                                    else:
                                        _tried.append(f"{_host} {_ql}: HTTP {_resp.status_code} — {(_resp.text or '')[:80]}")
                                except Exception as _ex_osm:
                                    _host = _srv.split('//')[1].split('/')[0]
                                    _tried.append(f"{_host} {_ql}: EXC {str(_ex_osm)[:80]}")
                            if _elements:
                                break
                    def _pop(tags):
                        for k in ("population", "ref:population"):
                            v = tags.get(k)
                            if v:
                                try: return int(str(v).replace(",","").replace(".","").strip())
                                except Exception: pass
                        return 0
                    def _radius_km(pt, pop):
                        if pop >= 1_000_000: return 12
                        if pop >= 500_000:   return 8
                        if pop >= 100_000:   return 5
                        if pop >= 30_000:    return 3
                        if pop >= 5_000:     return 2
                        if pt == "city": return 5
                        if pt == "town": return 3
                        if pt == "village": return 1.5
                        # No place tag (came from admin_level relation) — assume town-sized
                        return 4
                    _seen = set(); _loaded = []
                    for el in _elements:
                        _tags = el.get("tags", {}) or {}
                        _nm = (_tags.get("name:en") or _tags.get("name") or "").strip()
                        if not _nm or _nm.lower() in _seen:
                            continue
                        _seen.add(_nm.lower())
                        _pt = _tags.get("place","")
                        _pp = _pop(_tags)
                        _lat_el = el.get("lat") or el.get("center",{}).get("lat")
                        _lng_el = el.get("lon") or el.get("center",{}).get("lon")
                        if _lat_el is None or _lng_el is None:
                            continue
                        _loaded.append({
                            "name": _nm, "lat": _lat_el, "lng": _lng_el,
                            "place_type": _pt, "population": _pp,
                            "radius_km": _radius_km(_pt, _pp),
                        })
                    _loaded.sort(key=lambda c: (-c["population"], c["name"]))
                    _city_cache[_cities_key] = _loaded
                    st.session_state["region_city_list_cache"] = _city_cache
                    _city_list = _loaded
                    if not _loaded:
                        st.warning(
                            f"OpenStreetMap returned no cities for bbox "
                            f"({_lat_min:.3f},{_lng_min:.3f},{_lat_max:.3f},{_lng_max:.3f}). "
                            f"Try again later or use Rectangle mode."
                        )
                        with st.expander("Diagnostic info — what each Overpass server returned"):
                            st.code("\n".join(_tried) if _tried else "no attempts logged")
                    else:
                        if _winning_query.startswith("area:") and "admin8" in _winning_query:
                            _src = "admin polygon · municipalities only"
                        elif _winning_query.startswith("area:") and "city+town" in _winning_query:
                            _src = "admin polygon · cities + towns (no villages)"
                        elif _winning_query.startswith("area:"):
                            _src = "admin polygon · all populated places"
                        else:
                            _src = "bounding box (may include neighbours)"
                        st.success(f"Loaded **{len(_loaded)}** cities from OpenStreetMap · source: {_src}")
                        if _winning_query.startswith("bbox") and _region_names:
                            with st.expander("Why bbox fallback was used"):
                                st.code("\n".join(_tried))
            with _col_cm2:
                if _city_list:
                    st.caption(f"**{len(_city_list)}** cities available · sorted by population (largest first)")

            if _city_list:
                _selected_default = st.session_state.get("selected_cities", [c["name"] for c in _city_list])
                # Reconcile selection with current city list (drop names no longer present)
                _valid_names = {c["name"] for c in _city_list}
                _selected_default = [n for n in _selected_default if n in _valid_names] or [c["name"] for c in _city_list]
                _options = [f"{c['name']} · pop {c['population']:,}" if c["population"] else c["name"] for c in _city_list]
                _name_by_opt = {opt: c["name"] for opt, c in zip(_options, _city_list)}
                _opt_by_name = {c["name"]: opt for opt, c in zip(_options, _city_list)}
                _default_opts = [_opt_by_name[n] for n in _selected_default if n in _opt_by_name]
                _col_cs1, _col_cs2, _col_cs3 = st.columns([1,1,3])
                with _col_cs1:
                    if st.button("Select all", key="btn_cities_all"):
                        st.session_state["selected_cities"] = [c["name"] for c in _city_list]
                        st.rerun()
                with _col_cs2:
                    if st.button("Deselect all", key="btn_cities_none"):
                        st.session_state["selected_cities"] = []
                        st.rerun()
                _picked_opts = st.multiselect(
                    "Cities to scrape",
                    options=_options,
                    default=_default_opts,
                    key="cities_multiselect",
                )
                _picked_names = [_name_by_opt[o] for o in _picked_opts]
                st.session_state["selected_cities"] = _picked_names
                _picked_objs = [c for c in _city_list if c["name"] in set(_picked_names)]
                _est_tiles = sum(
                    max(1, int((c["radius_km"] * 2) // 6)) ** 2 if c["radius_km"] > 3 else 1
                    for c in _picked_objs
                )
                st.caption(f"**{len(_picked_names)}** of {len(_city_list)} cities selected · estimated ~{_est_tiles} scrape tiles")
            else:
                st.info("Click **Load cities in this region** to fetch the list from OpenStreetMap. If loading fails or returns nothing, switch back to **Rectangle** mode.")

    st.markdown("---")

    # ── Scraping categories ──────────────────────────────────────────────────
    st.markdown("**Store categories to scrape**")
    if google_categories:
        st.success(f"Auto-detected: **{', '.join(c.replace('_',' ').title() for c in google_categories)}**")
        extra = st.multiselect("Add extra categories",
            options=[c for c in ["supermarket","convenience_store","pharmacy","gas_station",
                                  "liquor_store","grocery_or_supermarket","hypermarket"]
                     if c not in google_categories],
            default=[], key="extra_cats_tab1")
        final_categories = google_categories + extra
    else:
        final_categories = st.multiselect("Select categories to scrape",
            options=["supermarket","convenience_store","pharmacy","gas_station",
                     "liquor_store","grocery_or_supermarket","hypermarket",
                     "dollar_store","variety_store"],
            default=["supermarket","convenience_store","pharmacy","gas_station"],
            key="cats_tab1")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: MY TEAM
# ═══════════════════════════════════════════════════════════════════════════════
with tab_team:
    st.markdown("**Rep planning mode**")
    rep_mode = st.radio("How should we plan reps?",
        options=["Fixed — I know how many reps I have",
                 "Recommended — tell me how many reps I need"],
        index=0, horizontal=True, key="rep_mode_radio")

    rep_count = 6
    rep_mode_key = "fixed"
    working_days = 22

    if rep_mode == "Fixed — I know how many reps I have":
        rep_mode_key = "fixed"
        rep_count = st.number_input("Number of field reps", min_value=1, max_value=200, value=6,
            help="The pipeline will assign stores to exactly this many reps.")
        st.markdown("**Time parameters**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            daily_minutes = st.number_input("Working day (min)", min_value=240, max_value=600, value=480,
                help="Full working day including travel and breaks.")
        with col2:
            break_minutes = st.number_input("Break (min/day)", min_value=0, max_value=120, value=30,
                help="Lunch and rest breaks.")
        with col3:
            working_days = st.number_input("Working days/month", min_value=15, max_value=26, value=22)
        with col4:
            avg_speed_kmh = st.number_input("Travel speed (km/h)", min_value=10, max_value=80, value=30)
    else:
        rep_mode_key = "recommended"
        st.info("The system will calculate how many reps you need based on store workload and rep capacity.")
        st.markdown("**Rep capacity**")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            daily_minutes = st.number_input("Working day (min)", min_value=240, max_value=600, value=480,
                help="Full working day including travel and breaks.")
        with col2:
            break_minutes = st.number_input("Break (min/day)", min_value=0, max_value=120, value=30,
                help="Lunch and rest breaks.")
        with col3:
            working_days = st.number_input("Working days/month", min_value=15, max_value=26, value=22)
        with col4:
            avg_speed_kmh = st.number_input("Travel speed (km/h)", min_value=10, max_value=80, value=30)
        with col5:
            effective_daily = daily_minutes - break_minutes
            monthly_cap = effective_daily * working_days
            st.metric("Capacity/month", f"{monthly_cap:,} min")

        st.markdown("**Current headcount (optional)**")
        rep_count = st.number_input("Current reps (0 = skip comparison)", min_value=0, max_value=200, value=0,
            help="Only used to compare against the recommendation.")

    st.markdown("---")

    # ── Direct accounts to exclude ───────────────────────────────────────────
    st.markdown("**Direct accounts to exclude** *(optional)*")
    st.caption(
        "Banners serviced directly by the manufacturer. Scraped stores whose names match these banners "
        "will be removed from the universe before scoring and route planning, so distributors don't get "
        "assigned to visit them. Your portfolio (current coverage) is never filtered."
    )

    _direct_default = "\n".join(st.session_state.get("direct_accounts", []))
    _direct_input = st.text_area(
        "Banner names (one per line)",
        value=_direct_default,
        height=140,
        placeholder="Walmart\nCarrefour\nAtacadão\nAssaí\nSam's Club\nMakro",
        key="direct_accounts_input",
    )
    _direct_list = [b.strip() for b in _direct_input.splitlines() if b.strip()]
    st.session_state["direct_accounts"] = _direct_list

    _col_da1, _col_da2 = st.columns([1, 2])
    with _col_da1:
        st.caption(f"**{len(_direct_list)} banners** on the exclusion list")
    with _col_da2:
        if st.button("Preview matches against last scrape", disabled=not _direct_list, key="direct_preview"):
            _cache = st.session_state.get("universe_cache", {})
            _last = next(iter(_cache.values()), None) if _cache else None
            _scraped = (_last or {}).get("universe", [])
            if not _scraped:
                st.info("No cached scrape found — run the pipeline at least once to enable preview.")
            else:
                _hits = []
                _banners_lower = [b.lower() for b in _direct_list]
                for s in _scraped:
                    _nm = str(s.get("store_name", "") or s.get("name", "")).lower()
                    for b in _banners_lower:
                        if b and b in _nm:
                            _hits.append(s)
                            break
                if not _hits:
                    st.info(f"No matches found in last scrape of {len(_scraped)} stores.")
                else:
                    st.success(
                        f"Would exclude **{len(_hits)} of {len(_scraped)}** scraped stores "
                        f"({100*len(_hits)/len(_scraped):.1f}%)."
                    )
                    _sample = pd.DataFrame([
                        {"store_name": h.get("store_name") or h.get("name", ""),
                         "city": h.get("city", ""),
                         "category": h.get("category", "")}
                        for h in _hits[:20]
                    ])
                    st.dataframe(_sample, use_container_width=True, hide_index=True)
                    if len(_hits) > 20:
                        st.caption(f"... and {len(_hits) - 20} more")

    st.markdown("---")

    # ── Sales Force Structure (simplified) ───────────────────────────────────
    st.markdown("**Dedicated rep rules** *(optional)*")
    st.caption("Assign specific reps to accounts, channels, or store groups. Remaining stores go to mixed geographic reps.")

    if "sf_rules" not in st.session_state:
        st.session_state["sf_rules"] = []
    _sf_rules = st.session_state["sf_rules"]

    _portfolio_for_rules = st.session_state.get("portfolio_df")
    _STANDARD_COLS = {
        "store_id", "store_name", "address", "city", "lat", "lng",
        "annual_sales_usd", "lines_per_store", "category",
        "district", "area", "neighbourhood", "neighborhood", "bairro",
        "zone", "suburb", "quarter", "region", "state", "governorate",
        "province", "county", "wilaya", "emirate", "prefecture",
    }
    _GENERIC_ACCOUNTS = {
        "others", "other", "independent", "unknown", "n/a", "na", "none",
        "general", "misc", "miscellaneous", "unassigned", "blank", "",
        "general trade", "traditional trade", "open market",
        "retail", "retailer", "dealer", "distributor", "wholesaler",
        "generic", "standard", "local", "local shop", "not applicable",
        "tbd", "to be confirmed", "pending",
    }

    # Build smart match phrases: "Account is Lulu", "Channel is Wholesale", etc.
    _match_phrases = []
    _match_phrase_map = {}
    if _portfolio_for_rules is not None:
        for _col in _portfolio_for_rules.columns:
            if _col in _STANDARD_COLS:
                continue
            _display_col = _col.replace("_", " ").title()
            for _val in sorted(_portfolio_for_rules[_col].dropna().astype(str).str.strip().unique()):
                if _val and _val.strip().lower() not in _GENERIC_ACCOUNTS:
                    _phrase = f"{_display_col} is {_val}"
                    _match_phrases.append(_phrase)
                    _match_phrase_map[_phrase] = {"column": _col, "value": _val, "field": _display_col}
    # Add category options
    _cats_for_rules = final_categories if 'final_categories' in dir() and final_categories else []
    for _cat in _cats_for_rules:
        _phrase = f"Category is {_cat.replace('_',' ').title()}"
        _match_phrases.append(_phrase)
        _match_phrase_map[_phrase] = {"column": "category", "value": _cat, "field": "Category"}
    _match_phrases.append("Store name contains keyword...")

    # Collect geography options — region fences from the coverage file first
    # (clean, coordinate-backed), then any manually-typed scraping scope.
    _region_fences = sorted((st.session_state.get("region_boundaries") or {}).keys())
    _configured_cities = sorted(set(
        [e.get("name","") for e in st.session_state.get("city_entries", []) or []] +
        [e.get("name","") for e in st.session_state.get("region_entries", []) or []]
    ))
    _configured_cities = [c for c in _configured_cities if c and c not in _region_fences]
    _geo_options = ["All"] + _region_fences + _configured_cities

    # Display existing rules
    if _sf_rules:
        for idx, rule in enumerate(_sf_rules):
            _geo_display = ", ".join(rule.get("geography", ["All"]))
            _conds = rule.get("match_conditions", [])
            if _conds:
                _desc = " OR ".join(f'{c.get("match_field","")}: {c.get("match_value","")}' for c in _conds)
            else:
                _desc = f'{rule.get("match_field","")}: {rule.get("match_value","")}'
            _reps_display = "Auto" if rule.get("dedicated_reps", 1) == 0 else f'{rule.get("dedicated_reps", 1)} rep(s)'
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid #1565C0;'
                f'border-radius:8px;padding:10px 14px;margin:5px 0;font-size:0.88rem">'
                f'<strong>{rule.get("rule_name","")}</strong> — {_desc} — '
                f'Geography: {_geo_display} — <strong>{_reps_display}</strong></div>',
                unsafe_allow_html=True)
        _del_cols = st.columns(min(len(_sf_rules), 5))
        for idx, rule in enumerate(_sf_rules):
            with _del_cols[idx % 5]:
                if st.button(f"Remove: {rule.get('rule_name','')}", key=f"del_rule_{idx}"):
                    _sf_rules.pop(idx)
                    st.session_state["sf_rules"] = _sf_rules
                    st.rerun()

    # Add new rule
    with st.expander("+ Add dedicated rep rule", expanded=len(_sf_rules) == 0):
        _new_rule_name = st.text_input("Rule name", placeholder="e.g., Lulu Exclusive", key="new_rule_name")

        if "rule_conditions_count" not in st.session_state:
            st.session_state["rule_conditions_count"] = 1
        _n_cond = st.session_state["rule_conditions_count"]

        _conditions_data = []
        for i in range(_n_cond):
            _label = "Match stores where" if i == 0 else f"OR match #{i+1}"
            _cond_c1, _cond_c2 = st.columns([3, 1])
            with _cond_c1:
                _sel_phrase = st.selectbox(_label, _match_phrases if _match_phrases else ["Store name contains keyword..."],
                    key=f"cond_match_on_{i}")
            with _cond_c2:
                if _sel_phrase == "Store name contains keyword...":
                    _ci_value = st.text_input("Keyword", placeholder="e.g., Lulu", key=f"cond_value_txt_{i}")
                    _ci_col = "store_name"
                    _ci_field = "Store name"
                else:
                    _mapped = _match_phrase_map.get(_sel_phrase, {})
                    _ci_value = _mapped.get("value", "")
                    _ci_col = _mapped.get("column", "store_name")
                    _ci_field = _mapped.get("field", "")
                    st.text_input("Value", value=_ci_value, disabled=True, key=f"cond_value_sel_{i}")

            if _n_cond > 1 and i == _n_cond - 1:
                if st.button("Remove condition", key=f"cond_remove_{i}"):
                    st.session_state["rule_conditions_count"] = max(1, _n_cond - 1)
                    st.rerun()

            _conditions_data.append({
                "match_field": _ci_field,
                "match_column": _ci_col,
                "match_value": str(_ci_value).strip(),
            })

        if st.button("+ Add another condition (OR)", key="btn_add_cond"):
            st.session_state["rule_conditions_count"] = _n_cond + 1
            st.rerun()

        _rc1, _rc2, _rc3 = st.columns(3)
        with _rc1:
            _new_geography = st.multiselect("Geography", _geo_options, default=["All"], key="new_geography")
        with _rc2:
            _new_size_filter = st.multiselect("Size tier filter", ["Large","Medium","Small"],
                default=["Large","Medium","Small"], key="new_size_filter",
                help="Filters scraped stores only. Portfolio stores always included.")
        with _rc3:
            _rep_options = ["Auto (recommended)"] + [str(i) for i in range(1, 21)]
            _rep_choice = st.selectbox("Dedicated reps", _rep_options, key="new_dedicated_reps",
                help="Auto = system calculates based on workload. Or pick a fixed number.")
            _new_ded_reps = 0 if _rep_choice == "Auto (recommended)" else int(_rep_choice)

        if st.button("Add rule", type="primary", key="btn_add_rule"):
            _valid_conds = [c for c in _conditions_data if c["match_value"]]
            if not _new_rule_name.strip():
                st.error("Please enter a rule name.")
            elif not _valid_conds:
                st.error("Please select or enter a match value.")
            else:
                _channel_cols = {"channel", "trade_channel", "sub_channel", "trade_type", "segment", "category"}
                _first_col = _valid_conds[0]["match_column"]
                _rule_type = "Channel" if _first_col in _channel_cols else "Customer"
                _new_rule = {
                    "rule_name":        _new_rule_name.strip(),
                    "rule_type":        _rule_type,
                    "match_conditions": _valid_conds,
                    "match_type":       "Contains",
                    "geography":        _new_geography if "All" not in _new_geography else ["All"],
                    "size_filter":      _new_size_filter if _new_size_filter else ["Large","Medium","Small"],
                    "dedicated_reps":   _new_ded_reps,
                    "match_field":      _valid_conds[0]["match_field"],
                    "match_column":     _valid_conds[0]["match_column"],
                    "match_value":      _valid_conds[0]["match_value"],
                }
                _sf_rules.append(_new_rule)
                _sf_rules.sort(key=lambda r: 0 if r.get("rule_type") == "Channel" else 1)
                st.session_state["sf_rules"] = _sf_rules
                st.session_state["rule_conditions_count"] = 1
                st.success(f"Rule added: {_new_rule_name}")
                st.rerun()

    # Numeric distribution % (recommended mode only)
    if rep_mode_key == "recommended":
        st.markdown("---")
        st.markdown("**Store selection for routing**")
        _store_select_pct = st.slider("Top N% of stores included in routing",
            min_value=10, max_value=100, value=60, step=5, key="store_select_pct_input",
            help="Higher = more stores routed, more reps needed. Lower = focus on top stores.")
    else:
        _store_select_pct = 100

    # Summary
    _n_dedicated = sum(r.get("dedicated_reps", 1) if r.get("dedicated_reps", 1) > 0 else 1 for r in _sf_rules)
    if _sf_rules:
        _auto_count = sum(1 for r in _sf_rules if r.get("dedicated_reps", 1) == 0)
        _info = f"**{len(_sf_rules)} rule(s)** · ~{_n_dedicated} dedicated rep(s)"
        if _auto_count:
            _info += f" ({_auto_count} on Auto)"
        if rep_mode_key == "fixed":
            _mixed = max(0, int(rep_count) - _n_dedicated)
            _info += f" · **{_mixed} mixed reps** remaining"
            if _mixed <= 0:
                st.error(f"Dedicated rules need ~{_n_dedicated} reps but total is {int(rep_count)}. Increase total reps.")
        st.info(_info)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: VISIT PLAYBOOK
# ═══════════════════════════════════════════════════════════════════════════════
with tab_playbook:
    # Market name & API key
    country_name = st.session_state.get("country_name", "")
    col1, col2 = st.columns(2)
    with col1:
        market_name = st.text_input("Market name",
            value=f"{country_name} - {final_scope}" if final_scope else country_name)
    with col2:
        market_api_key = st.text_input("Google API key (optional)", type="password",
            placeholder="Leave blank to use global admin key")

    st.markdown("---")

    # Route start month
    import datetime as _dt
    st.markdown("**Route plan start month**")
    _today = _dt.date.today()
    _col_m, _col_y = st.columns(2)
    with _col_m:
        route_month = st.selectbox("Start month", options=list(range(1, 13)),
            index=_today.month - 1,
            format_func=lambda m: _dt.date(2025, m, 1).strftime("%B"),
            key="route_month_sel")
    with _col_y:
        route_year = st.number_input("Start year", min_value=2024, max_value=2030,
            value=_today.year, key="route_year_sel")

    st.markdown("---")

    # Visit benchmarks
    st.markdown("**Visit frequency & duration per category**")

    admin_defaults = st.session_state.get("admin_benchmarks", {
        "large_pct": 20, "medium_pct": 60, "small_pct": 20,
        "large_visits": 4, "medium_visits": 2, "small_visits": 1,
        "large_duration": 40, "medium_duration": 25, "small_duration": 15,
    })

    # ── Bulk import / export of the visit playbook via CSV ──────────────────
    # Saves users from clicking through 80 number_input widgets every session.
    # Pure data flow: reads the CSV rows, writes lv_/ld_/mv_/md_/sv_/sd_ keys
    # into session_state before the widgets render below — same path the
    # manual inputs use. No logic change.
    with st.expander("Bulk import/export the visit playbook (CSV)"):
        st.caption(
            "Download a template, fill in visits/month and duration per category "
            "in Excel, upload back here. Faster than clicking through every "
            "number field for 20 categories. Columns: category, large_visits, "
            "large_duration, medium_visits, medium_duration, small_visits, small_duration."
        )
        # Build a template populated with whatever the user currently has so
        # they can edit instead of starting blank.
        _scrape_cats_t = final_categories if 'final_categories' in dir() and final_categories else []
        _portfolio_cats_t = []
        _pf_t = st.session_state.get("portfolio_df")
        if _pf_t is not None and "category" in _pf_t.columns:
            _pf_cats_t = _pf_t["category"].dropna().astype(str).str.strip().str.lower().unique().tolist()
            _portfolio_cats_t = [c for c in _pf_cats_t if c and c not in _scrape_cats_t]
        _cats_template = sorted(set(_scrape_cats_t + _portfolio_cats_t))
        if _cats_template:
            _tmpl_rows = []
            for _c in _cats_template:
                _tmpl_rows.append({
                    "category":         _c,
                    "large_visits":     st.session_state.get(f"lv_{_c}",  admin_defaults.get("large_visits", 4)),
                    "large_duration":   st.session_state.get(f"ld_{_c}",  admin_defaults.get("large_duration", 40)),
                    "medium_visits":    st.session_state.get(f"mv_{_c}",  admin_defaults.get("medium_visits", 2)),
                    "medium_duration":  st.session_state.get(f"md_{_c}",  admin_defaults.get("medium_duration", 25)),
                    "small_visits":     st.session_state.get(f"sv_{_c}",  admin_defaults.get("small_visits", 1)),
                    "small_duration":   st.session_state.get(f"sd_{_c}",  admin_defaults.get("small_duration", 15)),
                })
            _tmpl_df = pd.DataFrame(_tmpl_rows)
            st.download_button(
                "  Download visit-playbook template (CSV)",
                "﻿" + _tmpl_df.to_csv(index=False),
                file_name="visit_playbook_template.csv",
                mime="text/csv",
                key="pb_template_dl",
            )
        else:
            st.info("Define at least one scrape category or upload a portfolio first, then a template will appear here.")

        # Show a persistent success banner after the rerun that the apply triggers
        _pb_just_applied = st.session_state.pop("_pb_just_applied", None)
        if _pb_just_applied:
            st.success(
                f"  Applied **{_pb_just_applied}** playbook values from your CSV. "
                "Scroll down to the per-category table to confirm — every number_input "
                "below should now show the values you uploaded."
            )

        # Rotating nonce key so the uploader is empty on the next rerun.
        # Otherwise the apply block fires again, calls st.rerun() again, and
        # the page enters an infinite blink-loop.
        _pb_nonce = st.session_state.get("_pb_upload_nonce", 0)
        _pb_upload = st.file_uploader(
            "Upload visit-playbook CSV",
            type=["csv"],
            key=f"pb_csv_upload_{_pb_nonce}",
            label_visibility="collapsed",
        )
        if _pb_upload is not None:
            try:
                _pb_df = pd.read_csv(_pb_upload)
                _pb_df.columns = [str(c).strip().lower().replace(" ", "_") for c in _pb_df.columns]
                if "category" not in _pb_df.columns:
                    st.error("CSV must have a 'category' column.")
                else:
                    _applied = 0
                    _mapping = {
                        "lv": "large_visits",   "ld": "large_duration",
                        "mv": "medium_visits",  "md": "medium_duration",
                        "sv": "small_visits",   "sd": "small_duration",
                    }
                    for _r in _pb_df.to_dict("records"):
                        _cat = str(_r.get("category", "") or "").strip().lower()
                        if not _cat:
                            continue
                        for _prefix, _col in _mapping.items():
                            if _col in _pb_df.columns:
                                _v = _r.get(_col)
                                if _v is None: continue
                                try:
                                    _vv = float(_v) if _prefix in ("lv","mv","sv") else int(float(_v))
                                except (TypeError, ValueError):
                                    continue
                                st.session_state[f"{_prefix}_{_cat}"] = _vv
                                _applied += 1
                    if _applied:
                        # Rotate the nonce so the uploader is empty on rerun and the
                        # apply block doesn't fire again.
                        st.session_state["_pb_upload_nonce"] = _pb_nonce + 1
                        st.session_state["_pb_just_applied"] = _applied
                        st.rerun()
                    else:
                        st.warning("No values applied — check your CSV columns and category names.")
            except Exception as _e:
                st.error(f"Could not read CSV: {_e}")

    st.caption(
        f"Size splits: Large = top {admin_defaults.get('large_pct',20)}% · "
        f"Medium = middle {admin_defaults.get('medium_pct',60)}% · "
        f"Small = bottom {admin_defaults.get('small_pct',20)}% "
        f"(change in Admin Settings)"
    )

    # Preset buttons
    _preset_col1, _preset_col2, _preset_col3 = st.columns(3)
    with _preset_col1:
        _preset_std = st.button("Standard FMCG", key="preset_std",
            help="Large: 4 visits/40min · Medium: 2/25min · Small: 1/15min")
    with _preset_col2:
        _preset_pharma = st.button("Pharmacy focus", key="preset_pharma",
            help="Large: 3 visits/30min · Medium: 2/20min · Small: 1/15min")
    with _preset_col3:
        _preset_premium = st.button("Premium retail", key="preset_premium",
            help="Large: 4 visits/50min · Medium: 3/35min · Small: 2/20min")

    if _preset_std:
        admin_defaults.update({"large_visits":4,"large_duration":40,"medium_visits":2,"medium_duration":25,"small_visits":1,"small_duration":15})
    elif _preset_pharma:
        admin_defaults.update({"large_visits":3,"large_duration":30,"medium_visits":2,"medium_duration":20,"small_visits":1,"small_duration":15})
    elif _preset_premium:
        admin_defaults.update({"large_visits":4,"large_duration":50,"medium_visits":3,"medium_duration":35,"small_visits":2,"small_duration":20})

    visit_benchmarks = {}
    _scrape_cats = final_categories if 'final_categories' in dir() and final_categories else []

    # Detect portfolio categories (from uploaded CSV)
    _portfolio_cats = []
    _pf_for_bench = st.session_state.get("portfolio_df")
    if _pf_for_bench is not None and "category" in _pf_for_bench.columns:
        _pf_raw_cats = _pf_for_bench["category"].dropna().astype(str).str.strip().str.lower().unique().tolist()
        _pf_raw_cats = [c for c in _pf_raw_cats if c and c not in _scrape_cats]
        _portfolio_cats = sorted(set(_pf_raw_cats))

    _cats_for_bench = _scrape_cats + _portfolio_cats
    if _cats_for_bench:
        hc0,hc1,hc2,hc3,hc4,hc5,hc6 = st.columns([2,1,1,1,1,1,1])
        hc0.markdown("**Sub-channel**")
        hc1.markdown("**Large visits/mo**")
        hc2.markdown("**Large min**")
        hc3.markdown("**Medium visits/mo**")
        hc4.markdown("**Medium min**")
        hc5.markdown("**Small visits/mo**")
        hc6.markdown("**Small min**")
        st.caption("Decimals for less-than-monthly: 0.5 = every 2 months · 0.33 = quarterly")

        if _portfolio_cats:
            st.caption(f"Showing {len(_scrape_cats)} scraping categories + {len(_portfolio_cats)} portfolio categories")

        _all_min_freq = []
        for cat in _cats_for_bench:
            _is_portfolio_cat = cat in _portfolio_cats
            cat_label = cat.replace("_"," ").title()
            if _is_portfolio_cat:
                cat_label += " (portfolio)"
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

        if _all_min_freq:
            min_freq = min(_all_min_freq)
            plan_period = max(1, round(1 / min_freq)) if min_freq < 1 else 1
            st.info(f"Plan period: **{plan_period} month{'s' if plan_period > 1 else ''}** (driven by min frequency {min_freq}/month)")
    else:
        st.info("Select categories in the Market Area tab first.")
        visit_benchmarks = {}

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
total = 100

issues = []
if not st.session_state.get("country_name"):
    issues.append("Select a country in the Market Area tab.")
if not final_bbox:
    issues.append("Add at least one city or region.")
_cats_check = final_categories if 'final_categories' in dir() else []
if not _cats_check:
    issues.append("Select at least one scraping category.")

if issues:
    for issue in issues:
        st.warning(issue)
else:
    if st.button("Save & continue to pipeline", type="primary"):
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
            "categories":              _cats_check,
            "market_api_key":          market_api_key,
            "detected_from_portfolio": detected_categories,
            "visit_benchmarks":        visit_benchmarks,
            "plan_period":             max(1, round(1/min(min(v.get("large_visits",4), v.get("medium_visits",2), v.get("small_visits",1)) for v in visit_benchmarks.values())) if visit_benchmarks else 1),
            "size_percentiles":        admin_defaults,
            "route_month":             int(route_month),
            "route_year":              int(route_year),
            "weights": {k: v/100 for k,v in st.session_state.get("admin_scoring_weights",
                {"rating":20,"reviews":25,"affluence":15,"poi":15,"sales":15,"lines":10}).items()},
            "weights_gap": {k: v/100 for k,v in st.session_state.get("admin_scoring_weights_gap",
                {"rating":25,"reviews":25,"affluence":25,"poi":25}).items()},
            "sf_rules":                st.session_state.get("sf_rules", []),
            "store_select_pct":        _store_select_pct,
            "region_boundaries":       st.session_state.get("region_boundaries", {}),
        }
        st.markdown(f"""
        <div style="background:#E8F5E9;border:1.5px solid #66BB6A;border-left:5px solid #2E7D32;
        border-radius:8px;padding:1rem 1.4rem;margin:0.5rem 0">
            <div style="font-weight:700;color:#1B5E20;font-size:1rem;margin-bottom:4px">
                Configuration saved — {market_name}
            </div>
            <div style="color:#2E7D32;font-size:0.87rem">
                Go to <strong>Run Pipeline</strong> in the sidebar to start the pipeline.
            </div>
        </div>
        """, unsafe_allow_html=True)

if st.session_state.get("market_config"):
    with st.expander("View saved configuration"):
        cfg = dict(st.session_state["market_config"])
        cfg.pop("market_api_key", None)
        st.json(cfg)
