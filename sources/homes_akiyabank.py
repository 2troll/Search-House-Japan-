# -*- coding: utf-8 -*-
"""
Adaptador: LIFULL HOME'S 空き家バンク (agregador nacional).

Página por municipio, p. ej.:
  https://www.homes.co.jp/akiyabank/hyogo/minamiawaji/
  https://www.homes.co.jp/akiyabank/wakayama/shirahama/

IMPORTANTE — extracción responsable:
  - Este es un AGREGADOR comercial. Aunque /akiyabank/ no está en su robots.txt,
    su sección de 空き家バンク reúne los bancos municipales. Usamos rate limit
    estricto y, sobre todo, NOS QUEDAMOS CON LOS ENLACES a la ficha original.
  - El HttpClient ya respeta robots.txt automáticamente; si HOME'S bloquea una
    ruta, se omitirá sola.
  - Está DESACTIVADO por defecto en sources/registry.py. Actívalo bajo tu
    criterio y para uso personal, sin redistribuir los datos.

MUNICIPIOS_HOMES asocia cada zona de TARGET_AREAS con su ruta en HOME'S.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import Listing, parse_price_yen, assign_area
import config

SLUG = "homes_akiyabank"
NAME = "LIFULL HOME'S 空き家バンク"
BASE = "https://www.homes.co.jp/akiyabank/"

# zona_key -> "prefectura_romaji/municipio_romaji" en la URL de HOME'S.
MUNICIPIOS_HOMES = {
    "minamiawaji": "hyogo/minamiawaji/",
    "sumoto":      "hyogo/sumoto/",
    "awaji_shi":   "hyogo/awaji/",
    "shirahama":   "wakayama/shirahama/",
    "kushimoto":   "wakayama/kushimoto/",
    "nachikatsuura": "wakayama/nachikatsuura/",
    "tanabe":      "wakayama/tanabe/",
    "wakayama_shi": "wakayama/wakayama/",
}


def _parse_municipio(client, area_key, path):
    url = urljoin(BASE, path)
    html = client.get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    area = next((a for a in config.TARGET_AREAS if a["key"] == area_key), None)
    results = []
    seen = set()

    # Heurística genérica: tarjetas de propiedad con enlace a /akiyabank/.../bukken o detalle.
    for a in soup.select("a[href*='akiyabank']"):
        href = urljoin(url, a.get("href", ""))
        if href in seen or href.rstrip("/") == url.rstrip("/"):
            continue
        # solo enlaces que parezcan una ficha individual
        if not re.search(r"/(b-\d+|bukken|\d{6,})", href):
            continue
        seen.add(href)
        text = a.get_text(" ", strip=True)
        price = parse_price_yen(text)
        lst = Listing(
            source=SLUG, source_name=NAME, source_url=href,
            listing_type="sale",
            title=text or NAME,
            prefecture=area["pref"] if area else "",
            city=area["ja"] if area else "",
            address_raw=(area["pref"] + area["ja"]) if area else "",
            sale_price_yen=price,
            description_raw=text,
        )
        lst.area_key = area_key
        assign_area(lst)
        lst.area_key = lst.area_key or area_key
        results.append(lst)
    return results


def fetch(client):
    results = []
    for area_key, path in MUNICIPIOS_HOMES.items():
        try:
            results.extend(_parse_municipio(client, area_key, path))
        except Exception as e:
            print(f"  [homes] error en {area_key}: {e}")
    return results
