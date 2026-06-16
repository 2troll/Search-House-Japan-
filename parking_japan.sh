#!/bin/bash
# parking_japan.sh — raspa SUUMO con el filtro nj_109 (ガレージ付き・駐車場あり) en las
# 47 prefecturas y ETIQUETA esas casas como parking="yes" (SUUMO_PARKING=1).
# Así el filtro "Solo con parking" deja de dar 2-3 resultados.
# KEEP_MISSING=1 => NO jubila las casas que no salen en el filtro (se actualizan
# por source_url las que sí, el resto se queda intacto). Reanudable, publica por pref.
cd "$(dirname "$0")"
ALL=(osaka tokyo kanagawa saitama chiba aichi fukuoka hyogo kyoto hokkaido \
     nara shiga miyagi hiroshima shizuoka ibaraki gifu gumma tochigi okayama \
     kumamoto kagoshima nagasaki mie nagano niigata fukushima yamaguchi \
     ehime kagawa oita miyazaki ishikawa toyama yamagata aomori iwate akita \
     wakayama fukui yamanashi tokushima saga kochi tottori shimane okinawa)
PREFS=("${@:-${ALL[@]}}")
for p in "${PREFS[@]}"; do
  echo "===== PARKING: $p  $(date +%H:%M) ====="
  SUUMO_PREFS="$p" SUUMO_FILTER=nj_109 SUUMO_PARKING=1 SUUMO_MAX_PAGES=4 KEEP_MISSING=1 \
    python3 refresh.py suumo 2>&1 | tail -3
  python3 -c "import db; db.export_shards()" >/dev/null
  mkdir -p docs/data && cp web/data/*.geojson web/data/index.json docs/data/
  git add web/data docs/data
  git commit -q -m "Parking: +$p (駐車場あり SUUMO, etiquetado parking=yes)" || { echo "  (sin nuevas en $p)"; continue; }
  for i in 1 2 3 4; do
    git push origin HEAD:claude/akiya-house-finder-map-jSrtq >/dev/null 2>&1 && \
    git push origin HEAD:main >/dev/null 2>&1 && { echo "  ✓ $p publicado"; break; }
    sleep $((i*4))
  done
  git branch -f claude/akiya-house-finder-map-jSrtq HEAD >/dev/null 2>&1
done
echo "PARKING COMPLETO $(date +%H:%M)"
