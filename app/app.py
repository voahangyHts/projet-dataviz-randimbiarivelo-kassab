import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Vagues de froid et réseau électrique", page_icon="⚡", layout="wide")


# ---------- Données (couche gold dans PostgreSQL) ----------
@st.cache_resource
def connexion():
    """Connexion à PostgreSQL, créée une seule fois."""
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('PG_USER', 'projet')}:{os.getenv('PG_PASSWORD', 'projet')}"
        f"@{os.getenv('PG_HOST', 'postgres')}:5432/{os.getenv('PG_DB', 'enedis')}"
    )


@st.cache_data(ttl=600)
def lire(table):
    """Lit une table gold ; le résultat est gardé en cache 10 minutes."""
    return pd.read_sql(f"SELECT * FROM {table}", connexion())


jours = lire("gold_conso_jour_region")
thermo = lire("gold_thermosensibilite_region")
heures = lire("gold_pointe_horaire")
froids = lire("gold_jours_froids")
jours["date"] = pd.to_datetime(jours["date"])
froids["date"] = pd.to_datetime(froids["date"])

# ---------- En-tête ----------
st.title("Quelles régions risquent de saturer le réseau lors des prochaines vagues de froid ?")
st.caption(
    "Tableau de bord du gestionnaire des pics de charge et de la flexibilité réseau · "
    "Consommation des clients ≤ 36 kVA (Enedis, 2022) croisée avec la température (ODRÉ) · "
    "Source : couche gold du data lake, servie par PostgreSQL."
)

with st.expander("Contrôle des données chargées"):
    st.write(pd.DataFrame({
        "table": ["gold_conso_jour_region", "gold_thermosensibilite_region", "gold_pointe_horaire", "gold_jours_froids"],
        "lignes": [len(jours), len(thermo), len(heures), len(froids)],
    }))

# ---------- Filtres (barre latérale) ----------
NOMS_FAMILLES = {"RES": "Résidentiels", "PRO": "Professionnels", "ENT": "Petites entreprises"}
MOIS_HIVER = [11, 12, 1, 2, 3]

st.sidebar.header("Filtres")
toutes_regions = sorted(thermo["nom_region"])
regions = st.sidebar.multiselect("Régions", toutes_regions, default=toutes_regions)
familles = st.sidebar.multiselect("Familles de clients (profil horaire)", list(NOMS_FAMILLES),
                                  default=list(NOMS_FAMILLES), format_func=NOMS_FAMILLES.get)
periode = st.sidebar.radio("Période", ["Hiver (novembre à mars)", "Toute l'année"])
seuil = st.sidebar.slider("Seuil « jour froid » (température moyenne, °C)", -5.0, 10.0, 5.0, 0.5)

if not regions or not familles:
    st.warning("Choisissez au moins une région et une famille de clients dans la barre latérale.")
    st.stop()

hiver_seul = periode.startswith("Hiver")
j = jours[jours["nom_region"].isin(regions)]
h = heures[heures["nom_region"].isin(regions) & heures["famille_profil"].isin(familles)]
if hiver_seul:
    j = j[j["mois"].isin(MOIS_HIVER)]
    h = h[h["mois"].isin(MOIS_HIVER)]
t = thermo[thermo["nom_region"].isin(regions)]
f = froids[froids["nom_region"].isin(regions)]

st.sidebar.caption(f"{len(regions)} région(s) · {len(j):,} jours-région affichés".replace(",", " "))

# ---------- Outils d'affichage ----------
def fr(x, decimales=0):
    """Nombre à la française : espace pour les milliers, virgule pour les décimales."""
    return f"{x:,.{decimales}f}".replace(",", " ").replace(".", ",")


# ---------- KPI ----------
# 1. Thermosensibilité
plus_reactive = t.sort_values("gradient_w_par_client", ascending=False).iloc[0]
total_mw_par_degre = t["gradient_mw_par_degre"].sum()

# 2. Pointe la plus forte de la période
pointe = j.sort_values("pointe_mw", ascending=False).iloc[0]

# 3. Écart jour froid / jour normal (charge totale des régions choisies, jour par jour)
par_jour = j.groupby("date").agg(puissance=("puissance_moy_mw", "sum"), temperature=("tmoy_c", "mean"))
jours_froids = par_jour[par_jour["temperature"] < seuil]
jours_normaux = par_jour[par_jour["temperature"] >= seuil]
if len(jours_froids) and len(jours_normaux):
    ecart = (jours_froids["puissance"].mean() / jours_normaux["puissance"].mean() - 1) * 100
    texte_ecart = f"+{fr(ecart, 1)} %"
else:
    texte_ecart = "—"

# 4. Part des particuliers entre 18 h et 20 h (toutes familles, régions et période choisies)
soir = heures[heures["nom_region"].isin(regions) & heures["heure"].isin([18, 19])]
if hiver_seul:
    soir = soir[soir["mois"].isin(MOIS_HIVER)]
part_res = soir.loc[soir["famille_profil"] == "RES", "puissance_moy_mw"].sum() / soir["puissance_moy_mw"].sum() * 100

st.subheader("Les chiffres clés")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Région la plus réactive au froid", plus_reactive["nom_region"],
          f"{fr(plus_reactive['gradient_w_par_client'], 1)} W/°C par client", delta_color="off",
          help=f"Ensemble des régions choisies : {fr(total_mw_par_degre)} MW de plus pour chaque degré perdu.")
k2.metric("Pointe la plus forte", f"{fr(pointe['pointe_mw'])} MW",
          f"{pointe['nom_region']}, le {pointe['date']:%d/%m/%Y}", delta_color="off",
          help="Plus forte puissance sur une demi-heure, sur la période choisie.")
k3.metric(f"Surconsommation les jours < {fr(seuil, 1)} °C", texte_ecart,
          f"{len(jours_froids)} jours froids sur {len(par_jour)}", delta_color="off",
          help="Puissance moyenne des jours froids comparée aux autres jours de la période.")
k4.metric("Part des particuliers à la pointe du soir", f"{fr(part_res, 1)} %",
          "créneau 18 h – 20 h", delta_color="off",
          help="Puissance des clients résidentiels ÷ puissance totale, entre 18 h et 20 h.")

with st.expander("Fiches des KPI : définition, calcul, intérêt"):
    st.markdown("""
| KPI | Définition | Calcul | Intérêt pour le persona |
|---|---|---|---|
| **Région la plus réactive au froid** (W/°C par client) | Puissance supplémentaire appelée par un client moyen pour chaque degré perdu | Pente de la régression puissance moyenne journalière ~ température moyenne, sur les jours sous 15 °C, divisée par le nombre de clients | Désigne où chaque client réagit le plus au froid : où cibler la flexibilité en priorité |
| **Pointe la plus forte** (MW) | Plus forte puissance appelée sur une demi-heure | max(énergie en Wh × 2 ÷ 10⁶) sur la période et les régions choisies | Mesure le risque de saturation du réseau |
| **Surconsommation les jours froids** (%) | Effet d'une vague de froid sur la charge | (puissance moyenne des jours sous le seuil ÷ puissance moyenne des autres jours) − 1, sur la charge totale des régions choisies | Chiffre ce que coûte un jour froid au réseau |
| **Part des particuliers à la pointe du soir** (%) | Poids des clients résidentiels entre 18 h et 20 h | puissance résidentielle ÷ puissance totale, créneau 18 h – 20 h | Dit qui cibler : effacement chez les particuliers ou chez les professionnels |
""")

import plotly.express as px

COULEURS_FAMILLES = {"Résidentiels": "#c0392b", "Professionnels": "#2c7fb8", "Petites entreprises": "#7f8c8d"}

# ---------- 1. Contexte ----------
st.header("1. Contexte : une consommation qui suit les saisons et l'heure")
c1, c2 = st.columns(2)

# a) L'année : charge totale des régions choisies, jour par jour (toute l'année, pour voir la saison)
annee = jours[jours["nom_region"].isin(regions)].groupby("date", as_index=False)["puissance_moy_mw"].sum()
fig_annee = px.line(annee, x="date", y="puissance_moy_mw",
                    title="La charge est presque deux fois plus forte en hiver qu'en été",
                    labels={"date": "", "puissance_moy_mw": "Puissance moyenne du jour (MW)"})
fig_annee.add_vrect(x0="2022-01-01", x1="2022-03-31", fillcolor="#2c7fb8", opacity=0.08, line_width=0,
                    annotation_text="hiver", annotation_position="top left")
fig_annee.add_vrect(x0="2022-11-01", x1="2022-12-31", fillcolor="#2c7fb8", opacity=0.08, line_width=0,
                    annotation_text="hiver", annotation_position="top left")
fig_annee.update_traces(line_color="#c0392b")
fig_annee.update_yaxes(rangemode="tozero")
c1.plotly_chart(fig_annee, use_container_width=True)

# b) La journée : profil horaire moyen par famille de clients (filtres familles et période)
profil = (h.groupby(["mois", "heure", "famille_profil"], as_index=False)["puissance_moy_mw"].sum()
           .groupby(["heure", "famille_profil"], as_index=False)["puissance_moy_mw"].mean())
profil["famille"] = profil["famille_profil"].map(NOMS_FAMILLES)
fig_jour = px.line(profil, x="heure", y="puissance_moy_mw", color="famille", markers=True,
                   color_discrete_map=COULEURS_FAMILLES,
                   title="La pointe tombe en début de soirée, portée par les particuliers",
                   labels={"heure": "Heure de la journée", "puissance_moy_mw": "Puissance moyenne (MW)", "famille": ""})
fig_jour.add_vline(x=19, line_dash="dot", line_color="#888888", annotation_text="19 h")
fig_jour.update_xaxes(dtick=2)
fig_jour.update_yaxes(rangemode="tozero")
c2.plotly_chart(fig_jour, use_container_width=True)

st.caption(f"Période du profil horaire : {periode.lower()} · régions et familles choisies dans la barre latérale.")

# ---------- 2. Constat ----------
st.header("2. Constat : toutes les régions consomment plus quand il fait froid, mais pas au même rythme")
c3, c4 = st.columns(2)

# a) Nuage de points : consommation par client contre température (toute l'année, régions choisies)
nuage = jours[jours["nom_region"].isin(regions)].copy()
plus_faible = t.sort_values("gradient_w_par_client").iloc[0]["nom_region"]
nuage["groupe"] = nuage["nom_region"].where(
    nuage["nom_region"].isin([plus_reactive["nom_region"], plus_faible]), "Autres régions")
fig_nuage = px.scatter(nuage, x="tmoy_c", y="kwh_par_client", color="groupe", opacity=0.6,
                       color_discrete_map={plus_reactive["nom_region"]: "#c0392b", plus_faible: "#2c7fb8",
                                           "Autres régions": "#bbbbbb"},
                       hover_data={"nom_region": True, "date": "|%d/%m/%Y", "groupe": False},
                       title="Sous 15 °C, chaque degré perdu fait monter la consommation",
                       labels={"tmoy_c": "Température moyenne du jour (°C)",
                               "kwh_par_client": "Consommation par client (kWh / jour)", "groupe": ""})
fig_nuage.add_vline(x=15, line_dash="dot", line_color="#888888", annotation_text="seuil de chauffage 15 °C")
fig_nuage.update_yaxes(rangemode="tozero")
c3.plotly_chart(fig_nuage, use_container_width=True)

# b) Classement des régions : par client ou en total
critere = c4.radio("Classer les régions par", ["Réactivité par client (W/°C)", "Charge totale ajoutée (MW/°C)"],
                   horizontal=True)
colonne = "gradient_w_par_client" if critere.startswith("Réactivité") else "gradient_mw_par_degre"
classement = t.sort_values(colonne)
fig_barres = px.bar(classement, x=colonne, y="nom_region", orientation="h", text=colonne,
                    color=colonne, color_continuous_scale="Reds",
                    hover_data={"gradient_w_par_client": True, "gradient_mw_par_degre": True, "r2": True},
                    title=("L'Ouest réagit le plus au froid, client par client" if colonne == "gradient_w_par_client"
                           else "Les grandes régions ajoutent le plus de charge à chaque degré perdu"),
                    labels={"gradient_w_par_client": "W supplémentaires par client et par °C perdu",
                            "gradient_mw_par_degre": "MW supplémentaires par °C perdu",
                            "nom_region": "", "r2": "qualité de la droite (r²)"})
fig_barres.update_coloraxes(showscale=False)
fig_barres.update_traces(texttemplate="%{text:.1f}", textposition="outside")
fig_barres.update_traces(cliponaxis=False)
fig_barres.update_xaxes(range=[0, classement[colonne].max() * 1.15])
c4.plotly_chart(fig_barres, use_container_width=True)

st.caption("Gradient = pente de la droite puissance ~ température sur les jours sous 15 °C (table gold_thermosensibilite_region). "
           "Le classement ne dépend pas de la période choisie.")