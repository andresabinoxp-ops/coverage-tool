import streamlit as st
import pandas as pd
import json
import os
import datetime

st.set_page_config(page_title="Dashboard - Coverage Tool", page_icon="📈", layout="wide")

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
div.stButton > button[kind="primary"] {
    background: #1565C0; border-color: #1565C0; color: white;
    border-radius: 6px; font-weight: 600;
}
div.stButton > button { border-radius: 6px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📈 Market Dashboard</h2>
    <p>Upload market snapshots and explore results — no need to re-run the pipeline</p>
</div>
""", unsafe_allow_html=True)

# ── INIT SNAPSHOT LIBRARY ─────────────────────────────────────────────────────
if "snapshot_library" not in st.session_state:
    st.session_state["snapshot_library"] = {}
# {key: {name, category, run_date, stores_df, summary_df, uploaded_at}}

# ── ADMIN UPLOAD ──────────────────────────────────────────────────────────────
is_admin = st.session_state.get("admin_authenticated", False)

if is_admin:
    st.markdown('<div class="section-title">Upload market snapshot (Admin only)</div>', unsafe_allow_html=True)
    st.caption(
        "Upload the two CSV files generated after a pipeline run. "
        "The stores file contains all scored stores. The summary file contains market-level KPIs. "
        "Both files are downloaded from the Results page."
    )

    col1, col2 = st.columns(2)
    with col1:
        stores_file = st.file_uploader(
            "Stores CSV  (*_stores.csv)",
            type=["csv"], key="upload_stores",
            help="Contains all stores with scores, size tiers, rep assignments, lat/lng etc."
        )
    with col2:
        summary_file = st.file_uploader(
            "Summary CSV  (*_summary.csv)",
            type=["csv"], key="upload_summary",
            help="Contains market-level KPIs — coverage rate, gap count, rep workload."
        )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        snap_market   = st.text_input("Market name", placeholder="e.g. Oman")
    with col_b:
        snap_category = st.text_input("Category", placeholder="e.g. Pharmacy")
    with col_c:
        snap_date     = st.date_input("Run date", value=datetime.date.today())

    if st.button("Save snapshot to library", type="primary"):
        if not stores_file:
            st.error("Stores CSV is required.")
        elif not snap_market:
            st.error("Market name is required.")
        else:
            try:
                stores_df  = pd.read_csv(stores_file)
                summary_df = pd.read_csv(summary_file) if summary_file else pd.DataFrame()
                snap_key   = f"{snap_market}_{snap_category}_{snap_date}".replace(" ","_")
                st.session_state["snapshot_library"][snap_key] = {
                    "name":        snap_market,
                    "category":    snap_category,
                    "run_date":    str(snap_date),
                    "stores_df":   stores_df,
                    "summary_df":  summary_df,
                    "uploaded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "key":         snap_key,
                }
                st.success(f"Snapshot saved: {snap_market} — {snap_category} — {snap_date}")
                st.rerun()
            except Exception as e:
                st.error(f"Error reading files: {e}")

    st.markdown("---")

# ── SNAPSHOT LIBRARY ──────────────────────────────────────────────────────────
library = st.session_state.get("snapshot_library", {})

if not library:
    st.info(
        "No market snapshots uploaded yet. "
        + ("Use the upload section above to add a market." if is_admin
           else "Ask your admin to upload market snapshots.")
    )
    st.stop()

st.markdown('<div class="section-title">Market library</div>', unsafe_allow_html=True)

# Show library cards
keys_to_delete = []
cols_per_row = 3
snap_keys = list(library.keys())

for row_start in range(0, len(snap_keys), cols_per_row):
    row_keys = snap_keys[row_start:row_start+cols_per_row]
    row_cols = st.columns(cols_per_row)
    for i, key in enumerate(row_keys):
        snap = library[key]
        stores_df = snap["stores_df"]
        n_stores  = len(stores_df)
        n_gaps    = len(stores_df[stores_df.get("coverage_status","") == "gap"]) if "coverage_status" in stores_df.columns else 0
        cov_rate  = snap["summary_df"].iloc[0].get("coverage_rate_after","—") if not snap["summary_df"].empty else "—"
        with row_cols[i]:
            st.markdown(f"""
            <div class="market-card">
                <h4>📍 {snap['name']} — {snap['category']}</h4>
                <p>Run date: {snap['run_date']} &nbsp;·&nbsp; Uploaded: {snap['uploaded_at']}</p>
                <p style="margin-top:6px">
                    <strong>{n_stores:,}</strong> stores &nbsp;·&nbsp;
                    <strong>{n_gaps:,}</strong> gaps &nbsp;·&nbsp;
                    Coverage: <strong>{cov_rate}</strong>
                </p>
            </div>""", unsafe_allow_html=True)
            if is_admin:
                if st.button(f"🗑 Delete", key=f"del_{key}"):
                    keys_to_delete.append(key)

for k in keys_to_delete:
    del st.session_state["snapshot_library"][k]
if keys_to_delete:
    st.rerun()

st.markdown("---")

# ── MARKET SELECTOR ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">View market output</div>', unsafe_allow_html=True)

snap_options = {
    f"{snap['name']} — {snap['category']} ({snap['run_date']})": key
    for key, snap in library.items()
}
selected_label = st.selectbox("Select market snapshot to view", list(snap_options.keys()))
selected_key   = snap_options[selected_label]
snap           = library[selected_key]
stores_df      = snap["stores_df"].copy()
summary_df     = snap["summary_df"].copy()

st.markdown(f"**Viewing:** {snap['name']} — {snap['category']} — Run date {snap['run_date']}")

# ── KPIs ──────────────────────────────────────────────────────────────────────
n_total   = len(stores_df)
n_covered = len(stores_df[stores_df["coverage_status"]=="covered"]) if "coverage_status" in stores_df.columns else 0
n_gaps    = len(stores_df[stores_df["coverage_status"]=="gap"])    if "coverage_status" in stores_df.columns else 0
cov_pct   = round(n_covered/max(n_total,1)*100,1)

c1,c2,c3,c4,c5 = st.columns(5)
for col, val, label in [
    (c1, f"{n_total:,}",   "Total stores"),
    (c2, f"{n_covered:,}", "Covered"),
    (c3, f"{n_gaps:,}",    "Gap stores"),
    (c4, f"{cov_pct}%",    "Coverage rate"),
    (c5, f"{len(stores_df[stores_df.get('size_tier','')=='Large']):,}" if "size_tier" in stores_df.columns else "—", "Large stores"),
]:
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{val}</div>
        <div class="kpi-label">{label}</div>
    </div>""", unsafe_allow_html=True)

# ── SIZE DISTRIBUTION ─────────────────────────────────────────────────────────
if "size_tier" in stores_df.columns:
    st.markdown('<div class="section-title">Store size distribution</div>', unsafe_allow_html=True)
    fc = st.columns(3)
    tier_colors = {"Large":"#2E7D32","Medium":"#1565C0","Small":"#F57F17"}
    for i, tier in enumerate(["Large","Medium","Small"]):
        cnt = len(stores_df[stores_df["size_tier"]==tier])
        vpm = stores_df[stores_df["size_tier"]==tier]["visits_per_month"].sum() if "visits_per_month" in stores_df.columns else 0
        col = tier_colors[tier]
        fc[i].markdown(f"""
        <div style="background:#F8F9FA;border:1px solid #E0E0E0;border-top:4px solid {col};
        border-radius:8px;padding:1rem;text-align:center">
            <div style="font-size:1.6rem;font-weight:800;color:#1A2B4A">{cnt:,}</div>
            <div style="font-size:0.78rem;color:#6B7280;font-weight:600;text-transform:uppercase">{tier}</div>
            <div style="font-size:0.75rem;color:#9E9E9E;margin-top:2px">{vpm:.0f} visits/mo</div>
        </div>""", unsafe_allow_html=True)

# ── MAP ───────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Store map</div>', unsafe_allow_html=True)

colour_by = st.selectbox("Colour by", ["Coverage status","Size tier","Rep route"], key="dash_colour")

if "lat" in stores_df.columns and "lng" in stores_df.columns:
    map_df = stores_df.dropna(subset=["lat","lng"]).copy()

    REP_COLORS = [[21,101,192],[46,125,50],[230,81,0],[136,14,79],[0,96,100],[74,20,140],[183,28,28]]
    def get_color(row):
        if colour_by == "Coverage status":
            return [46,125,50,200] if row.get("coverage_status")=="covered" else [198,40,40,220]
        elif colour_by == "Size tier":
            return {"Large":[46,125,50,220],"Medium":[21,101,192,220],"Small":[245,127,23,220]}.get(row.get("size_tier",""),[150,150,150,180])
        else:
            c = REP_COLORS[(int(row.get("rep_id",0) or 0)) % len(REP_COLORS)]
            return [c[0],c[1],c[2],200]

    map_df["color"]  = map_df.apply(get_color, axis=1)
    map_df["radius"] = map_df.get("score",50).fillna(50) * 1.5

    try:
        import pydeck as pdk
        layer = pdk.Layer("ScatterplotLayer", data=map_df,
            get_position="[lng, lat]", get_color="color", get_radius="radius",
            radius_min_pixels=4, radius_max_pixels=20, pickable=True)
        view = pdk.ViewState(latitude=map_df["lat"].mean(), longitude=map_df["lng"].mean(), zoom=11)
        tooltip = {
            "html":"<b>{store_name}</b><br/>Score: {score}<br/>Size: {size_tier}<br/>Status: {coverage_status}<br/>Rep: {rep_id}",
            "style":{"backgroundColor":"#1A2B4A","color":"white","padding":"10px","borderRadius":"8px","fontSize":"13px"}
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    except Exception:
        st.map(map_df.rename(columns={"lng":"lon"})[["lat","lon"]])

# ── STORE TABLE ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Store explorer</div>', unsafe_allow_html=True)

with st.expander("Filters", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        status_f = st.multiselect("Status", ["covered","gap"], default=["covered","gap"], key="dash_status")
    with col2:
        size_opts = stores_df["size_tier"].dropna().unique().tolist() if "size_tier" in stores_df.columns else []
        size_f    = st.multiselect("Size tier", size_opts, default=size_opts, key="dash_size")
    with col3:
        cat_opts = stores_df["category"].dropna().unique().tolist() if "category" in stores_df.columns else []
        cat_f    = st.multiselect("Category", cat_opts, default=cat_opts, key="dash_cat")

filtered = stores_df.copy()
if "coverage_status" in filtered.columns:
    filtered = filtered[filtered["coverage_status"].isin(status_f)]
if "size_tier" in filtered.columns and size_f:
    filtered = filtered[filtered["size_tier"].isin(size_f)]
if "category" in filtered.columns and cat_f:
    filtered = filtered[filtered["category"].isin(cat_f)]

show_cols = [c for c in ["store_name","category","score","size_tier","visits_per_month",
    "coverage_status","rating","review_count","rep_id","address","city","lat","lng"] if c in filtered.columns]

if not filtered.empty:
    st.caption(f"Showing {len(filtered):,} of {n_total:,} stores")
    st.dataframe(filtered[show_cols].sort_values("score",ascending=False).reset_index(drop=True),
        use_container_width=True, height=380,
        column_config={
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "rating": st.column_config.NumberColumn("Rating", format="%.1f"),
        })

# ── GAP REPORT ────────────────────────────────────────────────────────────────
if "coverage_status" in stores_df.columns:
    gaps = stores_df[stores_df["coverage_status"]=="gap"].sort_values("score",ascending=False)
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
