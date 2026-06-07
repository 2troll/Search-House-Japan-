# -*- coding: utf-8 -*-
"""
Adaptador: at-home 空き家バンク (アットホーム空き家バンク).
Sitio: https://www.akiya-athome.jp/

Es un AGREGADOR nacional de los bancos de casas vacías municipales (~900
ayuntamientos). Cubre con una sola estructura todas las prefecturas que nos
interesan: Nara, Kyoto, Osaka, Hyogo, Wakayama, Fukui...

Estrategia:
  - Por cada PREFECTURA (código JIS en TARGET_AREAS["pref_code"]) recorre las
    páginas de venta (/buy/{pref}/) y alquiler (/rent/{pref}/).
  - Cada "card" trae ya casi todo: precio, 間取り, m², 築年月, dirección completa
    y una foto. No hace falta abrir la ficha (rápido y educado).
  - Solo conserva las casas cuya dirección caiga en una zona de TARGET_AREAS
    (config.match_area) y que sean 戸建て (descarta マンション/土地).

No hay robots.txt que lo prohíba; aun así se respeta el rate limit y el
User-Agent del HttpClient. Uso personal, sin redistribución.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import (
    Listing, parse_price_yen, parse_area_m2, detect_foreigner_ok, assign_area,
)
import config

SLUG = "athome"
NAME = "アットホーム空き家バンク"
BASE = "https://www.akiya-athome.jp"

_LAYOUT_RE = re.compile(r"[1-9０-９]+\s*[SLDKR]+")


def _field(text, label, nxt):
    """Extrae el valor entre `label` y el siguiente marcador `nxt` en el texto de la card."""
    m = re.search(re.escape(label) + r"\s*(.+?)\s*(?:" + nxt + r")", text)
    return m.group(1).strip() if m else ""


def _parse_card(node, listing_type):
    a = node.find("a", href=re.compile("bukken/detail"))
    if not a:
        return None
    url = a["href"]
    text = node.get_text(" ", strip=True)

    # precio
    pm = re.search(r"価格\s*([\d,\.]+)\s*万円", text) or re.search(r"賃料\s*([\d,\.]+)\s*万円", text)
    rent_m = re.search(r"賃料\s*([\d,\.]+)\s*(?:万)?円", text)
    price_yen = None
    if pm:
        price_yen = int(round(float(pm.group(1).replace(",", "")) * 10000))
    elif rent_m:
        price_yen = parse_price_yen(rent_m.group(0))

    # tipo de inmueble: casa, apartamento o terreno (descartamos solo terreno)
    kind = _field(text, "物件種目", "築年月|所在地|交通|間取|$")
    if "土地" in kind:
        return None
    if "マンション" in kind or "アパート" in kind:
        prop_type = "apartment"
    else:
        prop_type = "house"

    layout = ""
    lm = re.search(r"間取\s*([1-9０-９]+\s*[SLDKR]+(?:以上)?)", text)
    if lm:
        layout = lm.group(1).replace(" ", "")
    building = parse_area_m2(_field(text, "建物面積", "土地面積|私道|物件種目|$"))
    land = parse_area_m2(_field(text, "土地面積", "私道|物件種目|築年月|$"))
    year = _field(text, "築年月", "所在地|交通|$")
    address = _field(text, "所在地", "交通|※|詳細|$")
    access = _field(text, "交通", "※|詳細|$")
    photos_n = re.search(r"写真\s*(\d+)\s*枚", text)

    rent_yen = price_yen if listing_type == "rent" else None
    sale_yen = price_yen if listing_type == "sale" else None

    # NOTA: las fotos de at-home (img.akiya-athome.jp) están protegidas contra
    # hotlinking (devuelven 403 desde otro dominio), así que NO las guardamos
    # para no mostrar imágenes rotas. Las fuentes municipales (suminiko, wakayama)
    # sí traen fotos que cargan bien. El nº total de fotos queda en features.
    photos = []

    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type=listing_type, prop_type=prop_type,
        title=(address or kind or NAME),
        address_raw=address,
        rent_yen=rent_yen, sale_price_yen=sale_yen,
        layout=layout, building_area_m2=building, land_area_m2=land,
        year_built=year,
        photos=photos,
        description_raw=(access or ""),
        foreigner_ok=detect_foreigner_ok(text),
        features={"物件種目": kind, "交通": access,
                  "fotos_total": photos_n.group(1) if photos_n else ""},
    )
    # antigüedad desde 築年月 (1975年3月 -> año)
    ym = re.search(r"(19|20)\d{2}", year or "")
    if ym:
        from datetime import date
        lst.age_years = max(0, date.today().year - int(ym.group()))
    assign_area(lst)
    return lst


def _scrape_pref(client, pref_code):
    results = []
    for br_kbn, ltype in (("buy", "sale"), ("rent", "rent")):
        seen_pages = set()
        for page in range(1, config.ATHOME_MAX_PAGES + 1):
            url = f"{BASE}/{br_kbn}/{pref_code}/?page={page}"
            html = client.get(url)
            if not html:
                break
            soup = BeautifulSoup(html, "lxml")
            anchors = soup.find_all("a", href=re.compile("bukken/detail"))
            if not anchors:
                break
            # contenedor de cada card: el ancestro que contiene precio
            page_urls = set()
            for a in anchors:
                node = a
                for _ in range(6):
                    node = node.parent
                    if node is None:
                        break
                    if "万円" in node.get_text():
                        break
                if node is None:
                    continue
                lst = _parse_card(node, ltype)
                if lst and lst.area_key:  # solo zonas objetivo
                    if lst.source_url not in page_urls:
                        page_urls.add(lst.source_url)
                        results.append(lst)
            # detección de fin de paginación: misma firma de página
            sig = tuple(sorted(a["href"] for a in anchors))
            if sig in seen_pages:
                break
            seen_pages.add(sig)
    return results


def fetch(client):
    results = []
    seen = set()
    for pref_code in config.PREF_CODES:
        try:
            for lst in _scrape_pref(client, pref_code):
                if lst.source_url not in seen:
                    seen.add(lst.source_url)
                    results.append(lst)
        except Exception as e:
            print(f"  [athome] error en prefectura {pref_code}: {e}")
    return results
