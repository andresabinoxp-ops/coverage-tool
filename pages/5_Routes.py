import streamlit as st
import pandas as pd

st.set_page_config(page_title="Routes — Coverage Tool", page_icon="🗺️", layout="wide")
st.title("Rep Routes Map")

if not st.session_state.get("run_results"):
    st.warning("No results yet. Run the pipeline first.")
    st.stop()

res        = st.session_state["run_results"]
all_stores = res["all_stores"]
market     = st.session_state.get("last_market", "Market")

st.subheader(f"Market: {market}")

col1, col2, col3 = st.columns(3)
with col1:
    colour_by = st.selectbox("Colour markers by", ["Rep route", "Visit frequency", "Coverage status", "Score"])
with col2:
    show_gaps    = st.checkbox("Show gap stores",     value=True)
    show_covered = st.checkbox("Show covered stores", value=True)
with col3:
    min_score = st.slider("Min score to show", 0, 100, 0)

map_stores = [
    s for s in all_stores
    if s.get("lat") and s.get("lng")
    and s.get("score", 0) >= min_score
    and ((show_gaps    and s.get("coverage_status") == "gap") or
         (show_covered and s.get("covered")))
]
st.caption(f"Showing {len(map_stores):,} stores on map")

REP_COLORS = [
    [0,229,160],[108,143,255],[255,184,48],[255,107,53],
    [200,100,200],[100,200,255],[255,150,150],[150,255,150],
    [200,200,100],[100,150,200],
]
FREQ_COLORS = {
    "weekly":      [0,229,160,220],
    "fortnightly": [108,143,255,220],
    "monthly":     [255,184,48,220],
    "bi-weekly":   [255,107,53,200],
}
STATUS_COLORS = {
    "covered": [0,200,130,200],
    "gap":     [255,80,80,220],
}

def get_color(s):
    if colour_by == "Rep route":
        c = REP_COLORS[(s.get("rep_id",0) or 0) % len(REP_COLORS)]
        return [c[0],c[1],c[2],200]
    elif colour_by == "Visit frequency":
        return FREQ_COLORS.get(s.get("visit_frequency",""), [150,150,150,180])
    elif colour_by == "Coverage status":
        return STATUS_COLORS.get(s.get("coverage_status","covered"), [150,150,150,180])
    else:
        sc = s.get("score",0)
        if sc >= 80: return [0,220,120,220]
        if sc >= 60: return [100,150,255,220]
        if sc >= 40: return [255,190,50,220]
        return [255,100,60,200]

map_data = [{
    "lat":s["lat"],"lng":s["lng"],
    "name":s.get("store_name",""),
    "score":s.get("score",0),
    "freq":s.get("visit_frequency",""),
    "status":s.get("coverage_status",""),
    "rep":s.get("rep_id",0),
    "category":s.get("category",""),
    "color":get_color(s),
    "radius":max(30,s.get("score",0)*1.5),
} for s in map_stores]

try:
    import pydeck as pdk
    df_map = pd.DataFrame(map_data)
    if not df_map.empty:
        layer = pdk.Layer("ScatterplotLayer", data=df_map,
            get_position="[lng, lat]", get_color="color", get_radius="radius",
            radius_min_pixels=4, radius_max_pixels=20, pickable=True)
        view = pdk.ViewState(latitude=df_map["lat"].mean(), longitude=df_map["lng"].mean(), zoom=11, pitch=0)
        tooltip = {"html":"<b>{name}</b><br/>Score: <b>{score}</b><br/>Frequency: {freq}<br/>Status: {status}<br/>Rep: {rep}",
                   "style":{"backgroundColor":"#1a1a2e","color":"white","padding":"8px","borderRadius":"6px"}}
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    else:
        st.info("No stores with valid coordinates to display.")
except ImportError:
    if map_data:
        df_map = pd.DataFrame(map_data)
        st.map(df_map.rename(columns={"lng":"lon"})[["lat","lon"]])
    else:
        st.info("No stores to display.")

st.markdown("---")
st.subheader("Store list by rep")
all_reps = sorted(set(s.get("rep_id",0) for s in all_stores if s.get("rep_id")))
if all_reps:
    sel = st.selectbox("Select rep", ["All reps"] + [f"Rep {r}" for r in all_reps])
    if sel != "All reps":
        rep_num    = int(sel.split(" ")[1])
        rep_stores = [s for s in all_stores if s.get("rep_id") == rep_num]
        if rep_stores:
            rdf  = pd.DataFrame(rep_stores)
            show = [c for c in ["store_name","category","score","visit_frequency","calls_per_month","coverage_status"] if c in rdf.columns]
            rdf  = rdf[show].sort_values("score", ascending=False)
            rdf.columns = [c.replace("_"," ").title() for c in rdf.columns]
            st.dataframe(rdf, use_container_width=True, hide_index=True)
