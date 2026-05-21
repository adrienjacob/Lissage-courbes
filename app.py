import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.interpolate import PchipInterpolator

st.set_page_config(page_title="Lissage PCHIP", page_icon="📈", layout="centered")
st.title("Lissage de trajectoire — PCHIP")

_default = pd.DataFrame({
    "Année": [2020, 2025, 2030, 2040, 2050],
    "Valeur": [100.0, 85.0, 70.0, 40.0, 0.0],
})

if "waypoints" not in st.session_state:
    st.session_state.waypoints = _default.copy()
if "sel_pt" not in st.session_state:
    st.session_state.sel_pt = None
if "chart_ver" not in st.session_state:
    st.session_state.chart_ver = 0

st.subheader("Points de passage")
edited = st.data_editor(
    st.session_state.waypoints,
    num_rows="dynamic",
    column_config={
        "Année": st.column_config.NumberColumn(
            min_value=1900, max_value=2200, step=1, format="%d"
        ),
        "Valeur": st.column_config.NumberColumn(format="%.4f"),
    },
    use_container_width=True,
)
st.session_state.waypoints = edited

points = edited.dropna().copy()
points["Année"] = points["Année"].astype(int)
points = points.sort_values("Année").drop_duplicates("Année").reset_index(drop=True)

if len(points) < 2:
    st.warning("Entrez au moins 2 points de passage.")
    st.stop()

years_known = points["Année"].values.astype(float)
values_known = points["Valeur"].values.astype(float)
years_all = np.arange(int(years_known.min()), int(years_known.max()) + 1, dtype=float)

pchip = PchipInterpolator(years_known, values_known)
values_pchip = np.round(pchip(years_all), 4)

sel = st.session_state.sel_pt

hover_pchip = [f"{v:.4f}".replace(".", ",") for v in values_pchip]
hover_pts = [f"{v:.4f}".replace(".", ",") for v in values_known]

marker_colors = ["gold" if i == sel else "crimson" for i in range(len(years_known))]
marker_sizes = [13 if i == sel else 9 for i in range(len(years_known))]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=years_all, y=values_pchip,
    mode="lines", name="PCHIP",
    line=dict(color="#1f77b4", width=2),
    text=hover_pchip,
    hovertemplate="%{x|d} : %{text}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=years_known, y=values_known,
    mode="markers", name="Points de passage",
    marker=dict(color=marker_colors, size=marker_sizes, symbol="circle"),
    text=hover_pts,
    hovertemplate="%{x|d} : %{text}<extra></extra>",
))
fig.update_layout(
    xaxis_title="Année",
    yaxis_title="Valeur",
    hovermode="x unified",
    clickmode="event+select",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=40),
)

# st.caption("Cliquez sur un point rouge pour le modifier directement.")
event = st.plotly_chart(
    fig,
    on_select="rerun",
    selection_mode="points",
    key=f"chart_{st.session_state.chart_ver}",
    use_container_width=True,
)

# Handle chart click → select waypoint
try:
    sel_pts = event["selection"]["points"]
except (KeyError, TypeError, AttributeError):
    sel_pts = []

if sel_pts:
    curve1_pts = [pt for pt in sel_pts if pt.get("curve_number") == 1]
    new_sel = curve1_pts[0]["point_index"] if curve1_pts else None
    if new_sel != st.session_state.sel_pt:
        st.session_state.sel_pt = new_sel
        st.rerun()

# Edit panel for selected waypoint
if sel is not None and sel < len(points):
    year_val = int(points.iloc[sel]["Année"])
    valeur_val = float(points.iloc[sel]["Valeur"])
    with st.container(border=True):
        st.markdown(f"**Modifier le point {year_val}**")
        c1, c2 = st.columns(2)
        new_year = c1.number_input(
            "Année", value=year_val, step=1, min_value=1900, max_value=2200, key="edit_year"
        )
        new_val = c2.number_input(
            "Valeur", value=valeur_val, format="%.4f", key="edit_val"
        )
        b1, b2 = st.columns(2)
        if b1.button("✓ Appliquer", use_container_width=True, type="primary"):
            df = st.session_state.waypoints.copy()
            mask = df["Année"] == year_val
            if mask.any():
                df.loc[mask, "Année"] = int(new_year)
                df.loc[mask, "Valeur"] = new_val
            st.session_state.waypoints = df
            st.session_state.sel_pt = None
            st.session_state.chart_ver += 1
            st.rerun()
        if b2.button("✕ Annuler", use_container_width=True):
            st.session_state.sel_pt = None
            st.session_state.chart_ver += 1
            st.rerun()

result_df = pd.DataFrame({"Année": years_all.astype(int), "PCHIP": values_pchip})
result_display = result_df.copy()
result_display["PCHIP"] = result_display["PCHIP"].apply(lambda v: f"{v:.4f}".replace(".", ","))

st.subheader("Valeurs interpolées")
st.dataframe(result_display, use_container_width=True, hide_index=True, height=300)

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    result_df.to_excel(writer, index=False, sheet_name="PCHIP")
col1, col2 = st.columns(2)
col1.download_button(
    label="⬇ Télécharger Excel",
    data=buf.getvalue(),
    file_name="trajectoire_pchip.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
col2.download_button(
    label="⬇ Télécharger CSV",
    data=result_df.to_csv(index=False, sep=";", decimal=","),
    file_name="trajectoire_pchip.csv",
    mime="text/csv",
)

# TD : bouton copier valeurs dans presse-papier
