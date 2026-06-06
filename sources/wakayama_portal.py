# -*- coding: utf-8 -*-
"""
Adaptador: わかやま住まいポータルサイト (banco de casas vacías de la PREFECTURA
de Wakayama). Una sola fuente que cubre TODOS los municipios de Wakayama, así
que de aquí salen 白浜町, 串本町, 那智勝浦町, 田辺市 y 和歌山市 de golpe.

Sitio: https://www.wakayamagurashi.jp/house/search/
  - Listado paginado:  /house/search/pages/N   (12 fichas por página, en .property-list)
  - Ficha individual:  /house/search/{id}

Estrategia eficiente y educada:
  1. Recorre las páginas del listado y lee el 所在地 (ubicación) de cada ficha.
  2. PRE-FILTRA: solo continúa con las fichas cuyo municipio esté en TARGET_AREAS.
  3. Solo para esas descarga la ficha completa (建物面積, 構造, 駐車場, fotos...).
Así no descargamos cientos de fichas de toda la prefectura, solo las que te
interesan. robots.txt permite /house/.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import (
    Listing, parse_price_yen, parse_area_m2, parse_parking,
    detect_foreigner_ok, detect_renovated, parse_year_built, assign_area,
)
import config

SLUG = "wakayama_portal"
NAME = "わかやま住まいポータル（和歌山県 空き家バンク）"
BASE = "https://www.wakayamagurashi.jp/house/search/"
MAX_PAGES = 30  # tope de seguridad de páginas del listado a recorrer

_SHOZAI_RE = re.compile(r"所在地\s*(.+?)\s*価格")


def _detail_field(soup, label):
    """Extrae el valor de un campo de la ficha buscando la fila que empieza por `label`."""
    for el in soup.find_all(["span", "div", "p", "li", "dd", "dt", "td"]):
        txt = el.get_text(" ", strip=True)
        if txt.startswith(label) and txt != label and len(txt) < 90:
            return txt[len(label):].strip()
    return ""


def _collect_list_items(client):
    """Devuelve [(detail_url, shozai_texto)] de TODO el listado paginado."""
    items = []
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        html = client.get(urljoin(BASE, f"pages/{page}"))
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        plist = soup.find(class_="property-list")
        if not plist:
            break
        anchors = plist.find_all("a", href=True)
        if not anchors:
            break
        new_on_page = 0
        for a in anchors:
            href = urljoin(urljoin(BASE, f"pages/{page}"), a["href"])
            # normaliza a /house/search/{id}
            m = re.search(r"search/(\d+)", href)
            if not m:
                continue
            detail_url = urljoin(BASE, m.group(1))
            if detail_url in seen:
                continue
            seen.add(detail_url)
            text = a.get_text(" ", strip=True)
            sm = _SHOZAI_RE.search(text)
            shozai = sm.group(1) if sm else text
            items.append((detail_url, shozai))
            new_on_page += 1
        if new_on_page == 0:
            break
    return items


def _parse_detail(client, url, shozai_hint):
    html = client.get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.extract()

    kubun = _detail_field(soup, "区分")          # 売買 / 賃貸
    address = _detail_field(soup, "所在地") or shozai_hint
    price_txt = _detail_field(soup, "価格")
    bukken_kind = _detail_field(soup, "物件区分")  # 一戸建て / マンション ...
    layout = _detail_field(soup, "間取り")
    year_txt = _detail_field(soup, "建築年")
    building = parse_area_m2(_detail_field(soup, "建物面積"))
    land = parse_area_m2(_detail_field(soup, "土地面積"))
    structure = _detail_field(soup, "建物構造")
    floors = _detail_field(soup, "建物階層")
    parking_txt = _detail_field(soup, "駐車場")

    listing_type = "rent" if "賃" in kubun else "sale"
    rent_yen = parse_price_yen(price_txt) if listing_type == "rent" else None
    sale_yen = parse_price_yen(price_txt) if listing_type == "sale" else None
    year_raw, age = parse_year_built(year_txt)
    parking, pdetail = parse_parking(parking_txt)

    # fotos (dedup; el álbum repite miniaturas y tamaños)
    photos = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "user_images/property" in src and src not in photos:
            photos.append(src)

    full_text = " ".join([address, structure, layout, bukken_kind])
    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type=listing_type,
        title=f"{address}　{structure}{('　'+layout) if layout else ''}".strip(),
        prefecture="和歌山県",
        address_raw=("和歌山県" + address) if not address.startswith("和歌山") else address,
        rent_yen=rent_yen, sale_price_yen=sale_yen,
        layout=layout, building_area_m2=building, land_area_m2=land,
        year_built=year_raw, age_years=age,
        structure=structure, floors=floors,
        parking=parking, parking_detail=pdetail,
        foreigner_ok=detect_foreigner_ok(full_text),
        renovated=detect_renovated(full_text),
        photos=photos,
        description_raw=address,
        features={"物件区分": bukken_kind} if bukken_kind else {},
    )
    assign_area(lst)
    return lst, bukken_kind


def fetch(client):
    results = []
    for detail_url, shozai in _collect_list_items(client):
        # PRE-FILTRO por municipio: solo zonas de TARGET_AREAS.
        if not config.match_area(shozai):
            continue
        try:
            parsed = _parse_detail(client, detail_url, shozai)
            if not parsed:
                continue
            lst, kind = parsed
            # Solo casas unifamiliares (戸建て); descarta マンション/アパート.
            if kind and ("マンション" in kind or "アパート" in kind):
                continue
            if lst.area_key:  # confirma que cayó en una zona objetivo
                results.append(lst)
        except Exception as e:
            print(f"  [wakayama] error en {detail_url}: {e}")
    return results
