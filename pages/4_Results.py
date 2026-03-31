import streamlit as st
import pandas as pd
import json
import datetime

st.set_page_config(page_title="Results - Coverage Tool", page_icon=" ", layout="wide")

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
    <h2>  Results</h2>
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
st.markdown('<div class="section-title">Results Output</div>', unsafe_allow_html=True)

total_universe    = len(all_stores)
current_coverage  = sum(1 for s in all_stores if s.get("covered"))
total_gaps        = len(gap_stores)

# Route universe = stores ACTUALLY in the route plan (plan_visits > 0)
route_stores      = [s for s in all_stores if s.get("plan_visits", 0) > 0]
proposed_coverage = len(route_stores)
proposed_rate     = round(proposed_coverage / max(total_universe, 1) * 100, 1)
monthly_visits    = sum(s.get("visits_per_month", 0) for s in route_stores)

# Stores removed from original coverage (current coverage not in route plan)
removed_stores    = [s for s in all_stores if s.get("covered") and s.get("plan_visits",0) == 0]
# New stores added from gap list (gap stores now in route plan)
new_added_stores  = [s for s in route_stores if not s.get("covered")]

cols = st.columns(3)
for col, val, label, color in [
    (cols[0], f"{total_universe:,}",    "Total Universe",    "#1565C0"),
    (cols[1], f"{current_coverage:,}",  "Current Coverage",  "#2E7D32"),
    (cols[2], f"{proposed_coverage:,}", "Proposed Coverage", "#1A2B4A"),
]:
    col.markdown(f"""
    <div class="kpi-card" style="border-top-color:{color}">
        <div class="kpi-value" style="color:{color}">{val}</div>
        <div class="kpi-sub">{label}</div>
    </div>""", unsafe_allow_html=True)

cols2 = st.columns(3)
for col, val, label, color in [
    (cols2[0], f"{proposed_rate}%",          "Proposed Coverage Rate",              "#1565C0"),
    (cols2[1], f"{len(removed_stores):,}",   "Stores Removed from Original Coverage","#C62828"),
    (cols2[2], f"{len(new_added_stores):,}", "New Stores Added from Gap List",      "#2E7D32"),



]:
    col.markdown(f"""
    <div class="kpi-card" style="border-top-color:{color}">
        <div class="kpi-value" style="color:{color}">{val}</div>
        <div class="kpi-sub">{label}</div>
    </div>""", unsafe_allow_html=True)

col_pv = st.columns(1)[0]
col_pv.markdown(f"""
<div class="kpi-card" style="border-top-color:#6A1B9A">
    <div class="kpi-value" style="color:#6A1B9A">{monthly_visits:,.0f}</div>
    <div class="kpi-sub">Planned Visits / Month</div>
</div>""", unsafe_allow_html=True)

st.markdown("")

# ── GEOCODING SUMMARY (if available) ─────────────────────────────────────────
geo_summary = res.get("geocode_summary")
if geo_summary:
    ok  = geo_summary.get("ok", 0)
    fail= geo_summary.get("failed", 0)
    if fail > 0:
        st.warning(
            f"  Geocoding: {ok} stores located successfully · "
            f"{fail} stores failed (no lat/lng) — these are treated as gaps since their location could not be confirmed. "
            "Check addresses in your Current Coverage CSV."
        )
    else:
        st.success(f"  Geocoding: all {ok} Current Coverage stores located successfully.")

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



    # 2-month plan capacity
    plan_months_sess = st.session_state.get("route_plan_months", {})
    plan_period = plan_months_sess.get("plan_period", len(plan_months_sess.get("month_keys", ["m1","m2"])))
    plan_period = max(plan_period, 1)
    plan_cap = monthly_cap * plan_period

    m1, m2, m3, m4 = st.columns(4)
    if mode == "recommended":
        m1.metric("Recommended reps", rec_reps)
    else:
        m1.metric("Fixed reps", rec_reps)
    m2.metric("Time needed / month", f"{total_mins:,.0f} min",
        help="visits_per_month × duration per store — monthly estimate used for rep count.")
    m3.metric("Rep capacity / month", f"{monthly_cap:,} min",
        help=f"{daily_mins} min/day (incl. {break_mins} min break) × {work_days} days")
    if cur_reps > 0:
        m4.metric("vs Current headcount",
            f"{'+' if shortfall > 0 else ''}{shortfall} reps",
            delta_color="inverse" if shortfall > 0 else "normal")
    else:
        m4.metric("Current headcount", "Not provided",
            help="Enter current rep count in Configure to see comparison.")

    # Calculate actual utilisation from plan_visits (what was actually routed)
    actual_plan_time = sum(
        s.get("plan_visits",0) * s.get("visit_duration_min",25)
        for s in all_stores if s.get("plan_visits",0) > 0
    )
    # plan_visits is already the TOTAL across the full plan period
    # monthly equivalent = total / plan_period
    actual_monthly   = actual_plan_time / max(plan_period, 1)
    total_capacity   = rec_reps * monthly_cap if rec_reps > 0 else monthly_cap

    if total_capacity > 0 and actual_monthly > 0 and rec_reps > 0:
        util = round(actual_monthly / total_capacity * 100)
        st.caption(
            f"Average utilisation per rep: {util}% · "
            f"{daily_mins} min/day total · {break_mins} min break · "
            f"{work_days} working days/month · {speed} km/h avg travel speed"
        )

    # Shortfall / surplus message — based on actual routed time
    if cur_reps > 0 and actual_monthly > 0:
        time_per_cur_rep = actual_monthly / max(cur_reps, 1)
        util_cur = round(time_per_cur_rep / max(monthly_cap,1) * 100)
        if shortfall > 0:
            st.error(



                f"  {shortfall} additional rep{'s' if shortfall!=1 else ''} recommended. "
                f"With {cur_reps} reps, each would need "
                f"{time_per_cur_rep:,.0f} min/month ({util_cur}% utilisation) — over capacity."
            )
        elif shortfall < 0:
            st.success(
                f"  {abs(shortfall)} rep{'s' if abs(shortfall)!=1 else ''} to spare. "
                f"Your {cur_reps} reps handle this market at "
                f"{time_per_cur_rep:,.0f} min/month each ({util_cur}% utilisation)."
            )

    # ── Rep workload table ────────────────────────────────────────────────────
    # Get plan period from session state
    _plan_meta  = st.session_state.get("route_plan_months", {})
    _plan_pp    = _plan_meta.get("plan_period", 2)
    _plan_labels= _plan_meta.get("month_labels", ["Month 1","Month 2"])
    plan_label  = " + ".join(_plan_labels)

    st.markdown("**Rep workload breakdown:**")
    st.caption(f"Stores recommended = unique stores in the {plan_label} route plan.")

    rep_rows = {}
    for s in all_stores:
        rid = s.get("rep_id", 0)
        if not rid or rid == 0: continue
        if s.get("plan_visits", 0) == 0: continue
        if rid not in rep_rows:
            rep_rows[rid] = {
                "Rep":                 rid,
                "Stores recommended":  0,
                "Current":             0,
                "Gap (new)":           0,
                "Time needed (min)":   0,
            }
        rep_rows[rid]["Stores recommended"] += 1
        rep_rows[rid]["Time needed (min)"]  += (
            s.get("plan_visits", 0) * s.get("visit_duration_min", 25)
        )
        if s.get("covered"):
            rep_rows[rid]["Current"]   += 1
        else:
            rep_rows[rid]["Gap (new)"] += 1

    if rep_rows:
        rdf      = pd.DataFrame(list(rep_rows.values())).sort_values("Rep")
        plan_cap = monthly_cap * max(_plan_pp, 1)
        t_col    = f"Time needed — {_plan_pp}mo (min)"



        c_col    = f"Capacity — {_plan_pp}mo (min)"
        rdf[t_col]          = rdf["Time needed (min)"].round(0).astype(int)
        rdf[c_col]          = plan_cap
        rdf["Utilisation %"] = (rdf[t_col] / max(plan_cap,1) * 100).round(0).astype(int)
        rdf = rdf.drop(columns=["Time needed (min)"])

        col_order = ["Rep","Stores recommended","Current","Gap (new)", t_col, c_col, "Utilisation %"]

        total_row = {
            "Rep":                "TOTAL",
            "Stores recommended": int(rdf["Stores recommended"].sum()),
            "Current":            int(rdf["Current"].sum()),
            "Gap (new)":          int(rdf["Gap (new)"].sum()),
            t_col:                int(rdf[t_col].sum()),
            c_col:                int(rdf[c_col].sum()),
            "Utilisation %":      round(rdf[t_col].sum() / max(rdf[c_col].sum(),1) * 100),
        }

        rdf_with_total = pd.concat(
            [rdf[col_order], pd.DataFrame([total_row])[col_order]],
            ignore_index=True
        )
        st.dataframe(rdf_with_total, use_container_width=True, hide_index=True,
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
    # Show price_level and poi_count alongside rating/reviews — key scoring signals
    gcols = [c for c in ["store_name","category","score","size_tier",
                          "rating","review_count","price_level","poi_count",
                          "visits_per_month","address","city"] if c in gdf.columns]
    gdf   = gdf[gcols].sort_values("score", ascending=False).reset_index(drop=True)
    rename = {
        "store_name":"Store","category":"Category","score":"Score","size_tier":"Size",
        "rating":"Rating","review_count":"Reviews","price_level":"Price Level",
        "poi_count":"Nearby POI","visits_per_month":"Visits/Mo",
        "address":"Address","city":"City"
    }



    gdf   = gdf.rename(columns={c:rename.get(c,c) for c in gdf.columns})
    st.dataframe(gdf, use_container_width=True, height=320,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                       "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
                       "Price Level": st.column_config.NumberColumn("Price Level (%)", format="%d"),
                       "Nearby POI": st.column_config.NumberColumn("Nearby POI")})
else:
    st.info("No gap stores with score above 40.")

# ── DOWNLOADS ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">Download results</div>', unsafe_allow_html=True)

mkt_safe = market.replace(" ","_").replace("-","_")
run_date = datetime.date.today().strftime("%Y-%m-%d")

col1, col2, col3 = st.columns(3)
with col1:
    # Build clean CSV — keep only plan months, remove other month columns
    plan_months_sess = st.session_state.get("route_plan_months", {})
    _m1k = plan_months_sess.get("m1_key","")
    _m2k = plan_months_sess.get("m2_key","")
    _all_months = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
    _keep_month_cols = {f"{_m1k}_dates","m1_dates",f"{_m1k}_visits",f"{_m2k}_dates","m2_dates",f"{_m2k}_visits","plan_visits"}
    _drop_cols = [c for c in (pd.DataFrame(all_stores).columns if all_stores else [])
                  if any(c.startswith(f"{m}_") for m in _all_months)
                  and c not in _keep_month_cols]
    _clean_df = pd.DataFrame(all_stores).drop(columns=[c for c in _drop_cols if c in pd.DataFrame(all_stores).columns], errors="ignore")
    st.download_button("  Full scored universe CSV",
        _clean_df.reset_index(drop=True).to_csv(index=False),
        f"scored_universe_{mkt_safe}.csv", "text/csv")
with col2:
    st.download_button("  Gap report CSV",
        pd.DataFrame(gap_stores).reset_index(drop=True).to_csv(index=False),
        f"gap_report_{mkt_safe}.csv", "text/csv")
with col3:
    features = [
        {"type":"Feature",
         "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
         "properties":{k:s.get(k) for k in ["store_name","score","size_tier",
             "visits_per_month","rep_id","coverage_status","category"]}}
        for s in all_stores if s.get("lat") and s.get("lng")
    ]
    st.download_button("  Routes GeoJSON",
        json.dumps({"type":"FeatureCollection","features":features}, indent=2),
        f"rep_routes_{mkt_safe}.geojson", "application/json")



st.markdown("---")
st.markdown('<div class="section-title">Dashboard snapshot</div>', unsafe_allow_html=True)
st.caption("Download this file and upload it to the Dashboard page to view results anytime.")
st.download_button("  Download stores snapshot (upload to Dashboard)",
    _clean_df.reset_index(drop=True).to_csv(index=False),
    f"{mkt_safe}_{run_date}_stores.csv", "text/csv")
st.info("Upload the stores CSV to the Dashboard page. Admin manages the market library from there.")
