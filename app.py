import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.interpolate import PchipInterpolator

st.set_page_config(page_title="Lissage PCHIP", page_icon="📈", layout="centered")
st.title("Lissage de trajectoire — PCHIP")

default_points = pd.DataFrame({
    "Année": [2020, 2025, 2030, 2040, 2050],
    "Valeur": [100.0, 85.0, 70.0, 40.0, 0.0],
})

st.subheader("Points de passage")
edited = st.data_editor(
    default_points,
    num_rows="dynamic",
    column_config={
        "Année": st.column_config.NumberColumn(
            min_value=1900, max_value=2200, step=1, format="%d"
        ),
        "Valeur": st.column_config.NumberColumn(format="%.4f"),
    },
    use_container_width=True,
)

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

hover_pchip = [f"{v:.4f}".replace(".", ",") for v in values_pchip]
hover_pts = [f"{v:.4f}".replace(".", ",") for v in values_known]

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
    marker=dict(color="crimson", size=9, symbol="circle"),
    text=hover_pts,
    hovertemplate="%{x|d} : %{text}<extra></extra>",
))
fig.update_layout(
    xaxis_title="Année",
    yaxis_title="Valeur",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=40),
)
st.plotly_chart(fig, use_container_width=True)

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
