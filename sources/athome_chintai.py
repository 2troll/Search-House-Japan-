# -*- coding: utf-8 -*-
"""
Adaptador: at-home 賃貸 (www.athome.co.jp/chintai) — ALQUILERES.

Complementa a SUUMO con OTRO portal (más agencias) en las zonas prioritarias:
Wakayama (toda), Fukui (toda) y la isla de Awaji (洲本/南あわじ/淡路, por ciudad).

- robots.txt de www.athome.co.jp NO tiene grupo "User-agent: *"; para Googlebot
  /chintai/{pref}/list/ está permitido (solo se prohíben sub-rutas concretas).
  Aun así se raspa despacio (DELAY alto) y con páginas limitadas. Uso personal.
- Cada "edificio" (js-block) trae varias habitaciones; tomamos la MÁS BARATA como
  referencia, con su 礼金/敷金 reales (útil para el filtro de poca entrada).
- Las fotos de www.athome.co.jp sí admiten hotlink (se sirven por URL, sin bajarlas).

SLUG distinto ("athome_rent") para no tocar las casas de otras fuentes al refrescar.
"""

import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from sources.base import Listing, parse_area_m2, detect_foreigner_ok, assign_area

SLUG = "athome_rent"
NAME = "アットホーム 賃貸"
BASE = "https://www.athome.co.jp"

# (ruta de listado, prefijo de prefectura para geocodificar/clasificar)
TARGETS = [
    ("/chintai/wakayama/list/", "和歌山県"),
    ("/chintai/fukui/list/", "福井県"),
    ("/chintai/hyogo/sumoto-city/list/", "兵庫県"),
    ("/chintai/hyogo/minamiawaji-city/list/", "兵庫県"),
    ("/chintai/hyogo/awaji-city/list/", "兵庫県"),
]
MAX_PAGES = 25     # páginas por destino (30 edificios/página); los destinos pequeños paran solos
DELAY = 3.5        # pausa entre peticiones (portal grande: educado)

_sess = requests.Session()
_sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
})


def _get(url):
    for _ in range(2):
        try:
            r = _sess.get(url, timeout=config.HTTP_TIMEOUT)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            time.sleep(DELAY)
    return None


def _yen_man(text):
    """'4.8万円' -> 48000 · 'なし'/'-' -> 0 · '3,000円' -> 3000 · '' -> None."""
    if not text:
        return None
    t = text.strip()
    if "なし" in t or t in ("-", "ー", "−"):
        return 0
    m = re.search(r"([\d.]+)\s*万", t)
    if m:
        return int(round(float(m.group(1)) * 10000))
    m = re.search(r"([\d,]+)\s*円", t)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _txt(node, cls):
    el = node.find(class_=cls)
    return el.get_text(" ", strip=True) if el else ""


def _parse_block(blk, pref_prefix):
    # nombre del edificio
    h = blk.find(class_="p-property__title--building")
    name = h.get_text(" ", strip=True) if h else ""

    # dirección y acceso: los dos primeros .p-property__information-hint
    hints = [x.get_text(" ", strip=True) for x in blk.find_all(class_="p-property__information-hint")]
    address = hints[0] if hints else ""
    access = hints[1] if len(hints) > 1 else ""
    if not address:
        return None

    # tipo y antigüedad (del texto del bloque)
    btext = blk.get_text(" ", strip=True)
    if "マンション" in btext:
        prop_type = "apartment"
    elif "アパート" in btext:
        prop_type = "apartment"
    elif "一戸建" in btext or "戸建" in btext:
        prop_type = "house"
    else:
        prop_type = "apartment"
    ym = re.search(r"((?:19|20)\d{2})年(\d{1,2})月", btext)
    year_built = f"{ym.group(1)}年{ym.group(2)}月" if ym else ""

    # habitaciones: tomar la más barata
    best = None
    for room in blk.find_all(class_="js-bukken"):
        rb = room.find(class_="p-property__information-rent")
        if not rb:
            continue
        rent = _yen_man(rb.get_text(strip=True) + "万")
        if not rent:
            continue
        price_txt = _txt(room, "p-property__information-price")  # '4.8 万円 3,000円'
        mgmt_m = re.search(r"万円\s*([\d,]+)\s*円", price_txt)
        mgmt = int(mgmt_m.group(1).replace(",", "")) if mgmt_m else 0
        # 敷金 礼金 en texto crudo ('4.8万円 なし' -> 敷金, 礼金). El frontend
        # (moneyField) entiende '4.8万円' / 'なし' / 'X ヶ月', así que lo pasamos tal cual.
        km = _txt(room, "p-property__room-keymoney")
        vals = re.findall(r"[\d.]+\s*万円|[\d.]+\s*ヶ?月|[\d,]+\s*円|なし|無|不要", km)
        deposit = vals[0] if vals else ""
        key = vals[1] if len(vals) > 1 else ""
        floor = _txt(room, "p-property__floor")            # '2LDK'
        fp = _txt(room, "p-property__room-floorplan")      # '2LDK 52.20m²'
        layout = floor or (re.search(r"[1-9][SLDKR]+", fp).group(0) if re.search(r"[1-9][SLDKR]+", fp) else "")
        area = parse_area_m2(fp)
        if best is None or rent < best["rent"]:
            best = {"rent": rent, "mgmt": mgmt, "deposit": deposit, "key": key,
                    "layout": layout, "area": area, "km": km}
    if not best:
        return None

    # enlace de la ficha del edificio (id único)
    a = blk.find("a", href=re.compile(r"/chintai/\d+/"))
    if not a:
        return None
    m = re.search(r"/chintai/(\d+)/", a["href"])
    url = f"{BASE}/chintai/{m.group(1)}/" if m else urljoin(BASE, a["href"].split("?")[0])

    # foto (hotlink directo)
    photos = []
    img = blk.find("img")
    if img:
        src = img.get("data-src") or img.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("http") and "image_files" in src:
            photos.append(src.split("?")[0])

    full_addr = f"{pref_prefix}{address}"
    feats = {"交通": access, "敷金礼金": best["km"],
             "contacto": "Ver anuncio en at-home (inmobiliaria)"}
    if "駐車" in btext:
        feats["条件"] = "駐車場あり"

    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type="rent", prop_type=prop_type,
        title=f"{name}（{address}）" if name else address,
        address_raw=full_addr,
        rent_yen=best["rent"], management_fee_yen=best["mgmt"],
        key_money=best["key"], deposit=best["deposit"],
        layout=best["layout"], building_area_m2=best["area"],
        year_built=year_built,
        photos=photos,
        description_raw=f"at-home 賃貸 · {access}",
        foreigner_ok=detect_foreigner_ok(btext),
        parking=("yes" if "駐車" in btext else "unknown"),
        features=feats,
    )
    ym2 = re.search(r"(19|20)\d{2}", year_built)
    if ym2:
        from datetime import date
        lst.age_years = max(0, date.today().year - int(ym2.group()))
    assign_area(lst)
    return lst


def fetch(client):
    results, seen = [], set()
    for path, pref in TARGETS:
        for page in range(1, MAX_PAGES + 1):
            # at-home pagina por RUTA (/list/page2/), no por ?page=. La página 1 es /list/.
            url = f"{BASE}{path}" if page == 1 else f"{BASE}{path}page{page}/"
            html = _get(url)
            if not html:
                break
            soup = BeautifulSoup(html, "lxml")
            blocks = soup.find_all(class_="js-block")
            if not blocks:
                break
            added = 0
            for blk in blocks:
                try:
                    lst = _parse_block(blk, pref)
                except Exception:
                    continue
                if lst and lst.area_key and lst.source_url not in seen:
                    seen.add(lst.source_url)
                    results.append(lst)
                    added += 1
            if added == 0 and page > 1:
                break
    return results
