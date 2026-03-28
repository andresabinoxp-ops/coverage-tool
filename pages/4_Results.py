import streamlit as st
import pandas as pd
import json
import datetime

st.set_page_config(page_title="Results - Coverage Tool", page_icon="📊", layout="wide")

st.markdown("""
<style>
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
.kpi-card {
    background: #F0F4F8; border: 1px solid #D0DCF0; border-top: 4px solid #1565C0;
    border-radius: 8px; padding: 1.2rem; text-align: center;
}
.kpi-value { font-size: 1.8rem; font-weight: 800; color: #1A2B4A; line-height: 1; }
.kpi-sub   { font-size: 0.75rem; color: #6B7280; margin-top: 0.3rem; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.05em; }
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white; border-radius: 6px; font-weight: 600;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📊 Results</h2>
    <p>Scored store universe, coverage analysis and rep planning</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.get("run_results"):
    st.warning("No results yet. Run the pipeline first.")
    st.stop()

res        = st.session_state["run_results"]
all_stores = res["all_stores"]
gap_stores = res["gap_stores"]
market     = st.session_state.get("last_market", "Market")
cfg        = st.session_state.get("market_config", {})

st.markdown(f"**Market:** {market}")

# ── KEY METRICS ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Market overview</div>', unsafe_allow_html=True)

total_universe  = len(all_stores)
currently_covered = sum(1 for s in all_stores if s.get("covered"))
total_gaps      = len(gap_stores)
cov_pct         = round(currently_covered / max(total_universe, 1) * 100, 1)

# Route universe = stores assigned to a rep (both covered and gap)
route_stores    = [s for s in all_stores if s.get("rep_id", 0) and s.get("rep_id", 0) > 0]
new_stores      = [s for s in route_stores if not s.get("covered")]  # gap stores in routes = new
monthly_visits  = sum(s.get("visits_per_month", 0) for s in route_stores)
annual_visits   = sum(s.get("annual_visits", 0) for s in route_stores)

cols = st.columns(6)
for col, val, label, color in [
    (cols[0], f"{total_universe:,}",      "Total universe",        "#1565C0"),
    (cols[1], f"{currently_covered:,}",   "Currently covered",     "#2E7D32"),
    (cols[2], f"{total_gaps:,}",          "Gap stores",            "#C62828"),
    (cols[3], f"{cov_pct}%",              "Coverage rate",         "#1565C0"),
    (cols[4], f"{len(new_stores):,}",     "New stores in routes",  "#E65100"),
    (cols[5], f"{monthly_visits:,.0f}",   "Planned visits / month","#6A1B9A"),
]:
    col.markdown(f"""
    <div class="kpi-card" style="border-top-color:{color}">
        <div class="kpi-value" style="color:{color}">{val}</div>
        <div class="kpi-sub">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ── GEOCODING SUMMARY (if available) ─────────────────────────────────────────
geo_summary = res.get("geocode_summary")
if geo_summary:
    ok  = geo_summary.get("ok", 0)
    fail= geo_summary.get("failed", 0)
    if fail > 0:
        st.warning(
            f"📍 Geocoding: {ok} stores located successfully · "
            f"{fail} stores failed (no lat/lng) — these are treated as gaps since their location could not be confirmed. "
            "Check addresses in your portfolio CSV."
        )
    else:
        st.success(f"📍 Geocoding: all {ok} portfolio stores located successfully.")

# ── SIZE DISTRIBUTION ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Store size distribution</div>', unsafe_allow_html=True)

size_colors = {"Large":"#2E7D32","Medium":"#1565C0","Small":"#F57F17"}
fc = st.columns(3)
for i, tier in enumerate(["Large","Medium","Small"]):
    tier_stores = [s for s in all_stores if s.get("size_tier") == tier]
    cnt     = len(tier_stores)
    covered = sum(1 for s in tier_stores if s.get("covered"))
    gaps_t  = cnt - covered
    vpm     = sum(s.get("visits_per_month",0) for s in tier_stores)
    col     = size_colors[tier]
    fc[i].markdown(f"""
    <div style="background:#F8F9FA;border:1px solid #E0E0E0;border-top:4px solid {col};
    border-radius:8px;padding:1rem;text-align:center">
        <div style="font-size:1.6rem;font-weight:800;color:#1A2B4A">{cnt:,}</div>
        <div style="font-size:0.78rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">{tier}</div>
        <div style="font-size:0.75rem;color:#9E9E9E;margin-top:4px">
            {covered} covered · {gaps_t} gaps · {vpm:.0f} visits/mo
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── REP PLANNING PANEL ────────────────────────────────────────────────────────
rep_rec = res.get("rep_recommendation")
if rep_rec:
    st.markdown('<div class="section-title">Rep planning</div>', unsafe_allow_html=True)

    mode        = rep_rec.get("mode","fixed")
    rec_reps    = rep_rec.get("recommended_reps", rep_rec.get("rep_count", 0))
    cur_reps    = rep_rec.get("current_reps", 0)
    shortfall   = rep_rec.get("shortfall", 0)
    total_mins  = rep_rec.get("total_minutes_needed", 0)
    monthly_cap = rep_rec.get("monthly_cap_per_rep", 0)
    daily_mins  = rep_rec.get("daily_minutes", 480)
    work_days   = rep_rec.get("working_days", 22)
    speed       = rep_rec.get("avg_speed_kmh", 30)
    break_mins  = rep_rec.get("break_minutes", 30)

    m1, m2, m3, m4 = st.columns(4)
    if mode == "recommended":
        m1.metric("Recommended reps", rec_reps)
    else:
        m1.metric("Fixed reps", rec_reps)
    m2.metric("Total time needed / month", f"{total_mins:,.0f} min",
        help="Sum of visit durations + travel time for all route stores")
    m3.metric("Rep capacity / month", f"{monthly_cap:,} min",
        help=f"{daily_mins} min/day (incl. {break_mins} min break) × {work_days} days")
    if cur_reps > 0:
        m4.metric("vs Current headcount",
            f"{'+' if shortfall > 0 else ''}{shortfall} reps",
            delta_color="inverse" if shortfall > 0 else "normal")
    else:
        m4.metric("Current headcount", "Not provided",
            help="Enter current rep count in Configure to see comparison.")

    if monthly_cap > 0 and total_mins > 0 and rec_reps > 0:
        util = round(total_mins / (rec_reps * monthly_cap) * 100)
        st.caption(
            f"Average utilisation per rep: {util}% · "
            f"{daily_mins} min/day total · {break_mins} min break · "
            f"{work_days} working days · {speed} km/h avg travel speed"
        )

    # Shortfall / surplus message
    if cur_reps > 0 and shortfall > 0:
        st.error(
            f"⚠️ {shortfall} additional rep{'s' if shortfall!=1 else ''} recommended. "
            f"With {cur_reps} reps, each would need "
            f"{total_mins/max(cur_reps,1):,.0f} min/month "
            f"({total_mins/max(cur_reps,1)/max(monthly_cap,1)*100:.0f}% utilisation) — over capacity."
        )
    elif cur_reps > 0 and shortfall < 0:
        st.success(
            f"✅ {abs(shortfall)} rep{'s' if abs(shortfall)!=1 else ''} to spare. "
            f"Your {cur_reps} reps can handle this market at "
            f"{total_mins/max(cur_reps,1):,.0f} min/month each "
            f"({total_mins/max(cur_reps,1)/max(monthly_cap,1)*100:.0f}% utilisation)."
        )

    # ── Zone summary ──────────────────────────────────────────────────────────
    zone_centres = rep_rec.get("zone_centres", [])
    if zone_centres:
        st.markdown("**Rep territory summary:**")
        st.caption(
            "Each zone is one rep's geographic territory. "
            "'Recommended stores' = stores assigned to this rep's monthly route (covered + new gap stores)."
        )

        # Enrich zone data with store-level breakdown
        zone_rows = []
        for z in zone_centres:
            zid         = z.get("zone", 0)
            zone_s      = [s for s in all_stores if s.get("rep_id") == zid]
            z_covered   = sum(1 for s in zone_s if s.get("covered"))
            z_new       = sum(1 for s in zone_s if not s.get("covered"))
            z_vpm       = sum(s.get("visits_per_month", 0) for s in zone_s)
            t_needed    = z.get("time_needed_min", 0)
            cap         = z.get("capacity_min", monthly_cap)
            util        = z.get("utilisation_pct", round(t_needed/max(cap,1)*100))
            zone_rows.append({
                "Rep":                  zid,
                "Total stores":         len(zone_s),
                "Currently covered":    z_covered,
                "Recommended stores":   len(zone_s),
                "New stores in route":  z_new,
                "Visits / month":       round(z_vpm),
                "Time needed (min)":    round(t_needed),
                "Capacity (min)":       round(cap),
                "Utilisation %":        util,
            })

        zdf = pd.DataFrame(zone_rows)
        st.dataframe(zdf, use_container_width=True, hide_index=True,
            column_config={
                "Utilisation %": st.column_config.ProgressColumn(
                    "Utilisation %", min_value=0, max_value=100, format="%d%%"),
            })

    # ── Rep workload table ────────────────────────────────────────────────────
    st.markdown("**Rep workload breakdown:**")
    rep_rows = {}
    for s in all_stores:
        rid = s.get("rep_id", 0)
        if not rid or rid == 0: continue
        if rid not in rep_rows:
            rep_rows[rid] = {
                "Rep":                    rid,
                "Stores visited / month": 0,
                "Current stores":         0,
                "New stores (gap)":       0,
                "Time needed (min)":      0.0,
            }
        rep_rows[rid]["Stores visited / month"] += 1
        if s.get("covered"):
            rep_rows[rid]["Current stores"] += 1
        else:
            rep_rows[rid]["New stores (gap)"] += 1
        rep_rows[rid]["Time needed (min)"] += (
            s.get("visits_per_month", 1) * s.get("visit_duration_min", 25)
        )

    if rep_rows:
        rdf = pd.DataFrame(list(rep_rows.values())).sort_values("Rep")
        rdf["Time needed (min)"]    = rdf["Time needed (min)"].round(0).astype(int)
        rdf["Capacity (min)"]       = monthly_cap
        rdf["Utilisation %"]        = (rdf["Time needed (min)"] / max(monthly_cap,1) * 100).round(0).astype(int)
        # Reorder columns: Rep | Stores visited/month | Current stores | New stores (gap) | Time needed | Capacity | Utilisation
        rdf = rdf.rename(columns={"Stores visited / month": "Stores visited / month"})
        col_order = [c for c in [
            "Rep",
            "Stores visited / month",
            "Current stores",
            "New stores (gap)",
            "Time needed (min)",
            "Capacity (min)",
            "Utilisation %",
        ] if c in rdf.columns]
        st.dataframe(rdf[col_order], use_container_width=True, hide_index=True,
            column_config={
                "Utilisation %": st.column_config.ProgressColumn(
                    "Utilisation %", min_value=0, max_value=100, format="%d%%"),
            })

# ── GAP OPPORTUNITIES ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">Top gap opportunities</div>', unsafe_allow_html=True)
st.caption("Uncovered stores ranked by score — these are candidate new distribution points.")

high_gaps = [s for s in gap_stores if s.get("score", 0) >= 40]
if high_gaps:
    gdf   = pd.DataFrame(high_gaps[:50])
    gcols = [c for c in ["store_name","category","score","size_tier",
                          "visits_per_month","rating","review_count","address","city"] if c in gdf.columns]
    gdf   = gdf[gcols].sort_values("score", ascending=False).reset_index(drop=True)
    gdf.columns = [c.replace("_"," ").title() for c in gdf.columns]
    st.dataframe(gdf, use_container_width=True, height=320,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})
else:
    st.info("No gap stores with score above 40.")

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">Download results</div>', unsafe_allow_html=True)

mkt_safe = market.replace(" ","_").replace("-","_")
run_date = datetime.date.today().strftime("%Y-%m-%d")

col1, col2, col3 = st.columns(3)
with col1:
    st.download_button("📄 Full scored universe CSV",
        pd.DataFrame(all_stores).to_csv(index=False),
        f"scored_universe_{mkt_safe}.csv", "text/csv")
with col2:
    st.download_button("🎯 Gap report CSV",
        pd.DataFrame(gap_stores).to_csv(index=False),
        f"gap_report_{mkt_safe}.csv", "text/csv")
with col3:
    features = [
        {"type":"Feature",
         "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
         "properties":{k:s.get(k) for k in ["store_name","score","size_tier",
             "visits_per_month","rep_id","coverage_status","category"]}}
        for s in all_stores if s.get("lat") and s.get("lng")
    ]
    st.download_button("🗺 Routes GeoJSON",
        json.dumps({"type":"FeatureCollection","features":features}, indent=2),
        f"rep_routes_{mkt_safe}.geojson", "application/json")

st.markdown("---")
st.markdown('<div class="section-title">Dashboard snapshot files</div>', unsafe_allow_html=True)
st.caption("Download these two files and upload them to the Dashboard page.")

summary_data = {
    "market_name":           [market],
    "run_date":              [run_date],
    "total_stores":          [total_universe],
    "covered_stores":        [currently_covered],
    "gap_stores":            [total_gaps],
    "coverage_rate":         [cov_pct],
    "new_stores_in_routes":  [len(new_stores)],
    "planned_visits_month":  [monthly_visits],
    "annual_visits":         [annual_visits],
    "large_stores":          [sum(1 for s in all_stores if s.get("size_tier")=="Large")],
    "medium_stores":         [sum(1 for s in all_stores if s.get("size_tier")=="Medium")],
    "small_stores":          [sum(1 for s in all_stores if s.get("size_tier")=="Small")],
}
summary_df = pd.DataFrame(summary_data)

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.download_button("⬇️ Stores snapshot (upload to Dashboard)",
        pd.DataFrame(all_stores).to_csv(index=False),
        f"{mkt_safe}_{run_date}_stores.csv", "text/csv")
with col_s2:
    st.download_button("⬇️ Summary snapshot (upload to Dashboard)",
        summary_df.to_csv(index=False),
        f"{mkt_safe}_{run_date}_summary.csv", "text/csv")
st.info("Upload both files to the Dashboard page. Admin manages the market library from there.")
