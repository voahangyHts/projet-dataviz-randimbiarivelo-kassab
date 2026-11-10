# Consommation électrique et vagues de froid — du data lake au tableau de bord

- **Binôme :** Voahangy RANDIMBIARIVELO · Elyes KASSAB
- **Cours :** Visualisation de données — Mastère Big Data & IA (M1), Sup de Vinci — M. L. NDAO
- **Session :** 2026-2027

## 1. Les jeux de données

Pour répondre à la problématique du persona, notre projet s'appuie sur le **croisement de deux
sources de données ouvertes**, téléchargeables par script.

### 1.1 Jeu de données principal : la consommation électrique

| | |
|---|---|
| **Source** | Open Data Enedis — *Agrégats segmentés de consommation électrique au pas 1/2 h des points de soutirage ≤ 36 kVA, maille régionale (2022)* |
| **Lien** | https://www.data.gouv.fr/datasets/677e6c9229987842305739fa |
| **Description** | Historique des consommations électriques agrégées à la **maille régionale**, par profil de client (particuliers, professionnels) et par puissance souscrite. |
| **Dimension temporelle** | Horodatage **demi-horaire** (une valeur toutes les 30 minutes) sur l'année 2022. |
| **Dimension géographique** | Les **régions** de France métropolitaine. |
| **Volume** | 4 fichiers CSV d'environ 425 Mo (≈ 1,7 Go) : le jeu **dépasse les 2 millions de lignes** attendues. |
| **Licence** | Licence Ouverte / Open Licence 2.0 |

### 1.2 Jeu de données d'enrichissement : la météo

| | |
|---|---|
| **Source** | Open Data Réseaux Énergies (ODRÉ) — *Température quotidienne départementale (depuis janvier 2018)* |
| **Lien** | https://www.data.gouv.fr/datasets/5eb236728ad018f2f0fe1b9e |
| **Description** | Historique des températures **minimales, maximales et moyennes** quotidiennes, par département de France métropolitaine. |
| **Mise en correspondance** | Les températures départementales sont **moyennées par région**, et la consommation demi-horaire est **agrégée par jour**, pour obtenir la même maille géographique (région) et temporelle (jour) que les données Enedis. |
| **Objectif** | Croiser la température avec la consommation lors de la phase de préparation (**Silver / Gold**) pour modéliser la **thermosensibilité** de chaque région. |
| **Licence** | Licence Ouverte / Open Licence 2.0 |

### 1.3 Critère d'exclusion

Le jeu de données **NYC Taxi** utilisé dans le cours n'est **pas** utilisé dans ce projet.

> Les données ne sont pas versionnées dans ce dépôt : elles sont téléchargées par un script.

---

## 2. Le persona

| | |
|---|---|
| **Qui ?** | Le **Gestionnaire des Pics de Charge et de la Flexibilité Réseau** chez Enedis. |
| **Que décide-t-il ?** | Le déclenchement d'actions de **flexibilité locale** (effacements, signaux tarifaires) ou la priorisation des **renforcements physiques du réseau** (transformateurs), pour éviter les coupures. |
| **À quelle fréquence ?** | Chaque **semaine**, voire chaque **jour**, pendant la période hivernale (novembre à mars). |

### Sa question principale

> **Quelles régions présentent la plus forte réactivité au froid (thermosensibilité) et risquent
> de saturer la capacité du réseau lors des prochaines vagues de froid ?**


## 3. Architecture

mermaid
flowchart LR
    A[Enedis CSV<br/>consommation 1/2 h] --> B[(Bronze<br/>Delta / RustFS)]
    M[ODRÉ CSV<br/>température quotidienne] --> B
    R[Référentiel<br/>départements → régions] --> B
    B --> S[(Silver<br/>nettoyé et typé)]
    S --> G[(Gold<br/>agrégats par région)]
    G --> P[(PostgreSQL)]
    P --> D[Tableau de bord<br/>Streamlit]
    O[Ontologie .ttl<br/>+ requêtes SPARQL] -.-> G


Architecture en médaillon : *bronze* (données brutes, sans transformation), *silver* (nettoyage et typage,
chaque règle est comptée), *gold* (agrégats construits pour répondre à la question du persona).

## 4. Structure du dépôt


.
├── compose.yaml                  # RustFS, PostgreSQL, Jupyter/Spark, Adminer, Fuseki, Streamlit
├── .env.example                  # variables d'environnement (valeurs par défaut)
├── scripts/
│   └── telecharger_donnees.sh    # télécharge les données dans data/raw (non versionnées)
├── ref/
│   └── departements_regions.csv  # référentiel des 96 départements métropolitains et de leur région
├── commun/                       # utilitaires partagés par les notebooks (Spark, S3, PostgreSQL)
├── notebooks/                    # à exécuter dans l'ordre
├── ontologie/                    # ontologie .ttl et requêtes SPARQL
├── app/                          # application Streamlit (Dockerfile, app.py)
└── docs/                         # captures et documentation


## 5. Lancer le projet

*Prérequis :* Git, Docker Desktop (8 Go de mémoire alloués), environ 10 Go d'espace disque libre.
Sous Windows, exécuter les commandes bash depuis *Git Bash*.

bash
# 1. Cloner le dépôt
git clone https://github.com/voahangyHts/projet-dataviz-randimbiarivelo-kassab.git
cd projet-dataviz-randimbiarivelo-kassab

# 2. Télécharger les données (≈ 1,7 Go, relançable sans risque)
bash scripts/telecharger_donnees.sh

# 3. Démarrer la stack (Jupyter + Spark, RustFS, PostgreSQL)
docker compose up -d
docker compose ps        # jupyter, rustfs, postgres, adminer : « running »


*4. Exécuter les notebooks dans l'ordre* depuis JupyterLab : http://localhost:8888/lab?token=projet

| Ordre | Notebook | Rôle | État |
|---|---|---|---|
| 1 | notebooks/01_bronze.ipynb | Ingestion des données brutes en Delta (couche bronze) | fait |
| 2 | notebooks/02_silver.ipynb | Nettoyage et typage, règles chiffrées | à venir |
| 3 | notebooks/03_gold.ipynb | Agrégats, thermosensibilité, export PostgreSQL | à venir |
| 4 | notebooks/04_ontologie_sparql.ipynb | Ontologie et requêtes SPARQL | à venir |
| 5 | notebooks/05_exploration.ipynb | Exploration et avant/après des graphiques | à venir |

*5. Lancer le tableau de bord*

bash
docker compose --profile app up -d --build


Puis ouvrir http://localhost:8501.

### Services et accès

| Service | Adresse | Identifiants |
|---|---|---|
| JupyterLab | http://localhost:8888/lab?token=projet | jeton projet |
| Console RustFS (data lake) | http://localhost:9001 | rustfsadmin / rustfsadmin |
| Adminer (PostgreSQL) | http://localhost:8080 | système PostgreSQL, serveur postgres, projet / projet, base enedis |
| Streamlit | http://localhost:8501 | — |
| Fuseki (SPARQL, profil semantique) | http://localhost:3030 | admin / admin |

### Arrêter

bash
docker compose --profile "*" down


## 6. Avancement

- [x] Jeux de données et persona validés
- [x] Script de téléchargement, compose.yaml
- [x] Couche bronze (Delta dans RustFS)
- [ ] Couche silver (règles de nettoyage chiffrées)
- [ ] Couche gold et export PostgreSQL
- [ ] Ontologie .ttl et requêtes SPARQL
- [ ] Notebook d'exploration et avant/après
- [ ] Tableau de bord Streamlit (KPI, récit, filtres)