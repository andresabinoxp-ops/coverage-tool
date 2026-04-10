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

st.html("""
<div class="page-header">
    <h2>  Results</h2>
    <p>Scored store universe, coverage analysis and rep planning</p>
</div>
""")



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



    # Capacity definitions (consistent with pipeline):
    # eff_cap  = (daily_minutes - break) × working_days = exec+travel budget only
    # full_cap = daily_minutes × working_days = includes break time
    monthly_cap_full = daily_mins * work_days            # 480 × 22 = 10,560 min (full day)
    monthly_eff_cap  = (daily_mins - break_mins) * work_days  # 450 × 22 = 9,900 min (exec+travel)
    monthly_break    = break_mins * work_days            # 30 × 22  =   660 min

    # total_mins = exec+travel from zone_centres (no break) — this is what drives rep count
    # rep count = ceil(total_mins / monthly_eff_cap)
    zone_cs           = rep_rec.get("zone_centres", [])
    exec_travel_total = rep_rec.get("total_minutes_needed", 0) or sum(z.get("time_needed_min",0) for z in zone_cs)
    n_reps_actual     = max(rec_reps, 1)
    break_total       = n_reps_actual * monthly_break
    display_total     = exec_travel_total + break_total  # exec+travel+break

    # Correct rec_reps from numbers (guard against pipeline bugs)
    import math as _math
    correct_reps = max(1, _math.ceil(exec_travel_total / monthly_eff_cap)) if exec_travel_total > 0 else rec_reps

    m1, m2, m3, m4 = st.columns(4)
    if mode == "recommended":
        m1.metric("Recommended reps", correct_reps,
            help=f"ceil({exec_travel_total:,} min ÷ {monthly_eff_cap:,} min/rep) = {correct_reps}")
    else:
        m1.metric("Fixed reps", rec_reps)

    top_time_placeholder = m2.empty()
    top_time_placeholder.metric("Exec + Travel / month",
        f"{exec_travel_total:,.0f} min",
        help=f"Execution + inter-store travel across all {correct_reps} rep(s). Excludes break.")
    m3.metric("Capacity / rep / month",
        f"{monthly_eff_cap:,} min",
        help=f"({daily_mins} - {break_mins} break) × {work_days} days = {monthly_eff_cap:,} min exec+travel budget")
    if cur_reps > 0:
        shortfall = correct_reps - cur_reps
        m4.metric("vs Current headcount",
            f"{'+' if shortfall > 0 else ''}{shortfall} reps",
            delta_color="inverse" if shortfall > 0 else "normal")
    else:
        m4.metric("Current headcount", "Not provided")

    # Utilisation caption
    total_capacity = correct_reps * monthly_eff_cap if correct_reps > 0 else monthly_eff_cap
    if total_capacity > 0 and exec_travel_total > 0:
        util = round(exec_travel_total / total_capacity * 100)
        st.caption(
            f"Utilisation: {util}% · "



            f"{exec_travel_total:,} min needed ÷ ({correct_reps} reps × {monthly_eff_cap:,} min) · "
            f"rep count = ceil({exec_travel_total:,} ÷ {monthly_eff_cap:,}) = {correct_reps} · "
            f"{break_mins} min break/day excluded from capacity calc · {speed} km/h travel speed"
        )

    # Shortfall message
    if cur_reps > 0 and exec_travel_total > 0:
        time_per_cur_rep = exec_travel_total / max(cur_reps, 1)
        util_cur = round(time_per_cur_rep / monthly_eff_cap * 100)
        if shortfall > 0:
            st.error(
                f"  {shortfall} additional rep{'s' if shortfall!=1 else ''} recommended. "
                f"With {cur_reps} reps, each would need "
                f"{time_per_cur_rep:,.0f} min/month exec+travel ({util_cur}% of {monthly_eff_cap:,} min capacity)."
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

    # ── Sales Force Structure summary ────────────────────────────────────
    _n_sf_rules   = rep_rec.get("sf_rules_applied", 0)
    _n_ded_reps   = rep_rec.get("dedicated_reps", 0)
    _n_mix_reps   = rep_rec.get("mixed_reps", rec_reps - _n_ded_reps if _n_ded_reps else rec_reps)
    _sf_warnings  = rep_rec.get("sf_warnings", [])

    if _n_sf_rules > 0:
        st.markdown("**Sales force structure:**")
        _ded_zones = [z for z in zone_cs if z.get("dedicated")]
        _mix_zones = [z for z in zone_cs if not z.get("dedicated")]
        st.info(
            f"  **{_n_sf_rules} rule(s)** applied · "
            f"**{_n_ded_reps} dedicated** rep(s) · "
            f"**{len(_mix_zones)} mixed** rep(s)"
        )
        if _ded_zones:
            for _dz in _ded_zones:
                _util_color = "#2E7D32" if _dz.get("utilisation_pct", 0) <= 100 else "#B71C1C"
                st.markdown(
                    f'<div style="background:#F8F9FA;border:1px solid #E0E0E0;border-left:4px solid #0D47A1;'
                    f'border-radius:6px;padding:0.5rem 0.8rem;margin:0.3rem 0;font-size:0.85rem">'
                    f'Rep {_dz.get("zone","?")} — <strong>{_dz.get("rule_name","")}</strong> '
                    f'({_dz.get("rule_type","")}) · '
                    f'{_dz.get("store_count",0)} stores · '
                    f'{_dz.get("time_needed_min",0):,} min · '
                    f'<span style="color:{_util_color};font-weight:700">'
                    f'{_dz.get("utilisation_pct",0)}% utilisation</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        for _sw in _sf_warnings:
            st.warning(f"  {_sw}")

    # Build zone→rule_name map for the workload table
    _zone_rule_map = {}
    for _z in zone_cs:
        if _z.get("zone") is not None:
            _zone_rule_map[_z["zone"]] = _z.get("rule_name", "Mixed")

    rep_rows = {}
    for s in all_stores:
        rid = s.get("rep_id", 0)
        if not rid or rid == 0: continue
        if s.get("plan_visits", 0) == 0: continue
        if rid not in rep_rows:
            _rule_label = s.get("_rule_name") or _zone_rule_map.get(rid, "Mixed")
            rep_rows[rid] = {"Rep": rid, "Assignment": _rule_label,
                             "Stores": 0, "Current": 0,
                             "Gap (new)": 0, "Execution (min)": 0}
        rep_rows[rid]["Stores"]          += 1
        rep_rows[rid]["Execution (min)"] += (
            s.get("plan_visits", 0) * s.get("visit_duration_min", 25))
        if s.get("covered"): rep_rows[rid]["Current"]  += 1
        else:                rep_rows[rid]["Gap (new)"] += 1

    if rep_rows:



        rdf = pd.DataFrame(list(rep_rows.values())).sort_values("Rep")

        zc_map = {int(z.get("zone",0)): z.get("time_needed_min", 0)
                  for z in rep_rec.get("zone_centres", [])}

        cap_per_period = daily_mins * work_days * max(_plan_pp, 1)   # 10,560 × plan_period
        brk_per_period = break_mins * work_days * max(_plan_pp, 1)   # 660 × plan_period
        cap_col = f"Capacity {_plan_pp}mo (min)"

        def _exec(rid):  return rep_rows.get(int(rid), rep_rows.get(rid, {})).get("Execution (min)", 0)
        def _travel(rid):
            et = zc_map.get(int(rid), 0) * _plan_pp
            return max(0, int(et) - _exec(rid))
        def _total(rid): return _exec(rid) + _travel(rid) + brk_per_period

        rdf["Execution (min)"]    = rdf["Rep"].apply(lambda r: _exec(r)).astype(int)
        rdf["Travel (min)"]       = rdf["Rep"].apply(_travel).astype(int)
        rdf["Break (min)"]        = brk_per_period
        rdf["Total needed (min)"] = rdf["Rep"].apply(_total).astype(int)
        rdf[cap_col]              = cap_per_period
        rdf["Utilisation %"]      = (rdf["Total needed (min)"] / max(cap_per_period,1) * 100).round(0).astype(int)

        # Update top metric with actual table total (exec+travel+break)
        real_total = int(rdf["Total needed (min)"].sum())
        real_et    = int(rdf["Execution (min)"].sum()) + int(rdf["Travel (min)"].sum())
        real_brk   = int(rdf["Break (min)"].sum())
        top_time_placeholder.metric("Time needed / month (total)",
            f"{real_total:,.0f} min",
            help=f"Execution: {real_et:,} min + Break: {real_brk:,} min = {real_total:,} min total.")

        col_order = ["Rep","Assignment","Stores","Current","Gap (new)",
                     "Execution (min)","Travel (min)","Break (min)",
                     "Total needed (min)", cap_col, "Utilisation %"]
        # Only include Assignment column if rules were applied
        if _n_sf_rules == 0:
            col_order = [c for c in col_order if c != "Assignment"]

        total_row = {
            "Rep":                "TOTAL",
            "Assignment":         "",
            "Stores":             int(rdf["Stores"].sum()),
            "Current":            int(rdf["Current"].sum()),
            "Gap (new)":          int(rdf["Gap (new)"].sum()),
            "Execution (min)":    int(rdf["Execution (min)"].sum()),
            "Travel (min)":       int(rdf["Travel (min)"].sum()),
            "Break (min)":        int(rdf["Break (min)"].sum()),
            "Total needed (min)": int(rdf["Total needed (min)"].sum()),
            cap_col:              int(rdf[cap_col].sum()),
            "Utilisation %":      round(rdf["Total needed (min)"].sum() /
                                        max(rdf[cap_col].sum(), 1) * 100),
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
        "store_name":"Store","category":"Sub-channel","score":"Score","size_tier":"Size",
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
    # Always keep scoring signals in output CSV
    _always_keep = {"price_level","poi_count","rating","review_count","score",
                    "coverage_status","size_tier","visits_per_month","rep_id",
                    "assigned_day","plan_visits","lat","lng","source","covered",
                    "cluster_id","cluster_name"}

    # Reorder columns so scoring signals are grouped together
    _always_exclude = {"calls_per_month", "visit_frequency"}
    # Also always drop abstract week labels — replaced by real dates
    _always_exclude.update({c for c in (pd.DataFrame(all_stores).columns if all_stores else [])
                            if c.endswith("_weeks")})

    def _reorder_cols(df):
        # Build dynamic date/visit columns for each plan month
        _date_visit_cols = []
        for mk in ([_m1k] if _m1k else []) + ([_m2k] if _m2k else []):
            _date_visit_cols += [f"{mk}_dates", f"{mk}_visits"]
        priority = ["store_id","store_name","address","city","district","region",
                    "lat","lng","category","source","covered","coverage_status",
                    "rating","review_count","price_level","poi_count",
                    "score","size_tier","visits_per_month","visit_duration_min",
                    "annual_sales_usd","lines_per_store","cluster_id","cluster_name",
                    "rep_id","assigned_day",
                    "day_visit_order","plan_visits"] + _date_visit_cols
        ordered = [c for c in priority if c in df.columns and c not in _always_exclude]
        rest    = [c for c in df.columns if c not in ordered and c not in _always_exclude]
        return df[ordered + rest]
    _keep_month_cols = {f"{_m1k}_dates","m1_dates",f"{_m1k}_visits",f"{_m2k}_dates","m2_dates",f"{_m2k}_visits","plan_visits"}
    _drop_cols = [c for c in (pd.DataFrame(all_stores).columns if all_stores else [])
                  if any(c.startswith(f"{m}_") for m in _all_months)
                  and c not in _keep_month_cols
                  and c not in _always_keep]
    _explicit_drop = list(_always_exclude) + [c for c in _drop_cols if c in pd.DataFrame(all_stores).columns]
    _clean_df = pd.DataFrame(all_stores).drop(columns=[c for c in _explicit_drop if c in pd.DataFrame(all_stores).columns], errors="ignore")
    _clean_df = _reorder_cols(_clean_df)
    st.download_button("  Full scored universe CSV",
        _clean_df.reset_index(drop=True).to_csv(index=False),
        f"scored_universe_{mkt_safe}.csv", "text/csv")
with col2:
    _gap_df = pd.DataFrame(gap_stores).reset_index(drop=True) if gap_stores else pd.DataFrame()
    if not _gap_df.empty and "score" in _gap_df.columns:



        _score_thresh = _gap_df["score"].quantile(0.40)  # top 60% = above 40th percentile
        _gap_df["top_gap_opportunity"] = (_gap_df["score"] >= _score_thresh).map({True:"Yes", False:"No"})
    st.download_button("  Gap report CSV",
        _gap_df.reset_index(drop=True).to_csv(index=False),
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
