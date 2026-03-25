import streamlit as st

st.set_page_config(
    page_title="Coverage Tool",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "run_results" not in st.session_state:
    st.session_state.run_results = None
if "last_market" not in st.session_state:
    st.session_state.last_market = None
if "market_config" not in st.session_state:
    st.session_state.market_config = None

st.markdown("""
<style>
div.stButton > button {
    width: 100%;
    height: 100px;
    font-size: 15px;
    font-weight: 600;
    border-radius: 10px;
    border: 2px solid rgba(255,255,255,0.15);
    background: rgba(255,255,255,0.05);
    color: inherit;
    cursor: pointer;
    transition: all 0.2s;
    white-space: pre-line;
}
div.stButton > button:hover {
    border-color: #00e5a0;
    background: rgba(0,229,160,0.1);
    color: #00e5a0;
}
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Coverage Tool")
st.subheader("FMCG Store Coverage Playbook Agent")
st.markdown("""
An end-to-end agent that geocodes your stores, scrapes the full universe via Google Places,
scores every outlet, identifies gaps, assigns visit frequencies and allocates rep routes.
""")
st.markdown("---")
st.markdown("### 👇 Click a page to get started")

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
st.markdown("### How to use")

c1, c2, c3 = st.columns(3)
with c1:
    st.info("**Step 1 — First time only**\n\nAdmin Settings → add your Google Maps API key into Streamlit Secrets.")
with c2:
    st.info("**Step 2 — Each market**\n\nConfigure → set bounding box, weights, thresholds → Save.")
with c3:
    st.info("**Step 3 — Run & explore**\n\nRun Pipeline → upload CSV → Run Agent → view Results and Routes.")

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    if st.session_state.get("market_config"):
        mkt = st.session_state["market_config"].get("market_name", "Unknown")
        st.success(f"✅ Market configured: **{mkt}**")
    else:
        st.warning("⚠️ No market configured yet — go to Configure")

with col_b:
    if st.session_state.get("run_results"):
        mkt = st.session_state.get("last_market", "")
        n = len(st.session_state["run_results"].get("all_stores", []))
        st.success(f"✅ Results ready: **{mkt}** — {n:,} stores scored")
    else:
        st.warning("⚠️ No results yet — go to Run Pipeline")

st.caption("💡 You can also navigate using the sidebar on the left at any time.")
