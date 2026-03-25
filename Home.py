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

st.title("Coverage Tool")
st.subheader("FMCG Store Coverage Playbook Agent")

st.markdown("""
An end-to-end agent that:
- Geocodes your current store portfolio
- Scrapes the full store universe from Google Places matching your portfolio categories
- Scores every store using ratings, footfall, category fit, sales and lines per store
- Identifies gaps — stores you are not covering but should be
- Assigns visit frequency — weekly, fortnightly, monthly or bi-weekly
- Allocates rep routes by geography and workload
""")

st.markdown("---")
st.info("Use the sidebar on the left to navigate between pages.")
st.markdown("---")

st.markdown("### How to use")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("**Step 1 - First time only**\n\nOpen Admin Settings from the sidebar. Set your Google Maps API key in Streamlit Secrets.")
with c2:
    st.info("**Step 2 - Each market**\n\nOpen Configure. Select country, region and city. Upload your portfolio CSV. The scraping categories are set automatically.")
with c3:
    st.info("**Step 3 - Run and explore**\n\nOpen Run Pipeline. Click Run Agent. Then view Results and Routes.")

st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    if st.session_state.get("market_config"):
        mkt = st.session_state["market_config"].get("market_name", "Unknown")
        st.success(f"Market configured: {mkt}")
    else:
        st.warning("No market configured yet - open Configure in the sidebar")

with col_b:
    if st.session_state.get("run_results"):
        mkt = st.session_state.get("last_market", "")
        n = len(st.session_state["run_results"].get("all_stores", []))
        st.success(f"Results ready: {mkt} - {n} stores scored")
    else:
        st.warning("No results yet - open Run Pipeline in the sidebar")
