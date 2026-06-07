# -*- coding: utf-8 -*-
"""
Adaptador: 住みニコ — banco de casas vacías de 南あわじ市 (淡路島).
Incluye zonas como 福良 (Fukura) y la isla 沼島 (Nushima).

Sitio: https://www.suminiko.jp/
  - Índice de anuncios activos:  list.php   (enlaces a detail.php?bid=N)
  - Ficha de cada casa:          detail.php?bid=N  (tabla.bukkeninfo)

Es un banco municipal/público pensado para atraer residentes (移住者),
así que es una fuente apropiada para consultar con educación y rate limit.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.base import (
    Listing, parse_price_yen, parse_area_m2, parse_parking,
    detect_foreigner_ok, detect_renovated, detect_pet, parse_year_built,
    assign_area,
)

SLUG = "suminiko"
NAME = "住みニコ（南あわじ市 空き家バンク）"
BASE = "https://www.suminiko.jp/"
INDEX_URL = BASE + "list.php"


def _collect_detail_urls(client):
    """Devuelve la lista de URLs de fichas activas desde list.php."""
    html = client.get(INDEX_URL)
    urls = set()
    if html:
        for bid in re.findall(r"detail\.php\?bid=(\d+)", html):
            urls.add(urljoin(BASE, f"detail.php?bid={bid}"))
    return sorted(urls)


def _table_to_dict(soup):
    """Aplana la tabla.bukkeninfo en pares clave->valor.

    Las filas pueden traer 1, 2 o 3 pares (th,td,th,td,...). Tomamos las celdas
    de dos en dos. Las cabeceras sueltas (一sola celda, p.ej. '設備') se ignoran
    como clave pero conservamos sub-filas siguientes.
    """
    info = {}
    for tbl in soup.find_all("table", class_="bukkeninfo"):
        for tr in tbl.find_all("tr"):
            cells = [c.get_text(" ", strip=True).replace("　", " ")
                     for c in tr.find_all(["th", "td"])]
            # pares (clave, valor)
            for i in range(0, len(cells) - 1, 2):
                key = cells[i].strip()
                val = cells[i + 1].strip()
                if key and key not in info:
                    info[key] = val
    return info


def _extract_photos(soup):
    photos = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        # Las fotos reales de la casa viven en /kanri/up/
        if "kanri/up/" in src:
            full = urljoin(BASE, src)
            if full not in photos:
                photos.append(full)
    return photos


def _parse_detail(client, url):
    html = client.get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    info = _table_to_dict(soup)
    if not info:
        return None

    # ----- precio / tipo de operación ----------------------------------
    price_text = info.get("価格", "")
    listing_type = "rent" if ("賃" in price_text or "賃貸" in price_text or "賃料" in price_text) else "sale"
    rent_yen = sale_price_yen = None
    if listing_type == "rent":
        rent_yen = parse_price_yen(price_text)
    else:
        sale_price_yen = parse_price_yen(price_text)

    # ----- título y descripción ----------------------------------------
    # En la ficha, dentro de div.bankdetail, los dos primeros div.cf son
    # el título de la casa y una frase descriptiva corta.
    title = ""
    description = ""
    cfs = []
    bankdetail = soup.find("div", class_="bankdetail")
    if bankdetail:
        cfs = [c.get_text(" ", strip=True) for c in bankdetail.find_all("div", class_="cf")]
        cfs = [c for c in cfs if c and "画像をクリック" not in c]
    if cfs:
        title = cfs[0]
        description = " ".join(cfs[1:])[:1500]
    # Número de物件 (物件番号:A312号) por si sirve de referencia.
    bukken_no = ""
    p_no = soup.find("p", class_="bukken")
    if p_no:
        bukken_no = p_no.get_text(strip=True)

    address = info.get("所在地", "")
    structure = info.get("構造", "")
    land = parse_area_m2(info.get("敷地面積", ""))
    building = parse_area_m2(info.get("延床面積", info.get("建物面積", "")))
    layout = info.get("間取り", "")
    year_raw, age = parse_year_built(info.get("築年", ""))
    parking, parking_detail = parse_parking(info.get("車庫", info.get("駐車場", "")))
    status_note = info.get("物件の利用状況", "")
    remarks = info.get("備考", "")

    blob = " ".join([description, remarks, structure, info.get("ペット", ""), info.get("設備", "")])

    listing = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type=listing_type,
        title=title or info.get("所在地", NAME),
        address_raw=address,
        rent_yen=rent_yen, sale_price_yen=sale_price_yen,
        layout=layout,
        building_area_m2=building, land_area_m2=land,
        year_built=year_raw, age_years=age,
        structure=structure,
        parking=parking, parking_detail=parking_detail,
        foreigner_ok=detect_foreigner_ok(blob),
        pet_ok=detect_pet(info.get("ペット", "") + " " + blob),
        renovated=detect_renovated(blob),
        photos=_extract_photos(soup),
        description_raw=(description + " " + remarks).strip(),
        status_note=status_note,
        features=dict(
            {"物件番号": bukken_no} if bukken_no else {},
            **{k: v for k, v in {
                "contacto": info.get("名称", ""),
                "contacto_tel": info.get("ＴＥＬ", "") or info.get("TEL", ""),
                "contacto_web": info.get("ＨＰアドレス", ""),
            }.items() if v},
            **{k: v for k, v in info.items() if k in (
                "設備", "庭", "収納", "農地面積", "付帯施設等", "トイレ", "風呂", "水道", "ガス")},
        ),
    )
    listing.prefecture = "兵庫県"
    listing.city = "南あわじ市"
    assign_area(listing)
    if not listing.area_key:
        # Esta fuente es siempre 南あわじ市 aunque la dirección no lo repita.
        listing.area_key = "minamiawaji"
    return listing


def fetch(client):
    """Punto de entrada estándar del adaptador: devuelve list[Listing]."""
    results = []
    for url in _collect_detail_urls(client):
        try:
            lst = _parse_detail(client, url)
            if lst:
                results.append(lst)
        except Exception as e:
            print(f"  [suminiko] error parseando {url}: {e}")
    return results
