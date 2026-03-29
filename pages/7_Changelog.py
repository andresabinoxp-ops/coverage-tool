import streamlit as st

st.set_page_config(page_title="Changelog - Coverage Tool", page_icon="📋", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #1A2B4A !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.page-header {
    background: linear-gradient(135deg, #1A2B4A 0%, #1565C0 100%);
    padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem;
}
.page-header h2 { color: white !important; margin: 0 !important; font-size: 1.6rem !important; }
.page-header p  { color: rgba(255,255,255,0.75); margin: 0.3rem 0 0; font-size: 0.9rem; }
.version-card {
    border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 1.2rem 1.5rem; margin-bottom: 1.2rem;
}
.version-tag {
    display: inline-block; padding: 3px 12px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 700; margin-bottom: 0.6rem;
}
.tag-current  { background: #1565C0; color: white; }
.tag-stable   { background: #2E7D32; color: white; }
.tag-previous { background: #90A4AE; color: white; }
.change-item { margin: 0.3rem 0; font-size: 0.88rem; line-height: 1.6; color: #374151; }
.change-item::before { content: "→ "; color: #1565C0; font-weight: 700; }
.section-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #6B7280; margin: 0.8rem 0 0.3rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>📋 Changelog</h2>
    <p>Version history and improvements to the Coverage Tool</p>
</div>
""", unsafe_allow_html=True)

versions = [
    {
        "version": "v1.4",
        "date": "29 March 2026",
        "tag": "current",
        "summary": "Route planning, rep capacity and coverage matching overhaul",
        "sections": {
            "Route Planning": [
                "Changed from annual 12-month plan to 2-month rolling route plan — more actionable and realistic",
                "Added Occasional tier (0.5 visits/month) — stores visited once per 2-month window, default bottom 10% by score",
                "Occasional stores split evenly between Month 1 and Month 2 by geography",
                "Route start month and year now configurable in Configure page",
            ],
            "Rep Capacity & Utilisation": [
                "Break time (default 30 min) now deducted from daily capacity — 8h day = 450 min effective selling time",
                "Overflow stores from full days now redistributed to other days before being dropped — maximises rep time usage",
                "60% utilisation threshold now applied after route builder using actual plan_visits, not pre-route estimates",
                "Over-capacity check added after redistribution — lowest-score stores moved to reps with remaining room",
                "All time calculations now use plan_visits as single source of truth across Results and Routes pages",
            ],
            "Coverage Matching": [
                "Added 4-layer matching: same place_id → same coordinates → within base radius → fuzzy name + extended radius",
                "Base radius increased from 50m to 100m — catches GPS and geocoding discrepancies for same store",
                "Fuzzy name matching added for stores 100-150m apart — strips common words (supermercado, ltda) before comparing",
                "New Admin section 5 — Coverage Matching Rules with plain-language explanation and configurable settings",
            ],
            "Results Page": [
                "Removed Store Universe Explorer and confusing coverage before/after metrics",
                "New market overview: 5 KPIs — Total universe, Currently covered, Gap stores, Coverage rate, Planned visits/month",
                "Rep workload table rebuilt: Stores recommended, Current, Gap (new), Time needed 2mo, Capacity, Utilisation",
                "Removed zone territory table — rep workload table is the single source",
            ],
            "Routes Page": [
                "Month filter shows plan months only (e.g. March + April) instead of all 12 months",
                "Rep chips simplified: Plan stores and Visits/month",
                "Route status filter added: Recommended stores / Not in route / All stores",
                "Utilisation metric now always calculated from recommended stores only, using effective daily capacity × number of reps",
            ],
            "Dashboard": [
                "Auto-detects plan months from uploaded CSV — no longer assumes 12-month structure",
                "Same filters as Routes: Rep, Month, Date, Route status",
                "Route detail table updated with plan_visits column and correct month columns",
            ],
            "Data Quality": [
                "Portfolio CSV blank rows now stripped automatically on upload — fixes phantom stores from Excel empty rows",
            ],
        }
    },
    {
        "version": "v1.3",
        "date": "28 March 2026",
        "tag": "stable",
        "summary": "Scoring stability, size tiers and pipeline error handling",
        "sections": {
            "Scoring": [
                "Added _safe_num() helper — all numeric fields (rating, reviews, sales, lines) now safely converted to float",
                "Added _score_store() function with full try/except — any store that fails scoring gets 0, pipeline never stops",
                "Fixed division by zero for max_sales and max_lines when portfolio has no sales/lines data",
                "Fixed NaN/inf in scoring formula — math.isfinite() check added before rounding",
            ],
            "Size Tiers": [
                "Added Occasional tier — 4 tiers now: Large / Medium / Small / Occasional (default 20/40/30/10%)",
                "Occasional locked at 0.5 visits/month, visit duration configurable",
                "Occasional % can be set to 0 to disable — all stores fall into Small",
                "Admin percentile splits updated to 4 columns",
            ],
            "Pipeline Stability": [
                "Fixed TypeError on annual_sales_usd — string values in CSV no longer crash scoring",
                "Fixed ValueError on round(NaN) — score always returns integer 0-100",
                "Fixed sorted() error on mixed category types — all categories forced to string",
                "Portfolio blank rows dropped at load time in both Configure and Run Pipeline",
            ],
        }
    },
    {
        "version": "v1.2",
        "date": "27 March 2026",
        "tag": "previous",
        "summary": "Rep planning model and route builder",
        "sections": {
            "Rep Planning": [
                "Time-based rep recommendation replacing simple call-count model",
                "K-means geographic clustering for rep territory assignment",
                "Minimum utilisation threshold (default 60%) — under-utilised reps removed and stores redistributed",
                "Nearest-neighbour route sorting within each day cluster",
            ],
            "Configuration": [
                "Admin Settings page — scoring weights, size tiers, rep defaults, API keys",
                "Configure page — portfolio upload, market setup, visit benchmarks, rep mode selection",
                "Fixed and Recommended rep modes",
                "Break time and travel speed configurable",
            ],
            "Results & Routes": [
                "Results page with KPIs, size distribution, rep planning panel and downloads",
                "Routes page with map, rep colour legend, day filter and route detail table",
                "GeoJSON download for external mapping tools",
                "Dashboard snapshot upload and market library",
            ],
        }
    },
    {
        "version": "v1.0 — v1.1",
        "date": "26 March 2026",
        "tag": "previous",
        "summary": "Initial build — scraping, scoring and gap analysis",
        "sections": {
            "Core Pipeline": [
                "Google Places scraping for store universe by city and category",
                "6-signal scoring model: rating, reviews, affluence, POI density, sales, lines carried",
                "Coverage matching — portfolio stores vs scraped universe",
                "Gap identification with score ranking",
                "Phone and opening hours enrichment via Google Place Details API",
                "POI enrichment — counts nearby points of interest as footfall proxy",
            ],
            "App Structure": [
                "6-page Streamlit app: Home, Admin Settings, Configure, Run Pipeline, Results, Routes, Dashboard",
                "Navy blue theme (#1A2B4A) with gradient page headers",
                "Session state management across pages",
                "Streamlit Cloud deployment via GitHub",
            ],
        }
    },
]

tag_labels = {"current": "Current", "stable": "Stable", "previous": "Previous"}
tag_classes = {"current": "tag-current", "stable": "tag-stable", "previous": "tag-previous"}

for v in versions:
    border = "#1565C0" if v["tag"] == "current" else ("#2E7D32" if v["tag"] == "stable" else "#E2E8F0")
    st.markdown(f"""
    <div class="version-card" style="border-color:{border}">
        <span class="version-tag {tag_classes[v['tag']]}">{tag_labels[v['tag']]}</span>
        <span style="font-size:1.1rem;font-weight:800;color:#1A2B4A;margin-left:10px">{v['version']}</span>
        <span style="font-size:0.82rem;color:#6B7280;margin-left:10px">{v['date']}</span>
        <div style="font-size:0.9rem;color:#374151;margin:0.4rem 0 0.8rem;font-style:italic">{v['summary']}</div>
    </div>
    """, unsafe_allow_html=True)

    for section, items in v["sections"].items():
        st.markdown(f'<div class="section-label">{section}</div>', unsafe_allow_html=True)
        for item in items:
            st.markdown(f'<div class="change-item">{item}</div>', unsafe_allow_html=True)
    st.markdown("")

st.markdown("---")
st.caption("Coverage Tool · Built for FMCG field sales planning · Powered by Google Places API + Streamlit")
