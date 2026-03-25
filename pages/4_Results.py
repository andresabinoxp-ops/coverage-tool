import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Results — Coverage Tool", page_icon="📊", layout="wide")
st.title("Results Dashboard")

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
col1.metric("Total stores",              f"{total:,}")
col2.metric("Currently covered",         f"{covered_n:,}")
col3.metric("Coverage rate before",      f"{res['coverage_rate_before']}%")
col4.metric("Coverage rate after",       f"{res['coverage_rate_after']}%")
col5.metric("High priority gaps",        f"{gap_high:,}")

st.markdown("---")
st.subheader("Visit frequency distribution")
freq_counts = {}
for s in all_stores:
    f = s.get("visit_frequency", "unknown")
    freq_counts[f] = freq_counts.get(f, 0) + 1

fc = st.columns(4)
for i, freq in enumerate(["weekly", "fortnightly", "monthly", "bi-weekly"]):
    fc[i].metric(freq.title(), f"{freq_counts.get(freq, 0):,} stores")

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
    show = [c for c in ["store_name","category","score","visit_frequency","coverage_status","rating","review_count","annual_sales_usd","lines_per_store","rep_id"] if c in df.columns]
    df_show = df[show].sort_values("score", ascending=False).reset_index(drop=True)
    df_show.columns = [c.replace("_"," ").title() for c in df_show.columns]
    st.dataframe(df_show, use_container_width=True, height=380,
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f"),
            "Annual Sales Usd": st.column_config.NumberColumn("Sales", format="$%,.0f"),
        })

st.markdown("---")
st.subheader("Top gap opportunities")
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
st.subheader("Rep workload summary")
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
mkt_safe = market.replace(" ","_")
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
