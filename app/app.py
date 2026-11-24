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