#!/bin/bash
# athome_japan.sh — añade el akiya bank de at-home (casas vacías baratas en VENTA)
# de las 47 prefecturas, exporta los shards y publica. KEEP_MISSING=1 para no
# jubilar el resto de fuentes. Un solo commit al final (no compite con otros).
cd "$(dirname "$0")"
echo "=== ATHOME AKIYA (47 prefecturas) $(date +%H:%M) ==="
KEEP_MISSING=1 python3 refresh.py athome 2>&1 | tail -6
echo "=== export shards $(date +%H:%M) ==="
python3 -c "import db; print('total casas:', db.export_shards())"
mkdir -p docs/data && cp web/data/*.geojson web/data/index.json docs/data/
git add web/data docs/data
git commit -q -m "Densidad: akiya bank de at-home en las 47 prefecturas (casas vacías baratas en venta)" || { echo "sin cambios"; exit 0; }
for i in 1 2 3 4; do
  git push origin HEAD:claude/akiya-house-finder-map-jSrtq >/dev/null 2>&1 && \
  git push origin HEAD:main >/dev/null 2>&1 && { echo "PUBLICADO ✓"; break; }
  sleep $((i*4))
done
git branch -f claude/akiya-house-finder-map-jSrtq HEAD >/dev/null 2>&1
echo "=== ATHOME AKIYA COMPLETO $(date +%H:%M) ==="
