import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Results - Coverage Tool", page_icon="📊", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1B4F9B; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.page-header { background: linear-gradient(135deg, #1B4F9B 0%, #2563C0 100%); padding: 28px 36px; border-radius: 12px; margin-bottom: 28px; }
.page-header h1 { color: white !important; font-size: 1.8rem !important; font-weight: 700 !important; margin: 0 0 4px 0 !important; }
.page-header p  { color: rgba(255,255,255,0.85) !important; font-size: 0.95rem !important; margin: 0 !important; }
hr { border: none; border-top: 1px solid #E2E8F0; margin: 20px 0; }
div.stButton > button { border-radius: 6px; font-weight: 600; border: 2px solid #1B4F9B; background: #1B4F9B; color: white; padding: 8px 24px; }
div.stButton > button:hover { background: #2563C0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>Results Dashboard</h1>
    <p>Scored store universe, gap analysis and downloads</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.get("run_results"):
    st.warning("No results yet. Run the pipeline first.")
    st.stop()

res        = st.session_state["run_results"]
all_stores = res["all_stores"]
gap_stores = res["gap_stores"]
market     = st.session_state.get("last_market", "Market")

st.subheader(f"Market: {market}")

total     = len(all_stores)
covered_n = sum(1 for s in all_stores if s.get("covered"))
gap_high  = sum(1 for s in gap_stores if s.get("score", 0) >= 60)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total stores in universe", f"{total:,}")
col2.metric("Currently covered",        f"{covered_n:,}")
col3.metric("Coverage rate before",     f"{res['coverage_rate_before']}%")
col4.metric("Coverage rate after",      f"{res['coverage_rate_after']}%")
col5.metric("High priority gaps",       f"{gap_high:,}")

st.markdown("---")
st.subheader("Store size distribution")
size_counts  = {}
visit_totals = {}
for s in all_stores:
    tier = s.get("size_tier","") or s.get("visit_frequency","")
    size_counts[tier]  = size_counts.get(tier,0) + 1
    visit_totals[tier] = visit_totals.get(tier,0) + s.get("visits_per_month", s.get("calls_per_month",0))

fc = st.columns(3)
tier_colors = {"Large":"#2E7D32","Medium":"#1565C0","Small":"#F57F17"}
for i, tier in enumerate(["Large","Medium","Small"]):
    cnt = size_counts.get(tier,0)
    vpm = visit_totals.get(tier,0)
    col = tier_colors[tier]
    fc[i].markdown(f"""
    <div style="background:#F8F9FA;border:1px solid #E0E0E0;border-top:4px solid {col};
    border-radius:8px;padding:1rem;text-align:center">
        <div style="font-size:1.6rem;font-weight:800;color:#1A2B4A">{cnt:,}</div>
        <div style="font-size:0.78rem;color:#6B7280;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">{tier} stores</div>
        <div style="font-size:0.75rem;color:#9E9E9E;margin-top:2px">{vpm:.0f} total visits/mo</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")
st.subheader("Store universe explorer")

with st.expander("Filters", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_filter = st.multiselect("Status", ["covered","gap"], default=["covered","gap"])
    with col2:
        freq_filter = st.multiselect("Frequency", ["weekly","fortnightly","monthly","bi-weekly"], default=["weekly","fortnightly","monthly","bi-weekly"])
    with col3:
        cats = sorted(set(s.get("category","") for s in all_stores if s.get("category")))
        cat_filter = st.multiselect("Category", cats, default=cats)
    with col4:
        score_min, score_max = st.slider("Score range", 0, 100, (0, 100))

filtered = [
    s for s in all_stores
    if s.get("coverage_status","covered") in status_filter
    and s.get("visit_frequency","") in freq_filter
    and s.get("category","") in cat_filter
    and score_min <= s.get("score", 0) <= score_max
]
st.caption(f"Showing {len(filtered):,} of {total:,} stores")

if filtered:
    df = pd.DataFrame(filtered)
    show = [c for c in ["store_name","category","score","size_tier","visits_per_month",
                         "visit_duration_min","assigned_day","coverage_status",
                         "rating","review_count","price_level","poi_count",
                         "annual_sales_usd","lines_per_store","rep_id"] if c in df.columns]
    df_show = df[show].sort_values("score", ascending=False).reset_index(drop=True)
    df_show.columns = [c.replace("_"," ").title() for c in df_show.columns]
    st.dataframe(df_show, use_container_width=True, height=380,
        column_config={
            "Score":          st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating":         st.column_config.NumberColumn("Rating",  format="%.1f"),
            "Annual Sales Usd": st.column_config.NumberColumn("Sales", format="$%,.0f"),
            "Price Level":    st.column_config.NumberColumn("Price Level ★", format="%d / 4",
                help="Google price level: 1=budget, 2=moderate, 3=premium, 4=luxury"),
        })

st.markdown("---")
st.subheader("Top gap opportunities — uncovered stores score >= 40")
high_gaps = [s for s in gap_stores if s.get("score",0) >= 40]
if high_gaps:
    gdf = pd.DataFrame(high_gaps[:50])
    gcols = [c for c in ["store_name","category","score","visit_frequency","rating","review_count","address","city"] if c in gdf.columns]
    gdf = gdf[gcols].sort_values("score", ascending=False).reset_index(drop=True)
    gdf.columns = [c.replace("_"," ").title() for c in gdf.columns]
    st.dataframe(gdf, use_container_width=True, height=320,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})
else:
    st.info("No gap stores with score above 40.")

st.markdown("---")

# ── REP RECOMMENDATION PANEL ─────────────────────────────────────────────────
rep_rec = res.get("rep_recommendation")
if rep_rec and rep_rec.get("mode") == "recommended":
    st.markdown('<div class="section-title">Rep planning recommendation</div>', unsafe_allow_html=True)

    rec_reps    = rep_rec.get("recommended_reps", 0)
    cur_reps    = rep_rec.get("current_reps", 0)
    shortfall   = rep_rec.get("shortfall", 0)
    total_calls = rep_rec.get("total_calls_needed", 0)
    cap         = rep_rec.get("cap_per_rep", 220)
    cpd         = rep_rec.get("calls_per_day", 10)
    wd          = rep_rec.get("working_days", 22)

    total_mins  = rep_rec.get("total_minutes_needed", rep_rec.get("total_calls_needed",0))
    monthly_cap = rep_rec.get("monthly_cap_per_rep",  rep_rec.get("cap_per_rep",480*22))
    daily_mins  = rep_rec.get("daily_minutes", 480)
    speed       = rep_rec.get("avg_speed_kmh", 30)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recommended reps",          rec_reps)
    col2.metric("Total time needed / month", f"{total_mins:,.0f} min",
        help="Sum of visit time + estimated travel time for all priority stores")
    col3.metric("Rep capacity / month",      f"{monthly_cap:,} min",
        help=f"{daily_mins} min/day × {wd} working days")
    if cur_reps > 0:
        col4.metric("vs Current headcount",
            f"{'+' if shortfall > 0 else ''}{shortfall} reps",
            delta_color="inverse" if shortfall > 0 else "normal")
    else:
        col4.metric("Current headcount", "Not provided",
            help="Enter your current rep count in Configure to see the comparison.")

    # Utilisation info
    if monthly_cap > 0 and total_mins > 0:
        util = round(total_mins / (rec_reps * monthly_cap) * 100)
        st.caption(
            f"Each rep uses ~{util}% of their monthly capacity "
            f"({daily_mins} min/day · {wd} working days · {speed} km/h avg travel speed)"
        )

    if cur_reps == 0:
        st.info(
            f"The agent recommends **{rec_reps} reps** for this market "
            f"based on {total_mins:,.0f} total minutes needed per month "
            f"at {monthly_cap:,} min/rep/month. "
            "Go back to Configure and enter your current headcount to see the shortfall or surplus."
        )

    if shortfall > 0:
        st.markdown(f"""
        <div style="background:#FFF5F5;border:1px solid #FFCDD2;border-left:4px solid #C62828;
        border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0">
            <div style="font-weight:700;color:#B71C1C;margin-bottom:4px">
                ⚠️ Headcount shortfall — {shortfall} additional rep{'s' if shortfall != 1 else ''} recommended
            </div>
            <div style="font-size:0.87rem;color:#C62828;line-height:1.6">
                With {cur_reps} reps and {total_calls:,.0f} calls needed per month,
                each rep would need {total_mins/max(cur_reps,1):,.0f} min/month
                ({total_mins/max(cur_reps,1)/wd/daily_mins*100:.0f}% utilisation) — above the {monthly_cap:,} min/month capacity.
                Adding {shortfall} rep{'s' if shortfall != 1 else ''} brings each to
                {total_mins/max(rec_reps,1):,.0f} min/month ({total_mins/max(rec_reps,1)/wd/daily_mins*100:.0f}% utilisation).
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif shortfall < 0:
        st.markdown(f"""
        <div style="background:#E8F5E9;border:1px solid #A5D6A7;border-left:4px solid #2E7D32;
        border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0">
            <div style="font-weight:700;color:#1B5E20;margin-bottom:4px">
                ✅ Headcount sufficient — {abs(shortfall)} rep{'s' if abs(shortfall) != 1 else ''} to spare
            </div>
            <div style="font-size:0.87rem;color:#2E7D32;line-height:1.6">
                Your {cur_reps} reps can handle this market comfortably at
                {total_mins/max(cur_reps,1):,.0f} min/month each ({total_mins/max(cur_reps,1)/monthly_cap*100:.0f}% utilisation).
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Exactly {rec_reps} reps needed — your current headcount is a perfect match.")

    zone_centres = rep_rec.get("zone_centres", [])
    if zone_centres:
        st.markdown("**Rep zone summary — base locations and workload:**")
        zdf = pd.DataFrame(zone_centres)
        # rename columns depending on what fields are present
        col_map = {
            "zone":"Zone","centre_lat":"Base Lat","centre_lng":"Base Lng",
            "store_count":"Stores","visits_per_month":"Visits/Month",
            "time_needed_min":"Time Needed (min)","capacity_min":"Capacity (min)",
            "utilisation_pct":"Utilisation %","calls_per_month":"Visits/Month",
        }
        zdf = zdf.rename(columns={k:v for k,v in col_map.items() if k in zdf.columns})
        st.dataframe(zdf, use_container_width=True, hide_index=True,
            column_config={
                "Utilisation %": st.column_config.ProgressColumn("Utilisation %", min_value=0, max_value=100),
            })
        st.caption("Base location = geographic centre of each rep territory. Utilisation = time needed vs available capacity.")
else:
    st.markdown('<div class="section-title">Rep workload summary</div>', unsafe_allow_html=True)

rep_data = {}
for s in all_stores:
    rid = s.get("rep_id", 0)
    if rid == 0: continue
    if rid not in rep_data:
        rep_data[rid] = {"Rep ID": rid, "Stores": 0, "Calls per Month": 0.0}
    rep_data[rid]["Stores"]          += 1
    rep_data[rid]["Calls per Month"] += s.get("calls_per_month", 0)
if rep_data:
    rdf = pd.DataFrame(list(rep_data.values())).sort_values("Rep ID")
    rdf["Calls per Month"] = rdf["Calls per Month"].round(1)
    st.dataframe(rdf, use_container_width=True, hide_index=True)

import datetime
st.markdown("---")
st.subheader("Download results")
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
         "properties":{k:s.get(k) for k in ["store_name","score","size_tier","visits_per_month","rep_id","coverage_status","category"]}}
        for s in all_stores if s.get("lat") and s.get("lng")
    ]
    st.download_button("🗺 Routes GeoJSON",
        json.dumps({"type":"FeatureCollection","features":features}, indent=2),
        f"rep_routes_{mkt_safe}.geojson", "application/json")

st.markdown("---")
st.markdown('<div class="section-title">Dashboard snapshot files</div>', unsafe_allow_html=True)
st.caption("Download these two files and upload them to the Dashboard page to view results anytime without re-running the pipeline.")

summary_data = {
    "market_name":           [market],
    "run_date":              [run_date],
    "total_stores":          [len(all_stores)],
    "covered_stores":        [sum(1 for s in all_stores if s.get("covered"))],
    "gap_stores":            [len(gap_stores)],
    "coverage_rate_before":  [res.get("coverage_rate_before","")],
    "coverage_rate_after":   [res.get("coverage_rate_after","")],
    "large_stores":          [sum(1 for s in all_stores if s.get("size_tier")=="Large")],
    "medium_stores":         [sum(1 for s in all_stores if s.get("size_tier")=="Medium")],
    "small_stores":          [sum(1 for s in all_stores if s.get("size_tier")=="Small")],
    "total_visits_per_month":[sum(s.get("visits_per_month",0) for s in all_stores)],
}
summary_df = pd.DataFrame(summary_data)

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.download_button(
        "⬇️ Stores snapshot  (upload to Dashboard)",
        pd.DataFrame(all_stores).to_csv(index=False),
        f"{mkt_safe}_{run_date}_stores.csv", "text/csv")
with col_s2:
    st.download_button(
        "⬇️ Summary snapshot  (upload to Dashboard)",
        summary_df.to_csv(index=False),
        f"{mkt_safe}_{run_date}_summary.csv", "text/csv")
st.info("Upload both files to the Dashboard page. Admin can manage the market library from there.")
