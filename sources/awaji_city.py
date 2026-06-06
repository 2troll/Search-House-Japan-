# -*- coding: utf-8 -*-
"""
Adaptador: 淡路市 空き家バンク (web oficial del ayuntamiento).

Página: https://www.city.awaji.lg.jp/site/kurashi/akiyabank.html

Las webs municipales cambian de estructura a menudo y muchas publican las
fichas como PDF. Este adaptador es CONSERVADOR: recopila los enlaces a fichas
de cada propiedad (PDF/subpáginas) bajo la sección del banco de casas y crea
una entrada mínima por cada uno, geocodificada a 淡路市. Así no pierdes el
anuncio aunque no podamos extraer todos los campos automáticamente.

Está DESACTIVADO por defecto en sources/registry.py: actívalo cuando hayas
comprobado que la estructura de la página sigue siendo válida.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import Listing, assign_area

SLUG = "awaji_city"
NAME = "淡路市 空き家バンク"
INDEX_URL = "https://www.city.awaji.lg.jp/site/kurashi/akiyabank.html"


def fetch(client):
    results = []
    html = client.get(INDEX_URL)
    if not html:
        return results
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(INDEX_URL, a["href"])
        text = a.get_text(" ", strip=True)
        # Heurística: enlaces a fichas de propiedad (PDF o subpágina con nº de物件)
        if href in seen:
            continue
        if re.search(r"\.pdf$", href, re.I) or re.search(r"(物件|空き家|No\.?\d+|号)", text):
            if not text or len(text) < 4:
                continue
            seen.add(href)
            lst = Listing(
                source=SLUG, source_name=NAME, source_url=href,
                listing_type="sale",
                title=text,
                prefecture="兵庫県", city="淡路市",
                address_raw="兵庫県淡路市",
                description_raw=text,
            )
            lst.area_key = "awaji_shi"
            assign_area(lst)
            lst.area_key = lst.area_key or "awaji_shi"
            results.append(lst)
    return results
