import streamlit as st

st.set_page_config(
    page_title="Coverage Tool",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Professional CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Main header bar */
[data-testid="stHeader"] {
    background-color: #1B4F9B;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #1B4F9B;
}
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] a:hover {
    background-color: #2563C0 !important;
    border-radius: 6px;
}

/* Page title style */
.page-header {
    background: linear-gradient(135deg, #1B4F9B 0%, #2563C0 100%);
    padding: 32px 40px;
    border-radius: 12px;
    margin-bottom: 32px;
    color: white;
}
.page-header h1 {
    color: white !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    margin: 0 0 6px 0 !important;
}
.page-header p {
    color: rgba(255,255,255,0.85) !important;
    font-size: 1rem !important;
    margin: 0 !important;
}

/* Step cards */
.step-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #1B4F9B;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.step-card h4 {
    color: #1B4F9B;
    font-size: 0.95rem;
    font-weight: 700;
    margin: 0 0 6px 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.step-card p {
    color: #4A5568;
    font-size: 0.9rem;
    margin: 0;
    line-height: 1.5;
}

/* Nav buttons */
div.stButton > button {
    width: 100%;
    min-height: 80px;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    border: 2px solid #E2E8F0;
    background: #FFFFFF;
    color: #1A1A2E;
    cursor: pointer;
    transition: all 0.2s;
    white-space: pre-line;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
div.stButton > button:hover {
    border-color: #1B4F9B;
    background: #EBF2FF;
    color: #1B4F9B;
    box-shadow: 0 4px 12px rgba(27,79,155,0.15);
}

/* Status badges */
.badge-success {
    background: #F0FFF4;
    border: 1px solid #9AE6B4;
    color: #276749;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-warning {
    background: #FFFBEB;
    border: 1px solid #F6E05E;
    color: #744210;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
}

/* Divider */
hr {
    border: none;
    border-top: 1px solid #E2E8F0;
    margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key in ["run_results", "last_market", "market_config"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>Coverage Tool</h1>
    <p>FMCG Store Coverage Playbook Agent — Geocoding · Scraping · Scoring · Gap Analysis · Route Allocation</p>
</div>
""", unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown("### Navigate to")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("🔐\nAdmin Settings\nAPI keys & config", key="nav_admin"):
        st.switch_page("pages/1_Admin_Settings.py")
with col2:
    if st.button("⚙️\nConfigure\nMarket & weights", key="nav_configure"):
        st.switch_page("pages/2_Configure.py")
with col3:
    if st.button("📤\nRun Pipeline\nUpload & execute", key="nav_pipeline"):
        st.switch_page("pages/3_Run_Pipeline.py")
with col4:
    if st.button("📊\nResults\nScores & gaps", key="nav_results"):
        st.switch_page("pages/4_Results.py")
with col5:
    if st.button("🗺️\nRoutes\nRep route map", key="nav_routes"):
        st.switch_page("pages/5_Routes.py")

st.markdown("---")

# ── How to use ────────────────────────────────────────────────────────────────
st.markdown("### How to use")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
<div class="step-card">
    <h4>Step 1 — First time only</h4>
    <p>Open <strong>Admin Settings</strong> from the sidebar. Add your Google Maps API key in Streamlit Secrets or paste it directly in the admin panel.</p>
</div>
""", unsafe_allow_html=True)
with c2:
    st.markdown("""
<div class="step-card">
    <h4>Step 2 — Each market</h4>
    <p>Open <strong>Configure</strong>. Upload your portfolio CSV. Search for your country, add regions and cities. Set scoring weights and save.</p>
</div>
""", unsafe_allow_html=True)
with c3:
    st.markdown("""
<div class="step-card">
    <h4>Step 3 — Run and explore</h4>
    <p>Open <strong>Run Pipeline</strong>. Click Run Agent. Then explore scored stores in <strong>Results</strong> and rep routes in <strong>Routes</strong>.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Status ────────────────────────────────────────────────────────────────────
st.markdown("### Current status")
col_a, col_b = st.columns(2)

with col_a:
    if st.session_state.get("market_config"):
        mkt = st.session_state["market_config"].get("market_name", "Unknown")
        st.success(f"✅ Market configured: **{mkt}**")
    else:
        st.warning("⚠️ No market configured yet — open Configure in the sidebar")

with col_b:
    if st.session_state.get("run_results"):
        mkt = st.session_state.get("last_market", "")
        n   = len(st.session_state["run_results"].get("all_stores", []))
        st.success(f"✅ Results ready: **{mkt}** — {n:,} stores scored")
    else:
        st.warning("⚠️ No pipeline results yet — open Run Pipeline in the sidebar")

st.markdown("---")
st.caption("Coverage Tool — FMCG Store Coverage Playbook Agent")
