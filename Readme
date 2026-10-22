# Consommation électrique et vagues de froid — du data lake au tableau de bord

**Binôme :** Voahangy RANDIMBIARIVELO · Elyes KASSAB
**Cours :** Visualisation de données — Mastère Big Data & IA (M1), Sup de Vinci — M. L. NDAO
**Session :** 2026-2027

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