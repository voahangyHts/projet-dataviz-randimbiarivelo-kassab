#!/usr/bin/env bash
# Télécharge les données du projet dans data/raw :
#   - Enedis : consommation 1/2 h, maille régionale, 2022 (4 CSV, ≈ 1,7 Go)
#   - ODRÉ   : température quotidienne départementale (CSV, ≈ 10 Mo)
#   - contours des régions (GeoJSON, pour la carte du tableau de bord)
# Le référentiel départements -> régions est versionné dans ref/ (petit fichier statique).
#
# Usage : bash scripts/telecharger_donnees.sh
# Relançable : les fichiers déjà présents ne sont pas retéléchargés.
# Sources : https://www.data.gouv.fr/datasets/677e6c9229987842305739fa  (Enedis)
#           https://www.data.gouv.fr/datasets/5eb236728ad018f2f0fe1b9e  (ODRÉ)
set -euo pipefail

cd "$(dirname "$0")/.."
DG="https://www.data.gouv.fr/api/1/datasets/r"
mkdir -p data/raw/enedis data/raw/meteo data/raw/geo

telecharger() {   # $1 = url, $2 = fichier de destination
  if [ -s "$2" ]; then echo "  déjà présent : $2"; return; fi
  curl -fL --retry 3 -o "$2.part" "$1"
  mv "$2.part" "$2"
}

echo "→ Enedis : consommation électrique 1/2 h par région (2022) — 4 fichiers"
i=1
for id in 4f572a06-761d-4053-8cc4-e925861213eb \
          ce9f5441-fb91-4524-80c1-a0792efd15b2 \
          19f8070c-3539-4585-84e9-9dec78a0f30f \
          0468dbc1-3d32-4f74-89e9-92135c0213df; do
  telecharger "${DG}/${id}" "data/raw/enedis/conso_region_2022_part${i}.csv"
  i=$((i+1))
done

echo "→ ODRÉ : température quotidienne départementale"
telecharger "${DG}/dd0df06a-85f2-4621-8b8b-5a3fe195bcd7" "data/raw/meteo/temperature_departementale.csv"

echo "→ Contours des régions (facultatif : la carte du tableau de bord)"
telecharger "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions-version-simplifiee.geojson" \
  "data/raw/geo/regions.geojson" || echo "  ⚠ contours indisponibles : la carte sera désactivée, le reste fonctionne."

echo
echo "Terminé :"
ls -lh data/raw/enedis data/raw/meteo data/raw/geo
