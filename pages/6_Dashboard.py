import streamlit as st
import ast
import pandas as pd
import datetime
import math

st.set_page_config(page_title="Dashboard - Coverage Tool", page_icon=" ", layout="wide")

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

st.html("""
<div class="page-header">
    <h2>  Market Dashboard</h2>
    <p>Upload market snapshots and explore results &mdash; routes, reps, daily schedules</p>
</div>
""")

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
REP_COLORS = ["#1565C0","#2E7D32","#E65100","#6A1B9A","#00695C","#4A148C","#B71C1C","#004D40","#3E2723","#263238"]

def hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2],16) for i in (0,2,4)]

def parse_dates_cell(val):
    """Parse a date cell — handles lists and stringified lists from CSV."""
    if val is None or (isinstance(val, float)): return []
    if isinstance(val, list): return [str(d).strip() for d in val if d]
    s = str(val).strip()
    if not s or s in ("nan","[]",""): return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list): return [str(d).strip() for d in parsed if d]
    except Exception: pass
    s = s.strip("[]").replace("'","").replace('"',"")
    return [d.strip() for d in s.split(",") if d.strip()]

def get_plan_keys(df):
    """
    Detect plan month keys from dataframe columns.
    Supports both pipeline format (m1, m2 ...) and legacy (jan, feb ...).
    Returns list of (key, label) e.g. [("m1","April 2026"), ("m2","May 2026")]
    """
    keys = []
    # New format: m1, m2, m3 ... with m1_visits column
    for i in range(1, 13):
        mk = f"m{i}"
        if f"{mk}_visits" in df.columns or f"{mk}_dates" in df.columns:
            # Try to get real label from route_plan_months session state
            _rpm = st.session_state.get("route_plan_months", {})
            _labels = _rpm.get("month_labels", [])
            _keys   = _rpm.get("month_keys", [])
            if mk in _keys:
                label = _labels[_keys.index(mk)]
            else:



                label = f"Month {i}"
            keys.append((mk, label))
    # Legacy format: jan, feb ...
    if not keys:
        month_short = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
        month_full  = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        for mk, ml in zip(month_short, month_full):
            if f"{mk}_visits" in df.columns:
                keys.append((mk, ml))
    return keys

def get_dates_for_month(df, month_key):
    """Get sorted unique dates for a plan month."""
    dates = set()
    date_col = f"{month_key}_dates"
    week_col = f"{month_key}_weeks"
    for col in [date_col, week_col]:
        if col in df.columns:
            for val in df[col].dropna():
                for d in parse_dates_cell(val):
                    if d and d not in ("nan",""):
                        dates.add(d)
            if dates: break

    def _sort_key(d):
        for fmt in ("%d %b","%d %B","%b %d","%Y-%m-%d"):
            try: return datetime.datetime.strptime(d.strip(), fmt)
            except: pass
        return datetime.datetime.max

    return ["All dates"] + sorted(dates, key=_sort_key)

# ── SNAPSHOT LIBRARY ──────────────────────────────────────────────────────────
if "snapshot_library" not in st.session_state:
    st.session_state["snapshot_library"] = {}

# ── UPLOAD SECTION (all users can upload) ─────────────────────────────────────
st.html('<div class="section-title">Upload market snapshot</div>')
st.caption("Upload the stores CSV downloaded from the Results page to view it here. "
           "Snapshots are stored in this session only.")

with st.expander("  Upload snapshot CSV", expanded=not bool(st.session_state["snapshot_library"])):
    stores_file = st.file_uploader("Stores CSV (*_stores.csv from Results page)",
                                   type=["csv"], key="upload_stores")
    if stores_file:
        import re as _re



        fname      = stores_file.name
        date_match = _re.search(r"(\d{4}-\d{2}-\d{2})", fname)
        auto_date  = datetime.date.fromisoformat(date_match.group(1)) if date_match else datetime.date.today()
        name_part  = _re.sub(r"_?\d{4}-\d{2}-\d{2}_?","",
                             fname.replace("_stores.csv","").replace("_stores","")
                             ).replace("_"," ").strip()
        st.caption(f"Detected: **{name_part or 'Market'}** · **{auto_date}**")
    else:
        auto_date = datetime.date.today()
        name_part = ""

    col_a, col_b, col_c = st.columns(3)
    with col_a: snap_market   = st.text_input("Market name",  value=name_part or "", placeholder="e.g. Al Kamil")
    with col_b: snap_category = st.text_input("Sub-channel",  placeholder="e.g. Supermarket")
    with col_c: snap_date     = st.date_input("Run date",     value=auto_date)

    if st.button("  Save snapshot", type="primary", key="btn_save_snap"):
        if not stores_file:
            st.error("Please upload a stores CSV first.")
        elif not snap_market:
            st.error("Market name is required.")
        else:
            try:
                stores_file.seek(0)
                stores_df_up = pd.read_csv(stores_file)
                if "Unnamed: 0" in stores_df_up.columns:
                    stores_df_up = stores_df_up.drop(columns=["Unnamed: 0"])
                if "store_name" not in stores_df_up.columns:
                    st.error("Missing store_name column — please upload the *_stores.csv from Results page.")
                else:
                    snap_key = f"{snap_market}_{snap_category}_{snap_date}".replace(" ","_")
                    st.session_state["snapshot_library"][snap_key] = {
                        "name":        snap_market,
                        "category":    snap_category,
                        "run_date":    str(snap_date),
                        "stores_df":   stores_df_up,
                        "uploaded_at": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                        "key":         snap_key,
                    }
                    st.success(f"  Snapshot saved: {snap_market} — {snap_date}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")

st.markdown("---")

# ── BUILD LIBRARY (snapshots + live session fallback) ─────────────────────────



library = dict(st.session_state.get("snapshot_library", {}))

# Always add live session if pipeline has been run
run_res = st.session_state.get("run_results", {})
if run_res and run_res.get("all_stores"):
    _live_df     = pd.DataFrame(run_res["all_stores"])
    cfg_live     = st.session_state.get("market_config", {})
    _market_name = cfg_live.get("market_name", "Current run")
    library["live_session"] = {
        "name":        _market_name,
        "category":    "Live session",
        "run_date":    datetime.date.today().strftime("%d %b %Y"),
        "uploaded_at": "Live",
        "stores_df":   _live_df,
        "key":         "live_session",
    }

if not library:
    st.info("No data yet. Run the pipeline or upload a snapshot above.")
    st.stop()

# ── MARKET LIBRARY CARDS ──────────────────────────────────────────────────────
st.html('<div class="section-title">Market library</div>')
keys_to_delete = []
snap_keys = [k for k in library if k != "live_session"]  # live always shown, not deletable
if snap_keys:
    for row_start in range(0, len(snap_keys), 3):
        row_cols = st.columns(3)
        for i, key in enumerate(snap_keys[row_start:row_start+3]):
            snap = library[key]
            sdf  = snap["stores_df"]
            n_stores = len(sdf)
            n_gaps   = len(sdf[sdf["coverage_status"]=="gap"]) if "coverage_status" in sdf.columns else 0
            with row_cols[i]:
                st.markdown(f"""
                <div class="market-card">
                    <h4>  {snap['name']} — {snap['category']}</h4>
                    <p>Run date: {snap['run_date']} · Uploaded: {snap['uploaded_at']}</p>
                    <p style="margin-top:6px">
                        <strong>{n_stores:,}</strong> stores ·
                        <strong>{n_gaps:,}</strong> gaps
                    </p>
                </div>""", unsafe_allow_html=True)
                if st.button("  Delete", key=f"del_{key}"):
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

# Detect plan keys from this dataframe
PLAN_KEYS = get_plan_keys(stores_df)  # list of (key, label)
PLAN_LABELS = [label for _, label in PLAN_KEYS]
PLAN_KEY_MAP = {label: key for key, label in PLAN_KEYS}  # label -> key

st.caption(f"Viewing: **{snap['name']}** — {snap['category']} — {snap['run_date']} · "
           f"{len(stores_df):,} stores · plan months: {', '.join(PLAN_LABELS) if PLAN_LABELS else 'none detected'}")

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.html('<div class="section-title">Summary KPIs</div>')

n_total      = len(stores_df)
n_covered    = len(stores_df[stores_df["coverage_status"]=="covered"]) if "coverage_status" in stores_df.columns else 0
n_gaps       = len(stores_df[stores_df["coverage_status"]=="gap"])     if "coverage_status" in stores_df.columns else 0
n_proposed   = len(stores_df[stores_df["plan_visits"].fillna(0) > 0])  if "plan_visits" in stores_df.columns else 0
proposed_pct = round(n_proposed / max(n_total,1) * 100, 1)
n_removed    = len(stores_df[(stores_df.get("covered", pd.Series(dtype=bool))==True) &
                              (stores_df["plan_visits"].fillna(0)==0)]) \
               if "covered" in stores_df.columns and "plan_visits" in stores_df.columns else 0
n_new        = len(stores_df[(stores_df.get("covered", pd.Series(dtype=bool))==False) &
                              (stores_df["plan_visits"].fillna(0)>0)]) \
               if "covered" in stores_df.columns and "plan_visits" in stores_df.columns else 0

c1,c2,c3,c4,c5,c6 = st.columns(6)
for col, val, label in [
    (c1, f"{n_total:,}",        "Total Universe"),
    (c2, f"{n_covered:,}",      "Current Coverage"),
    (c3, f"{n_proposed:,}",     "Proposed Coverage"),
    (c4, f"{proposed_pct}%",    "Proposed Coverage Rate"),
    (c5, f"{n_removed:,}",      "Stores Removed"),
    (c6, f"{n_new:,}",          "New Stores Added"),
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
        vpm = stores_df[stores_df["size_tier"]==tier]["visits_per_month"].sum() \
              if "visits_per_month" in stores_df.columns else 0
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
st.html('<div class="section-title">Store map &amp; routes</div>')

all_reps = sorted([r for r in stores_df["rep_id"].dropna().unique() if int(r) > 0]) \
           if "rep_id" in stores_df.columns else []

# Build rep labels with rule names from zone_centres
_dash_rep_rec   = st.session_state.get("run_results", {}).get("rep_recommendation", {})
_dash_zone_rule = {}
for _z in _dash_rep_rec.get("zone_centres", []):
    if _z.get("zone") is not None:
        _dash_zone_rule[_z["zone"]] = _z.get("rule_name", "Mixed")

def _dash_rep_label(rid):
    rule = _dash_zone_rule.get(int(rid), "")
    if rule and rule != "Mixed":
        return f"Rep {int(rid)} ({rule})"
    return f"Rep {int(rid)}"

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    colour_by = st.selectbox("Colour by",
        ["Rep route","Size tier","Coverage status","Score"], key="dash_colour")
with col2:
    sel_rep = st.selectbox("Rep",
        ["All reps"] + [_dash_rep_label(r) for r in all_reps], key="dash_rep")
with col3:
    sel_month_label = st.selectbox("Month",
        ["Full plan"] + PLAN_LABELS, key="dash_month")
with col4:
    if sel_month_label != "Full plan" and sel_month_label in PLAN_KEY_MAP:
        _mkey  = PLAN_KEY_MAP[sel_month_label]
        _dates = get_dates_for_month(stores_df, _mkey)
        sel_date = st.selectbox("Date", _dates, key="dash_date")
    else:
        sel_date = "All dates"



        st.selectbox("Date", ["All dates"], key="dash_date_empty", disabled=True)
with col5:
    show_gaps    = st.checkbox("Show gaps",    value=True,  key="dash_gaps")
    show_covered = st.checkbox("Show covered", value=True,  key="dash_covered")

# Apply filters
map_df = stores_df.dropna(subset=["lat","lng"]).copy() \
         if "lat" in stores_df.columns and "lng" in stores_df.columns else pd.DataFrame()

if not map_df.empty:
    map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
    map_df["lng"] = pd.to_numeric(map_df["lng"], errors="coerce")
    map_df = map_df.dropna(subset=["lat","lng"])
    if map_df.empty:
        st.info("No stores with valid coordinates to display.")
    else:
        if sel_rep != "All reps" and "rep_id" in map_df.columns:
            map_df = map_df[map_df["rep_id"] == int(sel_rep.split()[1])]
        if sel_month_label != "Full plan" and sel_month_label in PLAN_KEY_MAP:
            mkey = PLAN_KEY_MAP[sel_month_label]
            if f"{mkey}_visits" in map_df.columns:
                map_df = map_df[map_df[f"{mkey}_visits"].fillna(0) > 0]
            if sel_date != "All dates":
                dcol = f"{mkey}_dates"
                if dcol in map_df.columns:
                    map_df = map_df[map_df[dcol].apply(
                        lambda x: sel_date in parse_dates_cell(x))]
        elif sel_month_label == "Full plan" and "plan_visits" in map_df.columns:
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
                return {"Large":[46,125,50,220],"Medium":[21,101,192,220],
                        "Small":[245,127,23,220]}.get(row.get("size_tier",""),[150,150,150,180])
            elif colour_by == "Coverage status":
                return [46,125,50,200] if row.get("coverage_status")=="covered" else [198,40,40,220]
            else:
                sc = row.get("score",0) or 0
                if sc>=80: return [46,125,50,220]



                if sc>=60: return [21,101,192,220]
                if sc>=40: return [245,127,23,220]
                return [198,40,40,200]

        map_df["_color"]  = map_df.apply(get_color, axis=1)
        map_df["_radius"] = (map_df["score"].fillna(50) * 1.5) if "score" in map_df.columns else 40

        try:
            import pydeck as pdk
            layer = pdk.Layer("ScatterplotLayer", data=map_df,
                get_position="[lng, lat]", get_color="_color", get_radius="_radius",
                radius_min_pixels=4, radius_max_pixels=20, pickable=True)
            view = pdk.ViewState(latitude=float(map_df["lat"].mean()),
                                 longitude=float(map_df["lng"].mean()), zoom=11, pitch=0)
            tooltip = {
                "html": "<b>{store_name}</b><br/>Score: <b>{score}</b><br/>"
                        "Size: {size_tier}<br/>Status: {coverage_status}<br/>"
                        "Rep: {rep_id}<br/>Day: {assigned_day}",
                "style": {"backgroundColor":"#1A2B4A","color":"white",
                          "padding":"10px","borderRadius":"8px","fontSize":"13px"}
            }
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
        except Exception:
            st.map(map_df.rename(columns={"lng":"lon"})[["lat","lon"]])

        # ── Colour legend ─────────────────────────────────────────────────────
        if colour_by == "Rep route" and all_reps:
            leg_cols = st.columns(min(len(all_reps), 6))
            for i, rep in enumerate(all_reps[:6]):
                hx  = REP_COLORS[int(rep) % len(REP_COLORS)]
                cnt = len(map_df[map_df["rep_id"]==rep]) if not map_df.empty else 0
                _rl = _dash_zone_rule.get(int(rep), "")
                _rl_tag = f" ({_rl})" if _rl and _rl != "Mixed" else ""
                leg_cols[i].markdown(
                    f'<span class="legend-chip" style="background:{hx}">Rep {int(rep)}{_rl_tag} · {cnt} stores</span>',
                    unsafe_allow_html=True)
        elif colour_by == "Size tier":
            lc = st.columns(3)
            for i,(tier,col) in enumerate([("Large","#2E7D32"),("Medium","#1565C0"),("Small","#F57F17")]):
                lc[i].markdown(f'<span class="legend-chip" style="background:{col}">{tier}</span>',
                               unsafe_allow_html=True)
        elif colour_by == "Coverage status":
            lc = st.columns(2)
            lc[0].markdown('<span class="legend-chip" style="background:#2E7D32">Covered</span>',
                           unsafe_allow_html=True)
            lc[1].markdown('<span class="legend-chip" style="background:#C62828">Gap</span>',
                           unsafe_allow_html=True)
        elif colour_by == "Score":
            lc = st.columns(4)



            for i,(label,col) in enumerate([("≥80","#2E7D32"),("60–79","#1565C0"),
                                            ("40–59","#F57F17"),("<40","#C62828")]):
                lc[i].markdown(f'<span class="legend-chip" style="background:{col}">{label}</span>',
                               unsafe_allow_html=True)

        st.caption(f"Showing {len(map_df):,} stores on map")

st.markdown("---")

# ── ROUTES TABLE ──────────────────────────────────────────────────────────────
st.html('<div class="section-title">Route detail</div>')
st.caption("Select rep, month and date to see stores and visit schedule for a specific day.")

tr1, tr2, tr3, tr4 = st.columns(4)
with tr1:
    tbl_rep = st.selectbox("Rep",
        ["All reps"] + [f"Rep {int(r)}" for r in all_reps], key="tbl_rep_dash")
with tr2:
    tbl_month_label = st.selectbox("Month",
        ["Full plan"] + PLAN_LABELS, key="tbl_month_dash")
with tr3:
    if tbl_month_label != "Full plan" and tbl_month_label in PLAN_KEY_MAP:
        _tmkey  = PLAN_KEY_MAP[tbl_month_label]
        _tdates = get_dates_for_month(stores_df, _tmkey)
        tbl_date = st.selectbox("Date", _tdates, key="tbl_date_dash")
    else:
        tbl_date = "All dates"
        st.selectbox("Date", ["All dates"], disabled=True, key="tbl_date_empty")
with tr4:
    route_filter = st.selectbox("Route status",
        ["Recommended stores","Not in route","All stores"], key="tbl_route_filter")

# Apply filters
if route_filter == "Recommended stores" and "plan_visits" in stores_df.columns:
    route_df = stores_df[stores_df["plan_visits"] > 0].copy()
elif route_filter == "Not in route" and "plan_visits" in stores_df.columns:
    route_df = stores_df[stores_df["plan_visits"] == 0].copy()
else:
    route_df = stores_df.copy()

if tbl_rep != "All reps" and "rep_id" in route_df.columns:
    route_df = route_df[route_df["rep_id"] == int(tbl_rep.split()[1])]

if tbl_month_label != "Full plan" and tbl_month_label in PLAN_KEY_MAP:
    tmkey = PLAN_KEY_MAP[tbl_month_label]
    vcol  = f"{tmkey}_visits"
    dcol  = f"{tmkey}_dates"



    if vcol in route_df.columns:
        route_df = route_df[route_df[vcol].fillna(0) > 0]
    if tbl_date != "All dates" and dcol in route_df.columns:
        route_df = route_df[route_df[dcol].apply(
            lambda x: tbl_date in parse_dates_cell(x))]

if "day_visit_order" in route_df.columns:
    route_df = route_df.sort_values(
        ["rep_id","assigned_day","day_visit_order"],
        na_position="last"
    ).reset_index(drop=True)

# Build display columns
show_cols = [c for c in [
    "rep_id","assigned_day","day_visit_order","store_name","category",
    "size_tier","score","visits_per_month","plan_visits","visit_duration_min",
    "coverage_status","rating","review_count","phone","opening_hours","address","city"
] if c in route_df.columns]

# Add the dates column for the selected month
if tbl_month_label != "Full plan" and tbl_month_label in PLAN_KEY_MAP:
    dcol = f"{PLAN_KEY_MAP[tbl_month_label]}_dates"
    if dcol in route_df.columns and dcol not in show_cols:
        show_cols.insert(3, dcol)

rename_map = {
    "rep_id":"Rep","assigned_day":"Day","day_visit_order":"Visit #",
    "store_name":"Store","category":"Sub-channel","size_tier":"Size",
    "score":"Score","visits_per_month":"Visits/Mo","plan_visits":"Plan Visits",
    "visit_duration_min":"Duration (min)","coverage_status":"Status",
    "rating":"Rating","review_count":"Reviews",
    "phone":"Phone","opening_hours":"Hours","address":"Address","city":"City",
}
if tbl_month_label != "Full plan" and tbl_month_label in PLAN_KEY_MAP:
    rename_map[f"{PLAN_KEY_MAP[tbl_month_label]}_dates"] = f"{tbl_month_label} Dates"

if not route_df.empty:
    # ── Daily budget metrics when specific date selected ──────────────────────
    if tbl_date != "All dates" and "visit_duration_min" in route_df.columns:
        exec_t = int(route_df["visit_duration_min"].fillna(0).sum())
        travel_t = 0
        day_ord  = route_df.sort_values("day_visit_order").to_dict("records") \
                   if "day_visit_order" in route_df.columns else []
        if len(day_ord) > 1:
            for i in range(1, len(day_ord)):
                s_a, s_b = day_ord[i-1], day_ord[i]
                try:



                    la1 = float(s_a.get("lat",0) or 0)
                    ln1 = float(s_a.get("lng",0) or 0)
                    la2 = float(s_b.get("lat",0) or 0)
                    ln2 = float(s_b.get("lng",0) or 0)
                    if la1 and la2:
                        p = math.pi/180
                        a = (math.sin((la2-la1)*p/2)**2 +
                             math.cos(la1*p)*math.cos(la2*p)*math.sin((ln2-ln1)*p/2)**2)
                        travel_t += (2*6371*math.asin(math.sqrt(a))/30)*60
                except: pass
        travel_t = round(travel_t)
        break_t  = 30
        total_t  = exec_t + travel_t + break_t
        flag     = " " if total_t <= 550 else (" " if total_t <= 600 else " ")
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Stores", len(route_df))
        m2.metric("Execution", f"{exec_t} min")
        m3.metric("Travel", f"{travel_t} min")
        m4.metric("Break", f"{break_t} min")
        m5.metric(f"{flag} Total / cap", f"{total_t} / 550 min")

    df_show = route_df[[c for c in show_cols if c in route_df.columns]].rename(columns=rename_map)
    st.dataframe(df_show, use_container_width=True, height=420,
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
        })
    st.caption(f"Showing {len(route_df):,} stores · {tbl_date if tbl_date != 'All dates' else 'all dates'}")
else:
    st.info("No stores match the current filters.")

st.markdown("---")

# ── GAP REPORT ────────────────────────────────────────────────────────────────
if "coverage_status" in stores_df.columns:
    gaps = stores_df[stores_df["coverage_status"]=="gap"]
    if not gaps.empty:
        st.html('<div class="section-title">Top gap opportunities</div>')
        if "score" in gaps.columns:
            gaps = gaps.sort_values("score", ascending=False)
        gap_cols = [c for c in [
            "store_name","category","score","size_tier","visits_per_month",
            "rating","review_count","address","city"
        ] if c in gaps.columns]
        st.dataframe(gaps[gap_cols].head(50).reset_index(drop=True),
            use_container_width=True, height=300,
            column_config={"score": st.column_config.ProgressColumn(



                "Score", min_value=0, max_value=100)})

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.html('<div class="section-title">Downloads</div>')
safe_name = f"{snap['name']}_{snap.get('category','')}_{snap['run_date']}".replace(" ","_")
col1, col2 = st.columns(2)
with col1:
    st.download_button("  Full stores CSV",
        stores_df.to_csv(index=False),
        f"{safe_name}_stores.csv", "text/csv")
with col2:
    # Export route plan only
    route_export = stores_df[stores_df["plan_visits"].fillna(0) > 0] \
                   if "plan_visits" in stores_df.columns else stores_df
    st.download_button("  Route plan CSV",
        route_export.to_csv(index=False),
        f"{safe_name}_route_plan.csv", "text/csv")
