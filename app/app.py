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