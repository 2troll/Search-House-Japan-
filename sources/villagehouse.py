# -*- coding: utf-8 -*-
"""
Adaptador: Village House (ビレッジハウス) — alquileres baratos para EXTRANJEROS,
con CERO entrada (sin 礼金, sin 敷金, sin comisión, sin aval). Por todo Japón.

Su web es un SPA, pero todo el catálogo viene en UNA llamada JSON:
  https://www.villagehouse.jp/api/analytics.json  -> {properties:{id:{name,pid,cid,pstl,addr,rent,...}}}
y el índice de áreas (para nombres/rutas de prefectura y ciudad):
  https://www.villagehouse.jp/api/area_en_us.json -> {regions,prefs,cities}

Marca todo como 礼金/敷金 = なし (su modelo es cero entrada) y foreigner_ok=yes.
"""

import re
import requests

import config
from sources.base import Listing, assign_area

SLUG = "villagehouse"
NAME = "🌏 Village House"
BASE = "https://www.villagehouse.jp"
ANALYTICS = BASE + "/api/analytics.json"
AREA = BASE + "/api/area_ja_jp.json"   # nombres japoneses (precisos para geocodificar) + rutas

_sess = requests.Session()
_sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
})

# código JIS de prefectura -> nombre japonés (de config.TARGET_AREAS)
_PREF_JA = {}
for a in config.TARGET_AREAS:
    if a.get("pref") and a.get("pref_code"):
        _PREF_JA.setdefault(a["pref_code"], a["pref"])


def _get_json(url):
    r = _sess.get(url, timeout=config.HTTP_TIMEOUT)
    return r.json() if r.status_code == 200 else None


def fetch(client):
    props = (_get_json(ANALYTICS) or {}).get("properties", {})
    area = _get_json(AREA) or {}
    regions = {str(r["id"]): r for r in area.get("regions", [])}
    prefs = {str(p["id"]): p for p in area.get("prefs", [])}
    cities = {str(c["id"]): c for c in area.get("cities", [])}
    if not props:
        print("  [villagehouse] sin datos de la API")
        return []

    out = []
    for pid_key, p in props.items():
        cid = str(p.get("cid") or "")
        addr = (p.get("addr") or "").strip()
        pref = prefs.get(str(p.get("pid")))
        city = cities.get(cid)
        if not addr or not pref:
            continue
        # Dirección japonesa COMPLETA (pref + ciudad + resto) -> geocodificado preciso
        pref_ja = pref.get("name", "")
        city_ja = city.get("name", "") if city else ""
        if not (pref_ja or _PREF_JA.get(cid[:2])):
            continue
        pref_ja = pref_ja or _PREF_JA.get(cid[:2], "")
        full_addr = f"{pref_ja}{city_ja}{addr}"

        # URL de la página de ciudad (real) + ancla única por edificio
        url = f"{BASE}/en/rent/?bid={pid_key}"
        if city:
            region = regions.get(str(pref.get("rid")))
            if region:
                url = f"{BASE}/en/rent/{region['path']}/{pref['path']}/{city['path']}/#vh{pid_key}"

        rent = p.get("rent")
        feats = {"交通": f"〒{p.get('pstl','')}",
                 "物件種目": "賃貸マンション (Village House)",
                 "contacto": "Village House (soporte multilingüe)",
                 "contacto_web": url}
        lst = Listing(
            source=SLUG, source_name=NAME, source_url=url,
            listing_type="rent", prop_type="apartment",
            title=f"Village House {p.get('name','')}（{addr[:14]}）",
            address_raw=full_addr,
            rent_yen=int(rent) if rent else None,
            key_money="なし", deposit="なし",     # CERO entrada (modelo de Village House)
            foreigner_ok="yes",
            parking=("yes" if p.get("pkVac") else "unknown"),
            description_raw="Village House · sin 礼金/敷金/comisión/aval · soporte multilingüe (en/pt/vi/…)",
            features=feats,
        )
        assign_area(lst)
        if lst.area_key:
            out.append(lst)
    print(f"  [villagehouse] {len(out)} propiedades (cero entrada, extranjeros)")
    return out
