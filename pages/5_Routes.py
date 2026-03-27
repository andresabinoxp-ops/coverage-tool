import streamlit as st
import pandas as pd
import json
import math

st.set_page_config(page_title="Routes - Coverage Tool", page_icon="🗺️", layout="wide")

st.markdown("""
<style>
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
    text-align: center; font-weight: 700; margin: 4px;
    font-size: 0.85rem; display: inline-block;
}
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white;
    border-radius: 6px; font-weight: 600;
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
thresholds = cfg.get("thresholds", {"weekly":80,"fortnightly":60,"monthly":40})

st.markdown(f"""
<div class="page-header">
    <h2>🗺️ Rep Routes Map</h2>
    <p>Market: {market}</p>
</div>
""", unsafe_allow_html=True)

REP_COLORS = [
    [21,101,192],[46,125,50],[230,81,0],[136,14,79],[0,96,100],
    [74,20,140],[183,28,28],[0,77,64],[62,39,35],[38,50,56]
]
FREQ_COLORS = {
    "Large":  [46,125,50,220],
    "Medium": [21,101,192,220],
    "Small":  [245,127,23,220],
    # legacy support
    "weekly":      [46,125,50,220],
    "fortnightly": [21,101,192,220],
    "monthly":     [245,127,23,220],
    "bi-weekly":   [191,54,12,200],
}
STATUS_COLORS = {
    "covered": [46,125,50,200],
    "gap":     [198,40,40,220],
}

def get_color(s, colour_by):
    if colour_by == "Rep route":
        c = REP_COLORS[(s.get("rep_id",0) or 0) % len(REP_COLORS)]
        return [c[0],c[1],c[2],200]
    elif colour_by == "Visit frequency":
        tier = s.get("size_tier","") or s.get("visit_frequency","")
        return FREQ_COLORS.get(tier, [150,150,150,180])
    elif colour_by == "Coverage status":
        return STATUS_COLORS.get(s.get("coverage_status","covered"), [150,150,150,180])
    else:
        sc = s.get("score",0)
        if sc >= 80: return [46,125,50,220]
        if sc >= 60: return [21,101,192,220]
        if sc >= 40: return [245,127,23,220]
        return [198,40,40,200]

def build_rep_dataframe(stores, rep_id=None):
    if rep_id is not None:
        filtered = [s for s in stores if s.get("rep_id") == rep_id]
    else:
        filtered = [s for s in stores if s.get("rep_id", 0) > 0]
    if not filtered:
        return pd.DataFrame()

    filtered = sorted(filtered, key=lambda x: x.get("score",0), reverse=True)

    rows = []
    fortnightly_count = 0
    monthly_count     = 0

    for i, s in enumerate(filtered):
        tier   = s.get("size_tier","") or s.get("visit_frequency","")
        visits = s.get("visits_per_month", s.get("calls_per_month",1))

        # Recommended visit week based on visits per month
        if visits >= 4:
            rec_week = "Every week (W1, W2, W3, W4)"
        elif visits >= 2:
            fortnightly_count += 1
            rec_week = "Week 1 & Week 3" if fortnightly_count % 2 == 1 else "Week 2 & Week 4"
        elif visits >= 1:
            monthly_count += 1
            rec_week = f"Week {(monthly_count % 4) + 1}"
        else:
            rec_week = "Every other month"
        freq = tier

        rows.append({
            "visit_order":            i + 1,
            "store_name":             s.get("store_name",""),
            "category":               s.get("category","").replace("_"," ").title(),
            "score":                  s.get("score",0),
            "size_tier":              s.get("size_tier","") or s.get("visit_frequency",""),
            "visits_per_month":       s.get("visits_per_month", s.get("calls_per_month",0)),
            "visit_duration_min":     s.get("visit_duration_min",0),
            "recommended_visit_week": rec_week,
            "calls_per_month":        s.get("visits_per_month", s.get("calls_per_month",0)),
            "coverage_status":        s.get("coverage_status",""),
            "rating":                 s.get("rating",0),
            "review_count":           s.get("review_count",0),
            "phone":                  s.get("phone",""),
            "opening_hours":          s.get("opening_hours",""),
            "address":                s.get("address",""),
            "city":                   s.get("city",""),
            "lat":                    s.get("lat",""),
            "lng":                    s.get("lng",""),
            "annual_sales_usd":       s.get("annual_sales_usd",0),
            "lines_per_store":        s.get("lines_per_store",0),
            "rep_id":                 s.get("rep_id",0),
        })
    return pd.DataFrame(rows)

# ── MAP CONTROLS ──────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    colour_by = st.selectbox("Colour markers by",
        ["Rep route","Visit frequency","Coverage status","Score"])
with col2:
    show_gaps    = st.checkbox("Show gap stores",     value=True)
    show_covered = st.checkbox("Show covered stores", value=True)
with col3:
    min_score = st.slider("Min score to show", 0, 100, 0)

map_stores = [
    s for s in all_stores
    if s.get("lat") and s.get("lng")
    and s.get("score",0) >= min_score
    and ((show_gaps    and s.get("coverage_status")=="gap") or
         (show_covered and s.get("covered")))
]
st.caption(f"Showing {len(map_stores):,} stores on map")

map_data = [{
    "lat":s["lat"],"lng":s["lng"],
    "name":s.get("store_name",""),
    "score":s.get("score",0),
    "freq":s.get("visit_frequency",""),
    "status":s.get("coverage_status",""),
    "rep":s.get("rep_id",0),
    "category":s.get("category",""),
    "phone":s.get("phone",""),
    "color":get_color(s,colour_by),
    "radius":max(30,s.get("score",0)*1.5),
} for s in map_stores]

try:
    import pydeck as pdk
    df_map = pd.DataFrame(map_data)
    if not df_map.empty:
        layer = pdk.Layer("ScatterplotLayer", data=df_map,
            get_position="[lng, lat]", get_color="color", get_radius="radius",
            radius_min_pixels=4, radius_max_pixels=20, pickable=True)
        view = pdk.ViewState(
            latitude=df_map["lat"].mean(),
            longitude=df_map["lng"].mean(),
            zoom=11, pitch=0)
        tooltip = {
            "html":"<b>{name}</b><br/>Score: <b>{score}</b><br/>Freq: {freq}<br/>Status: {status}<br/>Rep: {rep}<br/>Phone: {phone}",
            "style":{"backgroundColor":"#1A2B4A","color":"white","padding":"10px","borderRadius":"8px","fontSize":"13px"}
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    else:
        st.info("No stores with coordinates to display.")
except ImportError:
    if map_data:
        df_map = pd.DataFrame(map_data)
        st.map(df_map.rename(columns={"lng":"lon"})[["lat","lon"]])
    else:
        st.info("No stores to display.")

# ── LEGEND ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Legend</div>', unsafe_allow_html=True)
if colour_by == "Rep route":
    reps = sorted(set(s.get("rep_id",0) for s in map_stores if s.get("rep_id")))
    if reps:
        cols = st.columns(min(len(reps),5))
        for i,rep in enumerate(reps):
            rs  = [s for s in map_stores if s.get("rep_id")==rep]
            tc  = sum(s.get("calls_per_month",0) for s in rs)
            c   = REP_COLORS[rep % len(REP_COLORS)]
            hx  = "#{:02x}{:02x}{:02x}".format(c[0],c[1],c[2])
            cols[i%5].markdown(
                f'<div class="rep-chip" style="background:{hx}">Rep {rep}<br>'
                f'<small>{len(rs)} stores · {tc:.0f} calls/mo</small></div>',
                unsafe_allow_html=True)
elif colour_by == "Visit frequency":
    lc = st.columns(4)
    for i,(label,desc,col) in enumerate([
        ("Weekly","Score ≥ 80 · 4 calls/mo","#2E7D32"),
        ("Fortnightly","Score 60-79 · 2 calls/mo","#1565C0"),
        ("Monthly","Score 40-59 · 1 call/mo","#F57F17"),
        ("Bi-weekly","Score < 40 · 0.5 calls/mo","#BF360C"),
    ]):
        lc[i].markdown(f'<div class="rep-chip" style="background:{col}">{label}<br><small>{desc}</small></div>',unsafe_allow_html=True)
elif colour_by == "Coverage status":
    lc = st.columns(2)
    lc[0].markdown('<div class="rep-chip" style="background:#2E7D32">Covered<br><small>In your portfolio</small></div>',unsafe_allow_html=True)
    lc[1].markdown('<div class="rep-chip" style="background:#C62828">Gap<br><small>Not yet covered</small></div>',unsafe_allow_html=True)

st.markdown("---")

# ── DOWNLOADS PER REP ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Download rep route files</div>', unsafe_allow_html=True)
st.caption("Each file includes: visit order, recommended visit week, lat/lng, phone, opening hours, score and all store details.")

all_reps = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id",0) > 0))
mkt_safe = market.replace(" ","_").replace("-","_")

if all_reps:
    all_df = build_rep_dataframe(all_stores)
    if not all_df.empty:
        st.download_button(
            "⬇️ Download all reps — combined CSV",
            all_df.to_csv(index=False),
            f"all_reps_{mkt_safe}.csv",
            "text/csv",
            key="dl_all_reps"
        )

    st.markdown("**Individual rep files:**")
    n_cols   = min(len(all_reps), 4)
    rep_cols = st.columns(n_cols)

    for i, rep in enumerate(all_reps):
        rep_df = build_rep_dataframe(all_stores, rep_id=rep)
        if rep_df.empty:
            continue
        sc = sum(rep_df["calls_per_month"])
        c  = REP_COLORS[rep % len(REP_COLORS)]
        hx = "#{:02x}{:02x}{:02x}".format(c[0],c[1],c[2])
        with rep_cols[i % n_cols]:
            st.markdown(f"""
            <div style="background:{hx}18;border:1.5px solid {hx};
            border-radius:8px;padding:10px 12px;margin-bottom:8px;text-align:center">
                <div style="font-weight:700;color:#1A2B4A">Rep {rep}</div>
                <div style="font-size:0.78rem;color:#6B7280">{len(rep_df)} stores · {sc:.0f} calls/mo</div>
            </div>""", unsafe_allow_html=True)
            st.download_button(
                f"⬇️ Rep {rep} CSV",
                rep_df.to_csv(index=False),
                f"rep_{rep}_{mkt_safe}.csv",
                "text/csv",
                key=f"dl_rep_{rep}"
            )

st.markdown("---")

# ── REP DETAIL TABLE ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Rep route detail table</div>', unsafe_allow_html=True)
st.caption("Full call plan with visit order, recommended visit week, lat/lng and contact details.")

sel = st.selectbox("Select rep", ["All reps"] + [f"Rep {r}" for r in all_reps])

if sel == "All reps":
    display_df = build_rep_dataframe(all_stores)
else:
    rep_num    = int(sel.split(" ")[1])
    display_df = build_rep_dataframe(all_stores, rep_id=rep_num)

if not display_df.empty:
    show_cols = [c for c in [
        "visit_order","store_name","category","score","visit_frequency",
        "recommended_visit_week","calls_per_month","coverage_status",
        "rating","review_count","phone","opening_hours",
        "address","city","lat","lng","annual_sales_usd","lines_per_store","rep_id"
    ] if c in display_df.columns]

    rename_map = {
        "visit_order":"# Order","store_name":"Store","category":"Category",
        "score":"Score","visit_frequency":"Frequency",
        "recommended_visit_week":"Recommended Week","calls_per_month":"Calls/Mo",
        "coverage_status":"Status","rating":"Rating","review_count":"Reviews",
        "phone":"Phone","opening_hours":"Opening Hours","address":"Address",
        "city":"City","lat":"Latitude","lng":"Longitude",
        "annual_sales_usd":"Sales $","lines_per_store":"Lines","rep_id":"Rep",
    }

    df_show = display_df[show_cols].rename(columns=rename_map)
    st.dataframe(
        df_show, use_container_width=True, height=460,
        column_config={
            "Score":   st.column_config.ProgressColumn("Score",   min_value=0, max_value=100),
            "Rating":  st.column_config.NumberColumn("Rating",    format="%.1f"),
            "Sales $": st.column_config.NumberColumn("Sales $",   format="$%,.0f"),
            "Latitude":  st.column_config.NumberColumn("Latitude",  format="%.5f"),
            "Longitude": st.column_config.NumberColumn("Longitude", format="%.5f"),
        }
    )

    if sel != "All reps":
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total stores",      len(display_df))
        m2.metric("Calls per month",   f"{display_df['calls_per_month'].sum():.0f}")
        m3.metric("Weekly stores",     len(display_df[display_df["visit_frequency"]=="weekly"]))
        m4.metric("Gap opportunities", len(display_df[display_df["coverage_status"]=="gap"]))
else:
    st.info("No stores found for this selection.")

# ── GEOJSON ───────────────────────────────────────────────────────────────────
st.markdown("---")
features = [
    {"type":"Feature",
     "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
     "properties":{k:s.get(k) for k in ["store_name","score","visit_frequency","rep_id",
         "coverage_status","category","phone","opening_hours","address","calls_per_month"]}}
    for s in all_stores if s.get("lat") and s.get("lng")
]
st.download_button(
    "⬇️ Full routes GeoJSON (all reps)",
    json.dumps({"type":"FeatureCollection","features":features}, indent=2),
    f"rep_routes_{mkt_safe}.geojson",
    "application/json"
)
