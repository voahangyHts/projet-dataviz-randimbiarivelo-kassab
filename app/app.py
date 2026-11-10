"""Tableau de bord — Consommation électrique et vagues de froid.

Lancement :  docker compose --profile app up -d --build   ->  http://localhost:8501
Squelette : à compléter avec les KPI, le récit (contexte, constat, recommandation) et les filtres.
"""
import os

import pandas as pd
import sqlalchemy
import streamlit as st

st.set_page_config(page_title="Vagues de froid — réseau Enedis", layout="wide")

PG = (f"postgresql+psycopg2://{os.getenv('PG_USER', 'projet')}:{os.getenv('PG_PASSWORD', 'projet')}"
      f"@{os.getenv('PG_HOST', 'postgres')}:5432/{os.getenv('PG_DB', 'enedis')}")


@st.cache_data(ttl=600)
def lire(table):
    return pd.read_sql(f"SELECT * FROM {table}", sqlalchemy.create_engine(PG))


st.title("Quelles régions risquent de saturer le réseau lors des prochaines vagues de froid ?")
try:
    thermo = lire("gold_thermosensibilite")
    st.dataframe(thermo)
except Exception as e:  # tables gold pas encore créées
    st.info(f"Les tables gold ne sont pas encore disponibles ({type(e).__name__}). "
            "Exécutez les notebooks dans l'ordre.")
