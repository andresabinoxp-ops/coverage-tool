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
st.subheader("Visit frequency distribution")
freq_counts = {}
for s in all_stores:
    f = s.get("visit_frequency", "unknown")
    freq_counts[f] = freq_counts.get(f, 0) + 1

fc = st.columns(4)
for i, (freq, desc) in enumerate([
    ("weekly",      "4 calls/month"),
    ("fortnightly", "2 calls/month"),
    ("monthly",     "1 call/month"),
    ("bi-weekly",   "0.5 calls/month"),
]):
    fc[i].metric(freq.title(), f"{freq_counts.get(freq, 0):,} stores", desc)

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
    show = [c for c in ["store_name","category","score","visit_frequency","coverage_status",
                         "rating","review_count","annual_sales_usd","lines_per_store","rep_id"] if c in df.columns]
    df_show = df[show].sort_values("score", ascending=False).reset_index(drop=True)
    df_show.columns = [c.replace("_"," ").title() for c in df_show.columns]
    st.dataframe(df_show, use_container_width=True, height=380,
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
            "Annual Sales Usd": st.column_config.NumberColumn("Sales", format="$%,.0f"),
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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recommended reps",          rec_reps)
    col2.metric("Total calls / month",       f"{total_calls:,.0f}")
    col3.metric("Rep capacity / month",      f"{cap:,}",
        help=f"{cpd} visits/day x {wd} working days")
    col4.metric("vs Current headcount",
        f"{'+' if shortfall > 0 else ''}{shortfall} reps" if cur_reps > 0 else "Not set")

    if shortfall > 0:
        st.markdown(f"""
        <div style="background:#FFF5F5;border:1px solid #FFCDD2;border-left:4px solid #C62828;
        border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0">
            <div style="font-weight:700;color:#B71C1C;margin-bottom:4px">
                ⚠️ Headcount shortfall — {shortfall} additional rep{'s' if shortfall != 1 else ''} recommended
            </div>
            <div style="font-size:0.87rem;color:#C62828;line-height:1.6">
                With {cur_reps} reps and {total_calls:,.0f} calls needed per month,
                each rep would need {total_calls/max(cur_reps,1):,.0f} calls/month
                ({total_calls/max(cur_reps,1)/wd:.1f} visits/day) — above your target of {cpd}/day.
                Adding {shortfall} rep{'s' if shortfall != 1 else ''} brings each to
                {total_calls/max(rec_reps,1):,.0f} calls/month ({total_calls/max(rec_reps,1)/wd:.1f} visits/day).
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
                {total_calls/max(cur_reps,1):,.0f} calls/month each ({total_calls/max(cur_reps,1)/wd:.1f} visits/day).
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ Exactly {rec_reps} reps needed — your current headcount is a perfect match.")

    zone_centres = rep_rec.get("zone_centres", [])
    if zone_centres:
        st.markdown("**Recommended rep base locations:**")
        zdf = pd.DataFrame(zone_centres)
        zdf.columns = ["Zone","Base Lat","Base Lng","Stores","Calls / Month"]
        st.dataframe(zdf, use_container_width=True, hide_index=True)
        st.caption("Base location is the geographic centre of each rep territory. Use this to decide where reps should be stationed.")
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

st.markdown("---")
st.subheader("Download results")
mkt_safe = market.replace(" ","_").replace("-","_")
col1, col2, col3 = st.columns(3)
with col1:
    st.download_button("Full scored universe CSV",
        pd.DataFrame(all_stores).to_csv(index=False),
        f"scored_universe_{mkt_safe}.csv", "text/csv")
with col2:
    st.download_button("Gap report CSV",
        pd.DataFrame(gap_stores).to_csv(index=False),
        f"gap_report_{mkt_safe}.csv", "text/csv")
with col3:
    features = [
        {"type":"Feature",
         "geometry":{"type":"Point","coordinates":[s.get("lng",0),s.get("lat",0)]},
         "properties":{k:s.get(k) for k in ["store_name","score","visit_frequency","rep_id","coverage_status","category"]}}
        for s in all_stores if s.get("lat") and s.get("lng")
    ]
    st.download_button("Routes GeoJSON",
        json.dumps({"type":"FeatureCollection","features":features}, indent=2),
        f"rep_routes_{mkt_safe}.geojson", "application/json")
