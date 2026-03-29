import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Dashboard - Coverage Tool", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
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
.market-card {
    background: #F0F4F8; border: 1px solid #D0DCF0; border-left: 4px solid #1565C0;
    border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
}
.market-card h4 { color: #1A2B4A; font-size: 0.95rem; font-weight: 700; margin: 0 0 4px 0; }
.market-card p  { color: #6B7280; font-size: 0.82rem; margin: 0; }
.kpi-card {
    background: #F0F4F8; border: 1px solid #D0DCF0; border-top: 4px solid #1565C0;
    border-radius: 8px; padding: 1.2rem; text-align: center;
}
.kpi-value { font-size: 2rem; font-weight: 800; color: #1A2B4A; line-height: 1; }
.kpi-label { font-size: 0.8rem; color: #6B7280; margin-top: 0.3rem; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.05em; }
.legend-chip {
    display: inline-block; padding: 5px 12px; border-radius: 20px;
    color: white; font-size: 0.8rem; font-weight: 600; margin: 3px;
}
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white; border-radius: 6px; font-weight: 600;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📈 Market Dashboard</h2>
    <p>Upload market snapshots and explore results — routes, reps, daily schedules</p>
</div>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
REP_COLORS  = ["#1565C0","#2E7D32","#E65100","#6A1B9A","#00695C","#4A148C","#B71C1C","#004D40","#3E2723","#263238"]
MONTH_NAMES = ["January","February","March","April","May","June","July","August","September","October","November","December"]
MONTH_SHORT = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]

def get_dates_for_month(df, month_key):
    dates = set()
    col = f"{month_key}_dates"
    if col in df.columns:
        for val in df[col].dropna():
            for d in str(val).split(","):
                d = d.strip()
                if d and d != "nan":
                    dates.add(d)
    return ["All dates"] + sorted(dates)

def hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2],16) for i in (0,2,4)]

# ── SNAPSHOT LIBRARY ─────────────────────────────────────────────────────────
if "snapshot_library" not in st.session_state:
    st.session_state["snapshot_library"] = {}

is_admin = st.session_state.get("admin_authenticated", False)

# ── ADMIN UPLOAD ──────────────────────────────────────────────────────────────
if is_admin:
    st.markdown('<div class="section-title">Upload market snapshot (Admin only)</div>', unsafe_allow_html=True)
    st.caption("Upload the stores CSV downloaded from the Results page (*_stores.csv).")
    stores_file = st.file_uploader("Stores CSV  (*_stores.csv)", type=["csv"], key="upload_stores")

    if stores_file:
        # Auto-detect run date from filename e.g. Brazil_Recife_2026-03-29_stores.csv
        import re as _re
        fname       = stores_file.name
        date_match  = _re.search(r"(\d{4}-\d{2}-\d{2})", fname)
        auto_date   = datetime.date.fromisoformat(date_match.group(1)) if date_match else datetime.date.today()
        # Auto-detect market name from filename (first part before date)
        name_part   = fname.replace("_stores.csv","").replace("_stores","")
        name_part   = _re.sub(r"_?\d{4}-\d{2}-\d{2}_?","", name_part).replace("_"," ").strip()
        st.caption(f"Detected from filename: **{name_part}** · **{auto_date}**")
    else:
        auto_date  = datetime.date.today()
        name_part  = ""

    col_a, col_b, col_c = st.columns(3)
    with col_a: snap_market   = st.text_input("Market name",  value=name_part, placeholder="e.g. Recife")
    with col_b: snap_category = st.text_input("Category",     placeholder="e.g. Supermarket")
    with col_c: snap_date     = st.date_input("Run date",     value=auto_date)

    if st.button("Save snapshot to library", type="primary"):
        if not stores_file:
            st.error("Please upload a stores CSV first.")
        elif not snap_market:
            st.error("Market name is required.")
        else:
            try:
                stores_file.seek(0)
                stores_df = pd.read_csv(stores_file)
                if "Unnamed: 0" in stores_df.columns:
                    stores_df = stores_df.drop(columns=["Unnamed: 0"])
                if "store_name" not in stores_df.columns:
                    st.error("This doesn't look like a stores CSV — missing store_name column. Please upload the *_stores.csv file from the Results page.")
                    st.stop()
                snap_key = f"{snap_market}_{snap_category}_{snap_date}".replace(" ","_")
                st.session_state["snapshot_library"][snap_key] = {
                    "name": snap_market, "category": snap_category,
                    "run_date": str(snap_date), "stores_df": stores_df,
                    "summary_df": pd.DataFrame(),
                    "uploaded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "key": snap_key,
                }
                st.success(f"✅ Snapshot saved: {snap_market} — {snap_date}")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
    st.markdown("---")

library = st.session_state.get("snapshot_library", {})
if not library:
    st.info("No market snapshots uploaded yet. " +
        ("Use the upload section above to add a market." if is_admin
         else "Ask your admin to upload market snapshots."))
    st.stop()

# ── MARKET LIBRARY CARDS ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">Market library</div>', unsafe_allow_html=True)
keys_to_delete = []
snap_keys = list(library.keys())
for row_start in range(0, len(snap_keys), 3):
    row_cols = st.columns(3)
    for i, key in enumerate(snap_keys[row_start:row_start+3]):
        snap      = library[key]
        sdf       = snap["stores_df"]
        n_stores  = len(sdf)
        n_gaps    = len(sdf[sdf["coverage_status"]=="gap"]) if "coverage_status" in sdf.columns else 0
        cov_rate  = snap["summary_df"].iloc[0].get("coverage_rate_after","—") if not snap["summary_df"].empty else "—"
        with row_cols[i]:
            st.markdown(f"""
            <div class="market-card">
                <h4>📍 {snap['name']} — {snap['category']}</h4>
                <p>Run date: {snap['run_date']} · Uploaded: {snap['uploaded_at']}</p>
                <p style="margin-top:6px">
                    <strong>{n_stores:,}</strong> stores ·
                    <strong>{n_gaps:,}</strong> gaps ·
                    Coverage: <strong>{cov_rate}</strong>
                </p>
            </div>""", unsafe_allow_html=True)
            if is_admin and st.button("🗑 Delete", key=f"del_{key}"):
                keys_to_delete.append(key)
for k in keys_to_delete:
    del st.session_state["snapshot_library"][k]
if keys_to_delete:
    st.rerun()

st.markdown("---")

# ── MARKET SELECTOR ───────────────────────────────────────────────────────────
snap_options   = {f"{s['name']} — {s['category']} ({s['run_date']})": k for k, s in library.items()}
selected_label = st.selectbox("Select market snapshot to view", list(snap_options.keys()))
selected_key   = snap_options[selected_label]
snap           = library[selected_key]
stores_df      = snap["stores_df"].copy()
summary_df     = snap["summary_df"].copy()

st.markdown(f"**Viewing:** {snap['name']} — {snap['category']} — {snap['run_date']}")

# Detect 2-month plan columns from the stores CSV
_all_month_keys = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
_all_month_names = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]
DASH_PLAN_KEYS  = [m for m in _all_month_keys if f"{m}_visits" in stores_df.columns]
DASH_PLAN_NAMES = [_all_month_names[_all_month_keys.index(m)] for m in DASH_PLAN_KEYS]

# ── KPIs ──────────────────────────────────────────────────────────────────────
n_total   = len(stores_df)
n_covered = len(stores_df[stores_df["coverage_status"]=="covered"]) if "coverage_status" in stores_df.columns else 0
n_gaps    = len(stores_df[stores_df["coverage_status"]=="gap"])    if "coverage_status" in stores_df.columns else 0
cov_pct   = round(n_covered/max(n_total,1)*100,1)
n_reps    = stores_df["rep_id"].nunique() if "rep_id" in stores_df.columns else 0

c1,c2,c3,c4,c5,c6 = st.columns(6)
for col, val, label in [
    (c1, f"{n_total:,}",   "Total stores"),
    (c2, f"{n_covered:,}", "Covered"),
    (c3, f"{n_gaps:,}",    "Gaps"),
    (c4, f"{cov_pct}%",    "Coverage rate"),
    (c5, f"{len(stores_df[stores_df['size_tier']=='Large']):,}" if "size_tier" in stores_df.columns else "—", "Large stores"),
    (c6, f"{n_reps}",      "Reps"),
]:
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{val}</div>
        <div class="kpi-label">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ── SIZE DISTRIBUTION ─────────────────────────────────────────────────────────
if "size_tier" in stores_df.columns:
    fc = st.columns(3)
    tier_colors = {"Large":"#2E7D32","Medium":"#1565C0","Small":"#F57F17"}
    for i, tier in enumerate(["Large","Medium","Small"]):
        cnt = len(stores_df[stores_df["size_tier"]==tier])
        vpm = stores_df[stores_df["size_tier"]==tier]["visits_per_month"].sum() if "visits_per_month" in stores_df.columns else 0
        col = tier_colors[tier]
        fc[i].markdown(f"""
        <div style="background:#F8F9FA;border:1px solid #E0E0E0;border-top:4px solid {col};
        border-radius:8px;padding:1rem;text-align:center;margin-bottom:1rem">
            <div style="font-size:1.6rem;font-weight:800;color:#1A2B4A">{cnt:,}</div>
            <div style="font-size:0.78rem;color:#6B7280;font-weight:600;text-transform:uppercase">{tier}</div>
            <div style="font-size:0.75rem;color:#9E9E9E;margin-top:2px">{vpm:.0f} visits/mo</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── MAP + FILTERS ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Store map & routes</div>', unsafe_allow_html=True)

all_reps  = sorted([r for r in stores_df["rep_id"].dropna().unique() if r > 0]) if "rep_id" in stores_df.columns else []

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    colour_by = st.selectbox("Colour by", ["Rep route","Size tier","Coverage status","Score"], key="dash_colour")
with col2:
    sel_rep   = st.selectbox("Rep", ["All reps"] + [f"Rep {int(r)}" for r in all_reps], key="dash_rep")
with col3:
    sel_month = st.selectbox("Month", ["Full plan"] + DASH_PLAN_NAMES, key="dash_month")
with col4:
    if sel_month != "Full plan" and sel_month in DASH_PLAN_NAMES:
        _mkey   = DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(sel_month)]
        _dates  = get_dates_for_month(stores_df, _mkey)
        sel_date = st.selectbox("Date", _dates, key="dash_date")
    else:
        sel_date = "All dates"
        st.selectbox("Date", ["All dates"], key="dash_date_empty", disabled=True)
with col5:
    show_gaps    = st.checkbox("Show gaps",    value=True,  key="dash_gaps")
    show_covered = st.checkbox("Show covered", value=True,  key="dash_covered")

# Apply filters
map_df = stores_df.dropna(subset=["lat","lng"]).copy() if "lat" in stores_df.columns else pd.DataFrame()

if not map_df.empty:
    if sel_rep != "All reps":
        rep_num = int(sel_rep.split()[1])
        map_df  = map_df[map_df["rep_id"] == rep_num]
    if sel_month != "Full plan" and sel_month in DASH_PLAN_NAMES:
        mkey   = DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(sel_month)]
        if f"{mkey}_visits" in map_df.columns:
            map_df = map_df[map_df[f"{mkey}_visits"].fillna(0) > 0]
        if sel_date != "All dates":
            date_col = f"{mkey}_dates"
            if date_col in map_df.columns:
                map_df = map_df[map_df[date_col].apply(lambda x: sel_date in str(x) if pd.notna(x) else False)]
    elif sel_month == "Full plan" and "plan_visits" in map_df.columns:
        map_df = map_df[map_df["plan_visits"].fillna(0) > 0]
    if not show_gaps and "coverage_status" in map_df.columns:
        map_df = map_df[map_df["coverage_status"] != "gap"]
    if not show_covered and "coverage_status" in map_df.columns:
        map_df = map_df[map_df["coverage_status"] == "gap"]

    def get_color(row):
        if colour_by == "Rep route":
            rid = int(row.get("rep_id", 0) or 0)
            c   = hex_to_rgb(REP_COLORS[rid % len(REP_COLORS)])
            return [c[0],c[1],c[2],210]
        elif colour_by == "Size tier":
            return {"Large":[46,125,50,220],"Medium":[21,101,192,220],"Small":[245,127,23,220]}.get(row.get("size_tier",""),[150,150,150,180])
        elif colour_by == "Coverage status":
            return [46,125,50,200] if row.get("coverage_status")=="covered" else [198,40,40,220]
        else:
            sc = row.get("score",0)
            if sc>=80: return [46,125,50,220]
            if sc>=60: return [21,101,192,220]
            if sc>=40: return [245,127,23,220]
            return [198,40,40,200]

    map_df["_color"]  = map_df.apply(get_color, axis=1)
    map_df["_radius"] = map_df["score"].fillna(50) * 1.5 if "score" in map_df.columns else 40

    try:
        import pydeck as pdk
        layer = pdk.Layer("ScatterplotLayer", data=map_df,
            get_position="[lng, lat]", get_color="_color", get_radius="_radius",
            radius_min_pixels=4, radius_max_pixels=20, pickable=True)
        view = pdk.ViewState(latitude=map_df["lat"].mean(), longitude=map_df["lng"].mean(), zoom=11, pitch=0)
        tooltip = {
            "html": "<b>{store_name}</b><br/>Score: <b>{score}</b><br/>Size: {size_tier}<br/>"
                    "Status: {coverage_status}<br/>Rep: {rep_id}<br/>Day: {assigned_day}",
            "style": {"backgroundColor":"#1A2B4A","color":"white","padding":"10px","borderRadius":"8px","fontSize":"13px"}
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    except Exception:
        st.map(map_df.rename(columns={"lng":"lon"})[["lat","lon"]])

    # ── COLOUR LEGEND ─────────────────────────────────────────────────────────
    if colour_by == "Rep route" and all_reps:
        leg_cols = st.columns(min(len(all_reps), 6))
        for i, rep in enumerate(all_reps[:6]):
            hx  = REP_COLORS[int(rep) % len(REP_COLORS)]
            cnt = len(map_df[map_df["rep_id"]==rep]) if not map_df.empty else 0
            leg_cols[i].markdown(
                f'<span class="legend-chip" style="background:{hx}">Rep {int(rep)} · {cnt} stores</span>',
                unsafe_allow_html=True)
    elif colour_by == "Size tier":
        lc = st.columns(3)
        for i,(tier,col) in enumerate([("Large","#2E7D32"),("Medium","#1565C0"),("Small","#F57F17")]):
            lc[i].markdown(f'<span class="legend-chip" style="background:{col}">{tier}</span>', unsafe_allow_html=True)
    elif colour_by == "Coverage status":
        lc = st.columns(2)
        lc[0].markdown('<span class="legend-chip" style="background:#2E7D32">Covered</span>', unsafe_allow_html=True)
        lc[1].markdown('<span class="legend-chip" style="background:#C62828">Gap</span>', unsafe_allow_html=True)
    elif colour_by == "Score":
        lc = st.columns(4)
        for i,(label,col) in enumerate([("≥80","#2E7D32"),("60-79","#1565C0"),("40-59","#F57F17"),("<40","#C62828")]):
            lc[i].markdown(f'<span class="legend-chip" style="background:{col}">{label}</span>', unsafe_allow_html=True)

    st.caption(f"Showing {len(map_df):,} stores on map")

st.markdown("---")

# ── ROUTES TABLE ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Route detail</div>', unsafe_allow_html=True)
st.caption("Select rep, month and date to see stores and visit order for a specific day.")

tr1, tr2, tr3, tr4 = st.columns(4)
with tr1:
    tbl_rep   = st.selectbox("Rep", ["All reps"] + [f"Rep {int(r)}" for r in all_reps], key="tbl_rep_dash")
with tr2:
    tbl_month = st.selectbox("Month", ["Full plan"] + DASH_PLAN_NAMES, key="tbl_month_dash")
with tr3:
    if tbl_month != "Full plan" and tbl_month in DASH_PLAN_NAMES:
        _tmkey  = DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(tbl_month)]
        _tdates = get_dates_for_month(stores_df, _tmkey)
        tbl_date = st.selectbox("Date", _tdates, key="tbl_date_dash")
    else:
        tbl_date = "All dates"
        st.selectbox("Date", ["All dates"], disabled=True, key="tbl_date_dash_empty")
with tr4:
    route_filter_d = st.selectbox("Route status",
        ["Recommended stores","Not in route","All stores"], key="tbl_route_filter_dash")

# Apply route status filter
if route_filter_d == "Recommended stores" and "plan_visits" in stores_df.columns:
    route_df = stores_df[stores_df["plan_visits"] > 0].copy()
elif route_filter_d == "Not in route" and "plan_visits" in stores_df.columns:
    route_df = stores_df[stores_df["plan_visits"] == 0].copy()
else:
    route_df = stores_df.copy()

if tbl_rep != "All reps" and "rep_id" in route_df.columns:
    route_df = route_df[route_df["rep_id"] == int(tbl_rep.split()[1])]
if tbl_month != "Full plan" and tbl_month in DASH_PLAN_NAMES:
    tmkey = DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(tbl_month)]
    if f"{tmkey}_visits" in route_df.columns:
        route_df = route_df[route_df[f"{tmkey}_visits"] > 0]
    if tbl_date != "All dates":
        dcol = f"{tmkey}_dates"
        if dcol in route_df.columns:
            route_df = route_df[route_df[dcol].apply(lambda x: tbl_date in str(x) if pd.notna(x) else False)]

if "day_visit_order" in route_df.columns:
    route_df = route_df.sort_values(["rep_id","day_visit_order"]).reset_index(drop=True)

show_cols = [c for c in [
    "rep_id","assigned_day","day_visit_order","store_name","category",
    "size_tier","score","visits_per_month","plan_visits","visit_duration_min",
    "coverage_status","rating","review_count","phone","opening_hours","address","city"
] if c in route_df.columns]

if tbl_month != "Full plan" and tbl_month in DASH_PLAN_NAMES:
    dcol = f"{DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(tbl_month)]}_dates"
    if dcol in route_df.columns and dcol not in show_cols:
        show_cols.insert(4, dcol)

rename_map = {
    "rep_id":"Rep","assigned_day":"Day","day_visit_order":"Visit Order",
    "store_name":"Store","category":"Category","size_tier":"Size",
    "score":"Score","visits_per_month":"Visits/Mo","plan_visits":"Plan Visits",
    "visit_duration_min":"Duration (min)","coverage_status":"Status",
    "rating":"Rating","review_count":"Reviews",
    "phone":"Phone","opening_hours":"Hours","address":"Address","city":"City",
}
if tbl_month != "Full plan" and tbl_month in DASH_PLAN_NAMES:
    rename_map[f"{DASH_PLAN_KEYS[DASH_PLAN_NAMES.index(tbl_month)]}_dates"] = f"{tbl_month[:3]} Dates"

if not route_df.empty:
    df_show = route_df[[c for c in show_cols if c in route_df.columns]].rename(columns=rename_map)

    # Daily budget metrics when specific date selected
    if tbl_date != "All dates" and "Duration (min)" in df_show.columns:
        daily_cap = 480
        day_time  = int(df_show["Duration (min)"].sum())
        m1,m2,m3 = st.columns(3)
        m1.metric("Stores on this day", len(df_show))
        m2.metric("Time for this day",  f"{day_time} min",
            delta=f"Budget: {daily_cap} min", delta_color="off")
        m3.metric("Budget status",
            "✅ Within budget" if day_time <= daily_cap else f"⚠️ Over by {day_time-daily_cap} min")

    st.dataframe(df_show, use_container_width=True, height=420,
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
        })
    st.caption(f"Showing {len(route_df):,} stores")
else:
    st.info("No stores match the current selection.")

st.markdown("---")

# ── GAP REPORT ────────────────────────────────────────────────────────────────
if "coverage_status" in stores_df.columns:
    gaps = stores_df[stores_df["coverage_status"]=="gap"].sort_values("score",ascending=False) if "score" in stores_df.columns else stores_df[stores_df["coverage_status"]=="gap"]
    if not gaps.empty:
        st.markdown('<div class="section-title">Top gap opportunities</div>', unsafe_allow_html=True)
        gap_cols = [c for c in ["store_name","category","score","size_tier","visits_per_month","rating","review_count","address"] if c in gaps.columns]
        st.dataframe(gaps[gap_cols].head(50).reset_index(drop=True), use_container_width=True, height=300,
            column_config={"score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Downloads</div>', unsafe_allow_html=True)
safe_name = f"{snap['name']}_{snap['category']}_{snap['run_date']}".replace(" ","_")
col1, col2 = st.columns(2)
with col1:
    st.download_button("⬇️ Full stores CSV",
        stores_df.to_csv(index=False), f"{safe_name}_stores.csv", "text/csv")
with col2:
    if not summary_df.empty:
        st.download_button("⬇️ Summary CSV",
            summary_df.to_csv(index=False), f"{safe_name}_summary.csv", "text/csv")
