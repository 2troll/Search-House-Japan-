# -*- coding: utf-8 -*-
"""
Adaptador: 洲本移住ナビ — banco de casas vacías de 洲本市 (淡路島).

Sitio: https://sumo-navi.com/akiyabank/  (WordPress, paginado /page/N/)
Cada anuncio aparece como un enlace cuyo texto es del estilo:
    "千草庚　木造4SDK（売買）　202605B1号"
y enlaza a un PDF con la ficha completa.

De ese título podemos extraer: barrio (para geocodificar), estructura (木造),
distribución (4SDK) y tipo de operación (売買/賃貸). El precio detallado vive
en el PDF, así que aquí lo dejamos como desconocido (se puede completar a mano
o, más adelante, parseando el PDF). El robots.txt permite /akiyabank/.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import Listing, assign_area

SLUG = "sumonavi"
NAME = "洲本移住ナビ（洲本市 空き家バンク）"
BASE = "https://sumo-navi.com/akiyabank/"
MAX_PAGES = 6  # límite de páginas a recorrer (paginación /page/N/)

# Estructuras conocidas que pueden aparecer en el título (orden = prioridad).
_STRUCTURES = ["鉄筋コンクリート造", "軽量鉄骨", "鉄骨造", "鉄骨", "木造", "RC"]
_LAYOUT_RE = re.compile(r"[1-9０-９]+\s*[SLDKR]+")
_AREA_RE = re.compile(r"^([^\s　]+)")


def _page_urls():
    yield BASE
    for n in range(2, MAX_PAGES + 1):
        yield urljoin(BASE, f"page/{n}/")


def _parse_listing_anchor(a):
    text = a.get_text(" ", strip=True).replace("･･･", "").strip()
    href = a.get("href", "").split("#")[0]
    if not href or "（売買）" not in text and "（賃貸）" not in text:
        return None

    listing_type = "rent" if "（賃貸）" in text else "sale"
    # barrio (primer "palabra" antes del primer espacio)
    am = _AREA_RE.match(text)
    area_name = am.group(1) if am else ""
    # estructura (primera que aparezca en el título)
    structure = next((s for s in _STRUCTURES if s in text), "")
    # distribución (p. ej. 4SDK, 2K)
    lm = _LAYOUT_RE.search(text)
    layout = lm.group().replace(" ", "").upper() if lm else ""

    lst = Listing(
        source=SLUG, source_name=NAME, source_url=href,
        listing_type=listing_type,
        title=text,
        prefecture="兵庫県", city="洲本市",
        # dirección aproximada para geocodificar: 洲本市 + barrio del título
        address_raw=("兵庫県洲本市" + area_name) if area_name else "兵庫県洲本市",
        layout=layout, structure=structure,
        description_raw=text,
        features={"ficha_pdf": href},
    )
    lst.area_key = "sumoto"
    assign_area(lst)
    lst.area_key = lst.area_key or "sumoto"
    return lst


def fetch(client):
    results = []
    seen = set()
    for page_url in _page_urls():
        html = client.get(page_url)
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        found_on_page = 0
        for a in soup.find_all("a"):
            t = a.get_text(" ", strip=True)
            if "（売買）" in t or "（賃貸）" in t:
                lst = _parse_listing_anchor(a)
                if lst and lst.source_url not in seen:
                    seen.add(lst.source_url)
                    results.append(lst)
                    found_on_page += 1
        if found_on_page == 0:
            break  # no hay más páginas con anuncios
    return results
