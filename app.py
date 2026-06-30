import base64
import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.interpolate import PchipInterpolator

st.set_page_config(page_title="Lissage PCHIP", page_icon="📈", layout="centered")
st.title("Lissage de trajectoire PCHIP")

def points_from_url():
    """Décode les points de passage depuis l'URL (param ?p=annee,valeur;...)."""
    raw = st.query_params.get("p")
    if not raw:
        return None
    annees, valeurs = [], []
    for pair in raw.split(";"):
        if "," not in pair:
            continue
        a, v = pair.split(",", 1)
        try:
            annee, valeur = int(a), float(v)
        except ValueError:
            continue
        annees.append(annee)
        valeurs.append(valeur)
    if not annees:
        return None
    return pd.DataFrame({"Année": annees, "Valeur": valeurs})


def decode_state():
    """Décode les points de passage et la note depuis l'URL (params ?d= et ?n=)."""
    token = st.query_params.get("d")
    if token:
        try:
            annees, valeurs = [], []
            for pair in token.split("_"):
                a, v = pair.split("~")
                annees.append(int(a))
                valeurs.append(float(v))
            df = pd.DataFrame({"Année": annees, "Valeur": valeurs})
            note = ""
            raw_n = st.query_params.get("n")
            if raw_n:
                pad = "=" * (-len(raw_n) % 4)
                note = base64.urlsafe_b64decode(raw_n + pad).decode("utf-8")
            return (df if not df.empty else None), note
        except Exception:
            pass
    # Rétrocompatibilité : ancien lien ?p=annee,valeur;...
    return points_from_url(), ""


def encode_state(annees, valeurs, texte):
    """Encode points + note pour un lien permanent compact.

    Points : `annee~valeur_annee~valeur` (caractères jamais percent-encodés).
    Note   : base64url, courte même avec accents/espaces. Renvoie (points, note).
    """
    pts = "_".join(f"{int(a)}~{v:g}" for a, v in zip(annees, valeurs))
    note = (
        base64.urlsafe_b64encode(texte.encode("utf-8")).decode("ascii").rstrip("=")
        if texte
        else ""
    )
    return pts, note


default_points, default_note = decode_state()
if default_points is None:
    default_points = pd.DataFrame({
        "Année": [2020, 2025, 2030, 2040, 2050],
        "Valeur": [100.0, 85.0, 70.0, 40.0, 0.0],
    })

st.subheader("Points de passage")

# L'éditeur est amorcé une seule fois depuis l'URL puis devient la seule source
# de vérité. Lui repasser des données dérivées de l'URL à chaque rerun ferait
# perdre des éditions en cours pendant que le lien permanent se met à jour.
if "points_seed" not in st.session_state:
    seed = default_points.copy()
    seed["Valeur"] = seed["Valeur"].apply(lambda v: f"{v:.4f}".replace(".", ","))
    st.session_state["points_seed"] = seed
    st.session_state.setdefault("note_input", default_note)

edited = st.data_editor(
    st.session_state["points_seed"],
    key="points_editor",
    num_rows="dynamic",
    column_config={
        "Année": st.column_config.NumberColumn(
            min_value=1900, max_value=2200, step=1, format="%d"
        ),
        "Valeur": st.column_config.TextColumn(),
    },
    use_container_width=True,
)

note = st.text_area(
    "Note",
    key="note_input",
    help="Texte libre, inclus dans le lien permanent.",
)

points = edited.dropna().copy()
points["Valeur"] = points["Valeur"].astype(str).str.replace(",", ".", regex=False).str.strip()
points = points[points["Valeur"].str.match(r"^-?\d*\.?\d+$")]
points["Valeur"] = points["Valeur"].astype(float)
points["Année"] = points["Année"].astype(int)
points = points.sort_values("Année").drop_duplicates("Année").reset_index(drop=True)

if len(points) < 2:
    st.warning("Entrez au moins 2 points de passage.")
    st.stop()

# Met l'URL a jour : elle devient le lien permanent (points + note)
pts_enc, note_enc = encode_state(points["Année"].values, points["Valeur"].values, note)
if st.query_params.get("d") != pts_enc:
    st.query_params["d"] = pts_enc
if note_enc:
    if st.query_params.get("n") != note_enc:
        st.query_params["n"] = note_enc
elif "n" in st.query_params:
    del st.query_params["n"]
if "p" in st.query_params:
    del st.query_params["p"]

st.components.v1.html(
    """<style>
    *{margin:0;padding:0;box-sizing:border-box}
    html,body{background:transparent}
    button{
        width:100%;height:38px;cursor:pointer;
        display:inline-flex;align-items:center;justify-content:center;
        font-size:1rem;font-weight:400;line-height:1.6;
        font-family:"Source Sans Pro",sans-serif;
        border-radius:0.5rem;border:1px solid rgba(49,51,63,0.2);
        background:white;color:rgb(49,51,63);transition:border-color .15s;
    }
    button:hover{border-color:currentColor}
    button:active{opacity:.8}
    </style>
    <script>
    window.addEventListener('load',function(){
        try{
            var cs=window.parent.getComputedStyle(window.parent.document.documentElement);
            var bg=cs.getPropertyValue('--background-color').trim();
            var fg=cs.getPropertyValue('--text-color').trim();
            var btn=document.getElementById('lk');
            if(bg){document.body.style.background=bg;btn.style.background=bg;}
            if(fg){
                btn.style.color=fg;
                btn.style.borderColor=fg.replace('rgb(','rgba(').replace(')',',.2)');
            }
        }catch(e){}
    });
    function copyLink(){
        var b=document.getElementById('lk');
        navigator.clipboard.writeText(window.parent.location.href)
            .then(function(){
                b.textContent='✓ Lien copie !';
                setTimeout(function(){b.textContent='\U0001f517 Copier le lien permanent';},2000);
            });
    }
    </script>
    <button id="lk" onclick="copyLink()">\U0001f517 Copier le lien permanent</button>""",
    height=42,
)

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
csv_text = result_df.to_csv(index=False, sep=";", decimal=",")
# Tabulations + virgule decimale pour coller directement dans Excel francais
tsv_text = "\t".join(f"{v:.4f}".replace(".", ",") for v in result_df["PCHIP"])

col1, col2, col3 = st.columns(3)
col1.download_button(
    label="⬇ Telecharger Excel",
    data=buf.getvalue(),
    file_name="trajectoire_pchip.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
col2.download_button(
    label="⬇ Telecharger CSV",
    data=csv_text,
    file_name="trajectoire_pchip.csv",
    mime="text/csv",
)
with col3:
    st.components.v1.html(
        f"""<style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        html,body{{background:transparent}}
        button{{
            width:100%;height:38px;cursor:pointer;
            display:inline-flex;align-items:center;justify-content:center;
            font-size:1rem;font-weight:400;line-height:1.6;
            font-family:"Source Sans Pro",sans-serif;
            border-radius:0.5rem;border:1px solid rgba(49,51,63,0.2);
            background:white;color:rgb(49,51,63);transition:border-color .15s;
        }}
        button:hover{{border-color:currentColor}}
        button:active{{opacity:.8}}
        </style>
        <script>
        window.addEventListener('load',function(){{
            try{{
                var cs=window.parent.getComputedStyle(window.parent.document.documentElement);
                var bg=cs.getPropertyValue('--background-color').trim();
                var fg=cs.getPropertyValue('--text-color').trim();
                var btn=document.getElementById('cb');
                if(bg){{document.body.style.background=bg;btn.style.background=bg;}}
                if(fg){{
                    btn.style.color=fg;
                    btn.style.borderColor=fg.replace('rgb(','rgba(').replace(')',',.2)');
                }}
            }}catch(e){{}}
        }});
        function doCopy(){{
            var b=document.getElementById('cb');
            navigator.clipboard.writeText({json.dumps(tsv_text)})
                .then(function(){{
                    b.textContent='✓ Copie !';
                    setTimeout(function(){{b.textContent='\U0001f4cb Copier les valeurs';}},2000);
                }});
        }}
        </script>
        <button id="cb" onclick="doCopy()">\U0001f4cb Copier les valeurs</button>""",
        height=42,
    )
