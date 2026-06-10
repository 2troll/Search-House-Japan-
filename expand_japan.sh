#!/bin/bash
# expand_japan.sh — expansión a TODO Japón, prefectura a prefectura (ciclos).
#
# Por cada prefectura: raspa SUUMO (KEEP_MISSING=1 para no jubilar el resto),
# geocodifica, exporta los SHARDS y hace commit+push. Si el proceso se corta,
# todo lo completado ya está publicado; relanzar retoma donde iba (las URLs ya
# vistas solo se actualizan, y el geocode usa caché).
#
# Uso:  bash expand_japan.sh            # todas las pendientes, oeste/sur primero
#       bash expand_japan.sh tokyo aichi  # solo esas

cd "$(dirname "$0")"
set -u

# Oeste/sur primero (interés del usuario), luego este/norte.
ALL_PREFS=(yamaguchi kochi fukuoka saga nagasaki kumamoto oita miyazaki kagoshima okinawa \
           aichi shizuoka gifu nagano yamanashi ishikawa toyama niigata \
           kanagawa tokyo chiba saitama ibaraki tochigi gunma \
           fukushima yamagata miyagi akita iwate aomori hokkaido)
PREFS=("${@:-${ALL_PREFS[@]}}")

for p in "${PREFS[@]}"; do
  echo ""
  echo "===================== PREFECTURA: $p  $(date +%H:%M) ====================="
  SUUMO_PREFS="$p" KEEP_MISSING=1 python3 refresh.py suumo 2>&1 | tail -4

  # Exportar shards y publicar SOLO los archivos de datos (commit pequeño)
  python3 -c "import db; print('shards:', db.export_shards())"
  mkdir -p docs/data && cp web/data/*.geojson web/data/index.json docs/data/
  git add web/data docs/data
  git commit -q -m "Expansión Japón: +$p (SUUMO)" || { echo "  (sin cambios en $p)"; continue; }
  for i in 1 2 3; do
    git push origin HEAD:claude/akiya-house-finder-map-jSrtq >/dev/null 2>&1 && \
    git push origin HEAD:main >/dev/null 2>&1 && break
    sleep $((i*4))
  done
  git branch -f claude/akiya-house-finder-map-jSrtq HEAD >/dev/null 2>&1
  echo "  ✓ $p publicado"
done
echo ""
echo "EXPANSIÓN COMPLETA $(date +%H:%M)"
