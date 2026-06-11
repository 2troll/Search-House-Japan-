#!/bin/bash
# zero_japan.sh — raspa SOLO casas 敷金・礼金ゼロ (zero-zero) de SUUMO en las 47
# prefecturas (こだわり nj_114). KEEP_MISSING=1 para no jubilar el resto.
# Publica por prefectura (reanudable). Más páginas (las filtradas son pocas/ciudad).
cd "$(dirname "$0")"
ALL=(osaka tokyo kanagawa saitama chiba aichi fukuoka hyogo kyoto hokkaido \
     nara shiga miyagi hiroshima shizuoka ibaraki gifu gumma tochigi okayama \
     kumamoto kagoshima nagasaki mie nagano niigata gunma fukushima yamaguchi \
     ehime kagawa oita miyazaki ishikawa toyama yamagata aomori iwate akita \
     wakayama fukui yamanashi tokushima saga kochi tottori shimane okinawa)
PREFS=("${@:-${ALL[@]}}")
for p in "${PREFS[@]}"; do
  echo "===== ZERO-ZERO: $p  $(date +%H:%M) ====="
  SUUMO_PREFS="$p" SUUMO_FILTER=nj_114 SUUMO_MAX_PAGES=5 KEEP_MISSING=1 \
    python3 refresh.py suumo 2>&1 | tail -3
  python3 -c "import db; db.export_shards()" >/dev/null
  mkdir -p docs/data && cp web/data/*.geojson web/data/index.json docs/data/
  git add web/data docs/data
  git commit -q -m "Zero-zero: +$p (敷金・礼金なし SUUMO)" || { echo "  (sin nuevas en $p)"; continue; }
  for i in 1 2 3 4; do
    git push origin HEAD:claude/akiya-house-finder-map-jSrtq >/dev/null 2>&1 && \
    git push origin HEAD:main >/dev/null 2>&1 && { echo "  ✓ $p publicado"; break; }
    sleep $((i*4))
  done
  git branch -f claude/akiya-house-finder-map-jSrtq HEAD >/dev/null 2>&1
done
echo "ZERO-ZERO COMPLETO $(date +%H:%M)"
