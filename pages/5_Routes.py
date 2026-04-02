import streamlit as st
import ast
import pandas as pd
import json
import datetime
import math

def _hav_min(lat1, lng1, lat2, lng2, speed_kmh=30):
    """Straight-line travel time in minutes between two GPS points."""
    R = 6371000
    p = math.pi / 180
    a = (math.sin((lat2-lat1)*p/2)**2 +
         math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lng2-lng1)*p/2)**2)
    dist_km = 2 * R * math.asin(math.sqrt(a)) / 1000
    return (dist_km / speed_kmh) * 60

st.set_page_config(page_title="Routes - Coverage Tool", page_icon=" ", layout="wide")

st.markdown("""
<style>

/* ── Sidebar navy blue ── */
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #FFFFFF !important; }
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
.rep-chip {
    padding: 10px 16px; border-radius: 8px; color: white;
    text-align: center; font-weight: 700; margin: 4px; font-size: 0.85rem; display: inline-block;
}
.day-chip {
    padding: 6px 14px; border-radius: 20px; color: white;
    font-weight: 700; font-size: 0.82rem; display: inline-block; margin: 3px;
}



.legend-chip {
    display: inline-block; padding: 5px 14px; border-radius: 20px;
    color: white; font-size: 0.8rem; font-weight: 600; margin: 3px;
}
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white; border-radius: 6px; font-weight: 600;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("run_results"):
    st.warning("No results yet. Run the pipeline first.")
    st.stop()

res        = st.session_state["run_results"]
all_stores = res["all_stores"]
market     = st.session_state.get("last_market", "Market")
cfg        = st.session_state.get("market_config", {})

route_year   = cfg.get("route_year",   datetime.date.today().year)
route_month1 = cfg.get("route_month1", datetime.date.today().month)

# Get 2-month plan labels from session state
plan_months = st.session_state.get("route_plan_months", {})
m1_name = plan_months.get("month1", datetime.date(route_year, route_month1, 1).strftime("%B %Y"))
m2_idx  = route_month1 % 12 + 1
m2_year = route_year + (1 if m2_idx == 1 else 0)
m2_name = plan_months.get("month2", datetime.date(m2_year, m2_idx, 1).strftime("%B %Y"))
m1_key  = plan_months.get("m1_key", datetime.date(route_year, route_month1, 1).strftime("%b").lower())
m2_key  = plan_months.get("m2_key", datetime.date(m2_year, m2_idx, 1).strftime("%b").lower())

PLAN_MONTHS      = plan_months.get("month_labels", [m1_name, m2_name])
PLAN_MONTH_KEYS  = plan_months.get("month_keys",   [m1_key,  m2_key])
MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]
MONTH_SHORT = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]

plan_period = plan_months.get("plan_period", len(PLAN_MONTHS))
plan_label  = " + ".join(PLAN_MONTHS)
st.html(f"""
<div class="page-header">
    <h2>  Rep Routes</h2>
    <p>Market: {market} &nbsp;·&nbsp; {plan_period}-month plan: {plan_label}</p>
</div>
""")



REP_COLORS = [
    [21,101,192],[46,125,50],[230,81,0],[136,14,79],[0,96,100],
    [74,20,140],[183,28,28],[0,77,64],[62,39,35],[38,50,56]
]
DAY_COLORS = {
    "Monday":    "#1565C0",
    "Tuesday":   "#2E7D32",
    "Wednesday": "#E65100",
    "Thursday":  "#6A1B9A",
    "Friday":    "#00695C",
}
STATUS_COLORS = {"covered":[46,125,50,200],"gap":[198,40,40,220]}
SIZE_COLORS   = {"Large":[46,125,50,220],"Medium":[21,101,192,220],"Small":[245,127,23,220]}

def get_color(s, colour_by):
    if colour_by == "Rep route":
        c = REP_COLORS[(s.get("rep_id",0) or 0) % len(REP_COLORS)]
        return [c[0],c[1],c[2],200]
    elif colour_by == "Day of week":
        day = s.get("assigned_day","")
        dc  = {"Monday":[21,101,192,220],"Tuesday":[46,125,50,220],
               "Wednesday":[230,81,0,220],"Thursday":[136,14,79,220],"Friday":[0,96,100,220]}
        return dc.get(day,[150,150,150,180])
    elif colour_by == "Size tier":
        return SIZE_COLORS.get(s.get("size_tier",""),[150,150,150,180])
    elif colour_by == "Coverage status":
        return STATUS_COLORS.get(s.get("coverage_status","covered"),[150,150,150,180])
    else:
        sc = s.get("score",0)
        if sc>=80: return [46,125,50,220]
        if sc>=60: return [21,101,192,220]
        if sc>=40: return [245,127,23,220]
        return [198,40,40,200]

# ── FILTERS ───────────────────────────────────────────────────────────────────
all_reps  = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))
# Build date list from actual visit dates in the selected month
def parse_dates_val(val):
    """Parse a date value — handles real lists and stringified lists from CSV."""
    if val is None or (isinstance(val, float)): return []
    if isinstance(val, list): return [str(d).strip() for d in val if d]
    s = str(val).strip()
    if not s or s == "nan" or s == "[]": return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list): return [str(d).strip() for d in parsed if d]
    except Exception: pass



    s = s.strip("[]").replace("'","").replace('"',"")
    return [d.strip() for d in s.split(",") if d.strip()]

def get_dates_for_month(stores, month_key):
    """Get all unique real calendar dates for a given month key (e.g. 'm1').
    Reads {month_key}_dates column, e.g. m1_dates = ['07 Apr', '14 Apr', ...]"""
    import datetime
    dates_set = set()
    col = f"{month_key}_dates"   # always m1_dates, m2_dates etc.
    for s in stores:
        for d in parse_dates_val(s.get(col, [])):
            if d and str(d).strip() not in ("", "nan"):
                dates_set.add(str(d).strip())
    def date_sort(d):
        for fmt in ("%d %b", "%d %B", "%b %d"):
            try: return datetime.datetime.strptime(d.strip(), fmt)
            except: pass
        return datetime.datetime.max
    return ["All dates"] + sorted(dates_set, key=date_sort)

all_days = ["Full month"] + ["Monday","Tuesday","Wednesday","Thursday","Friday"]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    colour_by = st.selectbox("Colour by", ["Rep route","Day of week","Size tier","Coverage status","Score"])
with col2:
    sel_rep = st.selectbox("Rep", ["All reps"] + [f"Rep {r}" for r in all_reps])
with col3:
    sel_month = st.selectbox("Month", ["Full plan"] + PLAN_MONTHS)
with col4:
    if sel_month != "Full plan" and sel_month in PLAN_MONTHS:
        _mkey  = PLAN_MONTH_KEYS[PLAN_MONTHS.index(sel_month)]
        _dates = get_dates_for_month(all_stores, _mkey)
        sel_day = st.selectbox("Date", _dates)
    else:
        sel_day = st.selectbox("Date", ["All dates"])
with col5:
    show_gaps    = st.checkbox("Show gap stores",    value=True)
    show_covered = st.checkbox("Show covered stores",value=True)

# Resolve selected month key
sel_month_key = None
if sel_month != "Full plan":
    idx = PLAN_MONTHS.index(sel_month) if sel_month in PLAN_MONTHS else -1
    sel_month_key = PLAN_MONTH_KEYS[idx] if idx >= 0 else None

# Map base filter respects route_filter selection



_map_route_filter = st.session_state.get("tbl_route_filter", "Recommended stores")
if _map_route_filter == "Recommended stores":
    map_stores = [s for s in all_stores if s.get("lat") and s.get("lng") and s.get("plan_visits",0) > 0]
elif _map_route_filter == "Not in route":
    map_stores = [s for s in all_stores if s.get("lat") and s.get("lng") and s.get("plan_visits",0) == 0]
else:
    map_stores = [s for s in all_stores if s.get("lat") and s.get("lng")]
if sel_rep != "All reps":
    rep_num    = int(sel_rep.split()[1])
    map_stores = [s for s in map_stores if s.get("rep_id") == rep_num]
# Month filter — only stores with visits in that month
if sel_month_key:
    map_stores = [s for s in map_stores if s.get(f"{sel_month_key}_visits",0) > 0]
# Date filter — match against real calendar dates in mk_dates
if sel_day not in ("Full month", "All dates", "All weeks", "") and sel_month_key:
    map_stores = [s for s in map_stores
                  if sel_day in parse_dates_val(s.get(f"{sel_month_key}_dates", []))]
elif sel_day not in ("Full month", "All dates", "All weeks", "") and not sel_month_key:
    map_stores = [s for s in map_stores
                  if sel_day.split("-")[-1].strip() == s.get("assigned_day","").strip()]
if not show_gaps:
    map_stores = [s for s in map_stores if s.get("coverage_status") != "gap"]
if not show_covered:
    map_stores = [s for s in map_stores if not s.get("covered")]

st.caption(f"Showing {len(map_stores):,} stores on map")

# ── MAP ───────────────────────────────────────────────────────────────────────
map_data = [{
    "lat":s["lat"],"lng":s["lng"],
    "name":s.get("store_name",""),
    "score":s.get("score",0),
    "size_tier":s.get("size_tier",""),
    "annual_visits":s.get("annual_visits",0),
    "status":s.get("coverage_status",""),
    "rep":s.get("rep_id",0),
    "day":s.get("assigned_day",""),
    "order":s.get("day_visit_order",0),
    "color":get_color(s, colour_by),
    "radius":max(30,s.get("score",0)*1.5),
} for s in map_stores]

try:
    import pydeck as pdk
    df_map = pd.DataFrame(map_data)
    if not df_map.empty:
        layer = pdk.Layer("ScatterplotLayer", data=df_map,



            get_position="[lng, lat]", get_color="color", get_radius="radius",
            radius_min_pixels=4, radius_max_pixels=20, pickable=True)
        view = pdk.ViewState(latitude=df_map["lat"].mean(), longitude=df_map["lng"].mean(), zoom=11, pitch=0)
        tooltip = {
            "html":"<b>{name}</b><br/>Score: <b>{score}</b><br/>Size: {size_tier}<br/>"
                   "Annual visits: {annual_visits}<br/>Day: {day}<br/>Visit order: {order}<br/>"
                   "Rep: {rep}",
            "style":{"backgroundColor":"#1A2B4A","color":"white","padding":"10px","borderRadius":"8px","fontSize":"13px"}
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    else:
        st.info("No stores match the current filters.")
except ImportError:
    if map_data:
        df_map = pd.DataFrame(map_data)
        st.map(df_map.rename(columns={"lng":"lon"})[["lat","lon"]])

# ── LEGEND ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Legend</div>', unsafe_allow_html=True)
if colour_by == "Rep route":
    reps = sorted(set(s.get("rep_id",0) for s in map_stores if s.get("rep_id")))
    if reps:
        # Show all reps in rows of 5
        n_per_row = 5
        for row_start in range(0, len(reps), n_per_row):
            row_reps = reps[row_start:row_start + n_per_row]
            cols     = st.columns(len(row_reps))
            for i, rep in enumerate(row_reps):
                rs        = [s for s in all_stores if s.get("rep_id")==rep and s.get("plan_visits",0)>0]
                plan_n    = len(rs)
                visits_mo = sum(s.get("visits_per_month",0) for s in rs)
                c         = REP_COLORS[rep % len(REP_COLORS)]
                hx        = "#{:02x}{:02x}{:02x}".format(c[0],c[1],c[2])
                cols[i].markdown(
                    f'<div style="background:{hx};border-radius:8px;padding:8px 12px;color:white;text-align:center;margin:3px">'                    f'<div style="font-weight:700;font-size:0.85rem">Rep {rep}</div>'                    f'<div style="font-size:0.75rem;margin-top:3px;opacity:0.9">'                    f'Plan stores: {plan_n} &nbsp;·&nbsp; Visits/mo: {visits_mo:.0f}'                    f'</div></div>',
                    unsafe_allow_html=True)
elif colour_by == "Day of week":
    lc = st.columns(5)
    for i,(day,col) in enumerate(DAY_COLORS.items()):
        ds = [s for s in map_stores if s.get("assigned_day")==day]
        lc[i].markdown(
            f'<span class="legend-chip" style="background:{col}">{day} · {len(ds)} stores</span>',
            unsafe_allow_html=True)
elif colour_by == "Size tier":
    lc = st.columns(3)
    for i,(tier,col) in enumerate([("Large","#2E7D32"),("Medium","#1565C0"),("Small","#F57F17")]):
        cnt = len([s for s in map_stores if s.get("size_tier")==tier])



        lc[i].markdown(f'<span class="legend-chip" style="background:{col}">{tier} · {cnt} stores</span>',unsafe_allow_html=True)
elif colour_by == "Coverage status":
    lc = st.columns(2)
    cov = len([s for s in map_stores if s.get("coverage_status")=="covered"])
    gap = len([s for s in map_stores if s.get("coverage_status")=="gap"])
    lc[0].markdown(f'<span class="legend-chip" style="background:#2E7D32">Covered · {cov}</span>',unsafe_allow_html=True)
    lc[1].markdown(f'<span class="legend-chip" style="background:#C62828">Gap · {gap}</span>',unsafe_allow_html=True)

st.markdown("---")

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Download rep route files</div>', unsafe_allow_html=True)
st.caption("Each file includes store details, assigned day, visit dates, visit order and coordinates.")

mkt_safe = market.replace(" ","_").replace("-","_")

def build_rep_df(stores, rep_id=None, day=None, month_key=None):
    # For "Not in route" / "All stores" views, include all stores passed in
    # rep_id filter only applied when a specific rep is selected
    filtered = list(stores)
    if rep_id:
        filtered = [s for s in filtered if s.get("rep_id") == rep_id]
    if month_key and day and day not in ("Full month", "All dates", "All weeks", ""):
        # Filter by real calendar date e.g. "07 Apr"
        filtered = [s for s in filtered
                    if day in parse_dates_val(s.get(f"{month_key}_dates", []))]
    elif month_key:
        filtered = [s for s in filtered if s.get(f"{month_key}_visits",0) > 0]
    elif day and day not in ("Full month", "All dates", "All weeks", ""):
        day_name = day.split("-")[-1].strip()
        filtered = [s for s in filtered if s.get("assigned_day","").strip() == day_name]
    if not filtered:
        return pd.DataFrame()
    filtered = sorted(filtered, key=lambda x: (x.get("assigned_day",""), x.get("day_visit_order",99)))
    rows = []
    for s in filtered:
        row = {
            "rep_id":             s.get("rep_id"),
            "assigned_day":       s.get("assigned_day",""),
            "day_visit_order":    s.get("day_visit_order",0),
            "store_name":         s.get("store_name",""),
            "category":           s.get("category",""),
            "size_tier":          s.get("size_tier",""),
            "score":              s.get("score",0),
            "visits_per_month":   s.get("visits_per_month",0),
            "annual_visits":      s.get("annual_visits",0),
            "visit_duration_min": s.get("visit_duration_min",0),



            "coverage_status":    s.get("coverage_status",""),
            "rating":             s.get("rating",0),
            "review_count":       s.get("review_count",0),
            "phone":              s.get("phone",""),
            "opening_hours":      s.get("opening_hours",""),
            "address":            s.get("address",""),
            "city":               s.get("city",""),
            "lat":                s.get("lat",""),
            "lng":                s.get("lng",""),
        }
        # Add only plan month columns
        for mk in PLAN_MONTH_KEYS:
            row[f"{mk}_dates"]  = ", ".join(parse_dates_val(s.get(f"{mk}_dates", [])))
            row[f"{mk}_visits"] = s.get(f"{mk}_visits", 0)
        row["plan_visits"] = s.get("plan_visits", 0)
        rows.append(row)
    return pd.DataFrame(rows)

if all_reps:
    all_df = build_rep_df(all_stores)
    if not all_df.empty:
        st.download_button("  Download all reps — full month CSV",
            all_df.to_csv(index=False), f"all_reps_{mkt_safe}.csv", "text/csv", key="dl_all")

    st.markdown("**Individual rep files:**")
    n_cols   = min(len(all_reps), 4)
    rep_cols = st.columns(n_cols)
    for i, rep in enumerate(all_reps):
        rep_df = build_rep_df(all_stores, rep_id=rep)
        if rep_df.empty:
            continue
        tv = rep_df["visits_per_month"].sum() if "visits_per_month" in rep_df.columns else 0
        c  = REP_COLORS[rep % len(REP_COLORS)]
        hx = "#{:02x}{:02x}{:02x}".format(c[0],c[1],c[2])
        with rep_cols[i % n_cols]:
            st.markdown(f"""
            <div style="background:{hx}18;border:1.5px solid {hx};border-radius:8px;
            padding:10px 12px;margin-bottom:8px;text-align:center">
                <div style="font-weight:700;color:#1A2B4A">Rep {rep}</div>
                <div style="font-size:0.78rem;color:#6B7280">{len(rep_df)} stores · {tv:.0f} visits/mo</div>
            </div>""", unsafe_allow_html=True)
            st.download_button(f"  Rep {rep} CSV",
                rep_df.to_csv(index=False), f"rep_{rep}_{mkt_safe}.csv", "text/csv", key=f"dl_rep_{rep}")

st.markdown("---")

# ── ROUTE DETAIL TABLE ────────────────────────────────────────────────────────



st.markdown('<div class="section-title">Route detail</div>', unsafe_allow_html=True)
st.caption("Select a rep and day to see the exact stores and visit order for that day.")

col_r, col_m, col_d, col_f = st.columns(4)
with col_r:
    tbl_rep = st.selectbox("Rep", ["All reps"] + [f"Rep {r}" for r in all_reps], key="tbl_rep")
with col_m:
    tbl_month = st.selectbox("Month", ["Full plan"] + PLAN_MONTHS, key="tbl_month")
with col_d:
    if tbl_month != "Full plan" and tbl_month in PLAN_MONTHS:
        _tbl_mkey  = PLAN_MONTH_KEYS[PLAN_MONTHS.index(tbl_month)]
        _tbl_dates = get_dates_for_month(all_stores, _tbl_mkey)
        tbl_day    = st.selectbox("Date", _tbl_dates, key="tbl_day")
    else:
        if tbl_month != "Full plan" and tbl_month in PLAN_MONTHS:
            _tbl_mk   = PLAN_MONTH_KEYS[PLAN_MONTHS.index(tbl_month)]
            _tbl_dates = get_dates_for_month(all_stores, _tbl_mk)
        else:
            _tbl_dates = ["All dates"]
        tbl_day = st.selectbox("Date", _tbl_dates, key="tbl_day")
with col_f:
    route_filter = st.selectbox("Route status",
        ["Recommended stores", "Not in route", "All stores"], key="tbl_route_filter")

tbl_rep_id    = int(tbl_rep.split()[1]) if tbl_rep != "All reps" else None
if tbl_month != "Full plan" and tbl_month in PLAN_MONTHS:
    tbl_month_key = PLAN_MONTH_KEYS[PLAN_MONTHS.index(tbl_month)]
else:
    tbl_month_key = None

# Apply route status filter
if route_filter == "Recommended stores":
    _tbl_src = [s for s in all_stores if s.get("plan_visits",0) > 0]
elif route_filter == "Not in route":
    _tbl_src = [s for s in all_stores if s.get("plan_visits",0) == 0]
else:
    _tbl_src = all_stores

display_df    = build_rep_df(_tbl_src, rep_id=tbl_rep_id,
    day=tbl_day if tbl_day != "Full month" else None,
    month_key=tbl_month_key)

# When a specific day is selected, trim table to stores that fit within daily budget
cfg_tbl   = st.session_state.get("market_config", {})
daily_cap = cfg_tbl.get("daily_minutes", 480)

# When a specific date is selected, sort by visit order — already within budget



if not display_df.empty and tbl_day not in ("Full month", "All dates", "All weeks", "") and "visit_duration_min" in display_df.columns:
    display_df = display_df.sort_values("day_visit_order").reset_index(drop=True)

if not display_df.empty:
    base_cols = ["rep_id","assigned_day","day_visit_order","store_name","category",
                 "size_tier","score","visits_per_month","annual_visits","visit_duration_min",
                 "coverage_status","rating","review_count","phone","opening_hours",
                 "address","city","lat","lng"]
    # Add month columns if viewing a specific month
    if tbl_month_key:
        month_cols = [f"{tbl_month_key}_dates", f"{tbl_month_key}_visits"]
        base_cols  = base_cols[:4] + month_cols + base_cols[4:]
    else:
        base_cols = base_cols + [f"{mk}_dates" for mk in PLAN_MONTH_KEYS] + [f"{mk}_visits" for mk in PLAN_MONTH_KEYS] + ["plan_visits"]
    # Deduplicate show_cols — preserve order, remove duplicates
    seen = set()
    show_cols = []
    for c in base_cols:
        if c in display_df.columns and c not in seen:
            show_cols.append(c)
            seen.add(c)
    rename_map = {
        "rep_id":"Rep","assigned_day":"Day","day_visit_order":"Visit Order",
        "store_name":"Store","category":"Category","size_tier":"Size",
        "score":"Score","visits_per_month":"Visits/Mo","annual_visits":"Annual Visits",
        "visit_duration_min":"Duration (min)","coverage_status":"Status",
        "rating":"Rating","review_count":"Reviews","phone":"Phone",
        "opening_hours":"Opening Hours","address":"Address","city":"City",
        "lat":"Latitude","lng":"Longitude",
        "plan_visits": "Plan Visits (total)",
    }
    # Add month column renames using full label names to avoid 3-char collision
    for i, mk in enumerate(PLAN_MONTH_KEYS):
        lbl = PLAN_MONTHS[i] if i < len(PLAN_MONTHS) else f"Month {i+1}"
        rename_map[f"{mk}_dates"]  = f"{lbl} Dates"
        rename_map[f"{mk}_visits"] = f"{lbl} Visits"
    df_show = display_df[show_cols].rename(columns=rename_map)
    # Final dedup safeguard
    df_show = df_show.loc[:, ~df_show.columns.duplicated()]
    st.dataframe(df_show, use_container_width=True, height=460,
        column_config={
            "Score":    st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating":   st.column_config.NumberColumn("Rating", format="%.1f"),
            "Latitude": st.column_config.NumberColumn("Latitude",  format="%.5f"),
            "Longitude":st.column_config.NumberColumn("Longitude", format="%.5f"),
        })



    # Summary metrics
    st.markdown("---")
    cfg_ref        = st.session_state.get("market_config", {})
    daily_cap      = cfg_ref.get("daily_minutes", 480)
    break_mins     = cfg_ref.get("break_minutes",
        st.session_state.get("admin_rep_defaults",{}).get("break_minutes", 30))
    work_days      = cfg_ref.get("working_days", 22)
    effective_daily = daily_cap - break_mins  # actual selling time per day
    # Number of reps for this view
    n_reps_in_view = len(set(s.get("rep_id",0) for s in all_stores
                              if s.get("rep_id",0) > 0 and s.get("plan_visits",0) > 0))
    if tbl_rep_id:
        n_reps_in_view = 1
    monthly_cap_total = effective_daily * work_days * max(n_reps_in_view, 1)

    # Pull zone_centres travel data for this rep if available
    _zc_list   = st.session_state.get("run_results", {}).get("rep_recommendation", {}).get("zone_centres", [])
    _zc_by_rep = {int(z["zone"]): z for z in _zc_list}

    # Routed stores only
    if tbl_rep_id:
        _routed = display_df[display_df["plan_visits"].fillna(0) > 0] if "plan_visits" in display_df.columns else display_df
    else:
        _routed = display_df[display_df["plan_visits"].fillna(0) > 0] if "plan_visits" in display_df.columns else display_df

    is_day_view = tbl_day not in ("Full month", "All dates", "All weeks", "") and tbl_month != "Full plan"

    if is_day_view:
        # ── SPECIFIC DATE VIEW ──────────────────────────────────────────────
        # Execution = sum of visit_duration_min for stores on this day
        exec_t  = int(_routed["visit_duration_min"].sum()) if "visit_duration_min" in _routed.columns and not _routed.empty else 0
        # Travel = actual route through today's stores in visit order using geocoords
        avg_speed = cfg_ref.get("avg_speed_kmh",
            st.session_state.get("admin_rep_defaults", {}).get("avg_speed_kmh", 30))
        day_stores_ordered = (
            _routed.sort_values("day_visit_order")
            .to_dict("records")
            if "day_visit_order" in _routed.columns and not _routed.empty
            else []
        )
        travel_t = 0
        if day_stores_ordered:
            # Start from zone centroid if available, else first store
            if tbl_rep_id and tbl_rep_id in _zc_by_rep:
                prev_lat = _zc_by_rep[tbl_rep_id].get("centre_lat", day_stores_ordered[0].get("lat", 0))
                prev_lng = _zc_by_rep[tbl_rep_id].get("centre_lng", day_stores_ordered[0].get("lng", 0))
            else:



                prev_lat = day_stores_ordered[0].get("lat", 0)
                prev_lng = day_stores_ordered[0].get("lng", 0)
            for st_row in day_stores_ordered:
                slat = st_row.get("lat") or st_row.get("Latitude", 0)
                slng = st_row.get("lng") or st_row.get("Longitude", 0)
                try:
                    slat, slng = float(slat), float(slng)
                    if slat and slng:
                        travel_t += _hav_min(prev_lat, prev_lng, slat, slng, avg_speed)
                        prev_lat, prev_lng = slat, slng
                except (TypeError, ValueError):
                    pass
        travel_t = round(travel_t)
        total_t  = exec_t + break_mins + travel_t
        cap_day  = daily_cap   # 480 min (full day including break)
        util_pct = round(total_t / max(cap_day, 1) * 100)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Stores this day", len(_routed))
        m2.metric("Execution", f"{exec_t} min",
            help="Sum of visit durations for stores on this date.")
        m3.metric("Travel", f"{travel_t} min",
            help="Actual travel time routing through stores in visit order.")
        m4.metric("Break", f"{break_mins} min",
            help=f"Fixed {break_mins} min break per day.")
        flag = " " if total_t <= cap_day else (" " if total_t <= cap_day*1.25 else " ")
        m5.metric(f"{flag} Total / capacity",
            f"{total_t} / {cap_day} min ({util_pct}%)",
            help=f"Execution + Travel + Break vs {cap_day} min full day capacity.")

    else:
        # ── MONTHLY / FULL PLAN VIEW ────────────────────────────────────────
        if "visit_duration_min" in _routed.columns and not _routed.empty:
            exec_monthly = int((_routed["plan_visits"].fillna(0) * _routed["visit_duration_min"]).sum())
            # Travel from zone_centres
            if tbl_rep_id and tbl_rep_id in _zc_by_rep:
                monthly_et   = _zc_by_rep[tbl_rep_id].get("time_needed_min", 0)
                travel_monthly = max(0, monthly_et - exec_monthly)
            else:
                travel_monthly = 0
            break_monthly = break_mins * work_days * n_reps_in_view
            total_monthly = exec_monthly + travel_monthly + break_monthly
            cap_monthly   = daily_cap * work_days * n_reps_in_view
            util_pct      = round(total_monthly / max(cap_monthly, 1) * 100)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Stores in view", len(_routed))



            m2.metric("Execution / month", f"{exec_monthly:,} min",
                help="plan_visits × visit_duration for all routed stores.")
            m3.metric("Travel / month", f"{travel_monthly:,} min",
                help="From zone routing calculations.")
            m4.metric("Break / month", f"{break_monthly:,} min",
                help=f"{break_mins} min × {work_days} days × {n_reps_in_view} rep(s).")
            m5.metric(f"Utilisation",
                f"{util_pct}% ({total_monthly:,} / {cap_monthly:,} min)",
                help=f"(Execution + Travel + Break) / ({daily_cap} × {work_days} × {n_reps_in_view} reps).")
        else:
            m1, m2, m3, m4, m5 = st.columns(5)
            for mx in [m1,m2,m3,m4,m5]: mx.metric("—","—")

    if "coverage_status" in display_df.columns:
        gap_count = len(display_df[display_df["coverage_status"]=="gap"])
        if gap_count > 0:
            st.caption(f"  {gap_count} gap store(s) in this view.")
else:
    st.info("No stores for this selection.")

# ── GEOJSON ───────────────────────────────────────────────────────────────────
st.markdown("---")
features = [{"type":"Feature",
    "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
    "properties":{k:s.get(k) for k in ["store_name","score","size_tier","visits_per_month",
        "assigned_day","day_visit_order","visit_dates","rep_id","coverage_status","category"]}}
    for s in all_stores if s.get("lat") and s.get("lng")]
st.download_button("  Full routes GeoJSON",
    json.dumps({"type":"FeatureCollection","features":features}, indent=2),
    f"rep_routes_{mkt_safe}.geojson","application/json")
