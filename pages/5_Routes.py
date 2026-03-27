import streamlit as st
import pandas as pd
import json
import datetime

st.set_page_config(page_title="Routes - Coverage Tool", page_icon="🗺️", layout="wide")

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

route_year  = cfg.get("route_year", datetime.date.today().year)

st.markdown(f"""
<div class="page-header">
    <h2>🗺️ Rep Routes — {route_year}</h2>
    <p>Market: {market}</p>
</div>
""", unsafe_allow_html=True)

MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]
MONTH_SHORT = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]

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
all_days  = ["Full month"] + ["Monday","Tuesday","Wednesday","Thursday","Friday"]

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    colour_by = st.selectbox("Colour by", ["Rep route","Day of week","Size tier","Coverage status","Score"])
with col2:
    sel_rep = st.selectbox("Rep", ["All reps"] + [f"Rep {r}" for r in all_reps])
with col3:
    sel_month = st.selectbox("Month", ["Full year"] + MONTH_NAMES)
with col4:
    sel_day = st.selectbox("Day", all_days)
with col5:
    show_gaps    = st.checkbox("Show gap stores",    value=True)
    show_covered = st.checkbox("Show covered stores",value=True)

# Resolve selected month key
sel_month_key = None
if sel_month != "Full year":
    sel_month_key = MONTH_SHORT[MONTH_NAMES.index(sel_month)]

# Apply filters
map_stores = [s for s in all_stores if s.get("lat") and s.get("lng")]
if sel_rep != "All reps":
    rep_num    = int(sel_rep.split()[1])
    map_stores = [s for s in map_stores if s.get("rep_id") == rep_num]
if sel_day != "Full month":
    map_stores = [s for s in map_stores if s.get("assigned_day") == sel_day]
# For month filter — only show stores that have visits in that month
if sel_month_key:
    map_stores = [s for s in map_stores if s.get(f"{sel_month_key}_visits",0) > 0]
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
        cols = st.columns(min(len(reps),5))
        for i,rep in enumerate(reps):
            rs = [s for s in map_stores if s.get("rep_id")==rep]
            tv = sum(s.get("visits_per_month",0) for s in rs)
            c  = REP_COLORS[rep % len(REP_COLORS)]
            hx = "#{:02x}{:02x}{:02x}".format(c[0],c[1],c[2])
            cols[i%5].markdown(f'<div class="rep-chip" style="background:{hx}">Rep {rep}<br><small>{len(rs)} stores · {tv:.0f} visits/mo</small></div>',unsafe_allow_html=True)
elif colour_by == "Day of week":
    lc = st.columns(5)
    for i,(day,col) in enumerate(DAY_COLORS.items()):
        ds = [s for s in map_stores if s.get("assigned_day")==day]
        lc[i].markdown(f'<div class="day-chip" style="background:{col}">{day}<br><small>{len(ds)} stores</small></div>',unsafe_allow_html=True)
elif colour_by == "Size tier":
    lc = st.columns(3)
    for i,(tier,col) in enumerate([("Large","#2E7D32"),("Medium","#1565C0"),("Small","#F57F17")]):
        lc[i].markdown(f'<div class="rep-chip" style="background:{col}">{tier}</div>',unsafe_allow_html=True)
elif colour_by == "Coverage status":
    lc = st.columns(2)
    lc[0].markdown('<div class="rep-chip" style="background:#2E7D32">Covered</div>',unsafe_allow_html=True)
    lc[1].markdown('<div class="rep-chip" style="background:#C62828">Gap</div>',unsafe_allow_html=True)

st.markdown("---")

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Download rep route files</div>', unsafe_allow_html=True)
st.caption("Each file includes store details, assigned day, visit dates, visit order and coordinates.")

mkt_safe = market.replace(" ","_").replace("-","_")

def build_rep_df(stores, rep_id=None, day=None, month_key=None):
    filtered = [s for s in stores if s.get("rep_id",0) > 0]
    if rep_id:
        filtered = [s for s in filtered if s.get("rep_id") == rep_id]
    if day and day != "Full month":
        filtered = [s for s in filtered if s.get("assigned_day") == day]
    if month_key:
        filtered = [s for s in filtered if s.get(f"{month_key}_visits",0) > 0]
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
        # Add monthly visit dates
        for m in MONTH_SHORT:
            row[f"{m}_dates"]  = ", ".join(s.get(f"{m}_dates", []))
            row[f"{m}_visits"] = s.get(f"{m}_visits", 0)
        rows.append(row)
    return pd.DataFrame(rows)

if all_reps:
    all_df = build_rep_df(all_stores)
    if not all_df.empty:
        st.download_button("⬇️ Download all reps — full month CSV",
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
            st.download_button(f"⬇️ Rep {rep} CSV",
                rep_df.to_csv(index=False), f"rep_{rep}_{mkt_safe}.csv", "text/csv", key=f"dl_rep_{rep}")

st.markdown("---")

# ── ROUTE DETAIL TABLE ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Route detail</div>', unsafe_allow_html=True)
st.caption("Select a rep and day to see the exact stores and visit order for that day.")

col_r, col_m, col_d = st.columns(3)
with col_r:
    tbl_rep = st.selectbox("Rep", ["All reps"] + [f"Rep {r}" for r in all_reps], key="tbl_rep")
with col_m:
    tbl_month = st.selectbox("Month", ["Full year"] + MONTH_NAMES, key="tbl_month")
with col_d:
    tbl_day = st.selectbox("Day", all_days, key="tbl_day")

tbl_rep_id   = int(tbl_rep.split()[1]) if tbl_rep != "All reps" else None
tbl_month_key = MONTH_SHORT[MONTH_NAMES.index(tbl_month)] if tbl_month != "Full year" else None
display_df   = build_rep_df(all_stores, rep_id=tbl_rep_id,
    day=tbl_day if tbl_day != "Full month" else None,
    month_key=tbl_month_key)

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
        # Show all month visit counts
        base_cols = base_cols + [f"{m}_visits" for m in MONTH_SHORT]
    show_cols = [c for c in base_cols if c in display_df.columns]
    rename_map = {
        "rep_id":"Rep","assigned_day":"Day","day_visit_order":"Visit Order",
        "store_name":"Store","category":"Category","size_tier":"Size",
        "score":"Score","visits_per_month":"Visits/Mo","annual_visits":"Annual Visits",
        "visit_duration_min":"Duration (min)","coverage_status":"Status",
        "rating":"Rating","review_count":"Reviews","phone":"Phone",
        "opening_hours":"Opening Hours","address":"Address","city":"City",
        "lat":"Latitude","lng":"Longitude",
        **{f"{m}_dates": f"{n[:3]} Dates" for m,n in zip(MONTH_SHORT,MONTH_NAMES)},
        **{f"{m}_visits": f"{n[:3]}" for m,n in zip(MONTH_SHORT,MONTH_NAMES)},
    }
    df_show = display_df[show_cols].rename(columns=rename_map)
    st.dataframe(df_show, use_container_width=True, height=460,
        column_config={
            "Score":    st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating":   st.column_config.NumberColumn("Rating", format="%.1f"),
            "Latitude": st.column_config.NumberColumn("Latitude",  format="%.5f"),
            "Longitude":st.column_config.NumberColumn("Longitude", format="%.5f"),
        })

    # Summary metrics
    st.markdown("---")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Stores",        len(display_df))
    m2.metric("Visits/month",  f"{display_df['visits_per_month'].sum():.0f}" if "visits_per_month" in display_df.columns else "—")
    m3.metric("Large stores",  len(display_df[display_df["size_tier"]=="Large"]) if "size_tier" in display_df.columns else 0)
    m4.metric("Gap opportunities", len(display_df[display_df["coverage_status"]=="gap"]) if "coverage_status" in display_df.columns else 0)
else:
    st.info("No stores for this selection.")

# ── GEOJSON ───────────────────────────────────────────────────────────────────
st.markdown("---")
features = [{"type":"Feature",
    "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
    "properties":{k:s.get(k) for k in ["store_name","score","size_tier","visits_per_month",
        "assigned_day","day_visit_order","visit_dates","rep_id","coverage_status","category"]}}
    for s in all_stores if s.get("lat") and s.get("lng")]
st.download_button("⬇️ Full routes GeoJSON",
    json.dumps({"type":"FeatureCollection","features":features}, indent=2),
    f"rep_routes_{mkt_safe}.geojson","application/json")
