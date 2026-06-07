# -*- coding: utf-8 -*-
"""
Adaptador: 洲本移住ナビ — banco de casas vacías de 洲本市 (淡路島).

Sitio: https://sumo-navi.com/akiyabank/  (WordPress, paginado /page/N/)
Cada anuncio enlaza a un PDF con TODA la ficha (precio, 所在地, 交通, 土地/建物,
築年数, 間取り, 設備...). Antes solo leíamos el título; ahora ABRIMOS EL PDF,
extraemos todo el texto (los PDFs llevan texto real, sin OCR) y lo normalizamos.
Las etiquetas se traducen al español en la interfaz.
"""

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from sources.base import (
    Listing, parse_price_yen, parse_area_m2, parse_parking,
    detect_foreigner_ok, detect_renovated, parse_year_built, assign_area, zen2han,
)

SLUG = "sumonavi"
NAME = "洲本移住ナビ（洲本市 空き家バンク）"
BASE = "https://sumo-navi.com/akiyabank/"
MAX_PAGES = 6

_pdf_session = requests.Session()
_pdf_session.headers.update({"User-Agent": config.USER_AGENT})


def _page_urls():
    yield BASE
    for n in range(2, MAX_PAGES + 1):
        yield urljoin(BASE, f"page/{n}/")


def _collect_pdf_links(client):
    """Devuelve [(pdf_url, listing_type)] de todas las páginas del listado."""
    out, seen = [], set()
    for page_url in _page_urls():
        html = client.get(page_url)
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        found = 0
        for a in soup.find_all("a", href=True):
            t = a.get_text(" ", strip=True)
            if "（売買）" in t or "（賃貸）" in t:
                href = a["href"].split("#")[0]
                if href.lower().endswith(".pdf") and href not in seen:
                    seen.add(href)
                    ltype = "rent" if "（賃貸）" in t else "sale"
                    out.append((href, ltype))
                    found += 1
        if found == 0:
            break
    return out


def _pdf_text(url):
    """Descarga el PDF y devuelve su texto (con pypdfium2). '' si falla."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print("  [sumonavi] falta pypdfium2 (pip install pypdfium2); se omite el PDF")
        return ""
    try:
        r = _pdf_session.get(url, timeout=config.HTTP_TIMEOUT)
        if r.status_code != 200:
            return ""
        import io
        pdf = pdfium.PdfDocument(io.BytesIO(r.content))
        parts = []
        for i in range(len(pdf)):
            parts.append(pdf[i].get_textpage().get_text_range())
        pdf.close()
        return "\n".join(parts)
    except Exception as e:
        print(f"  [sumonavi] error leyendo PDF {url}: {e}")
        return ""


def _field(text, label, stop=r"\r|\n|$"):
    m = re.search(re.escape(label) + r"\s*(.+?)\s*(?:" + stop + r")", text)
    return m.group(1).strip() if m else ""


def _parse_pdf(text, url, listing_type):
    raw = text
    t = zen2han(text)

    # precio
    pm = re.search(r"(?:価格|賃料)\s*([\d,\.]+)\s*万円", t) or re.search(r"(?:価格|賃料)\s*([\d,\.]+)\s*円", t)
    price = parse_price_yen(pm.group(0)) if pm else None
    rent = price if listing_type == "rent" else None
    sale = price if listing_type == "sale" else None

    name = _field(raw, "名称") or "洲本市 空き家"
    # 所在 / 所在地
    address = _field(raw, "所在地") or _field(raw, "所在")
    access = _field(raw, "交通")
    structure = _field(raw, "構造")
    floors = _field(raw, "階層") or _field(raw, "建物階層")

    # áreas: puede haber dos "面積" (土地 y 建物); la de 坪 suele ser terreno
    areas = re.findall(r"面積\s*([\d\.]+)\s*㎡", t)
    land = building = None
    lm = re.search(r"土地[\s\S]{0,18}?面積\s*([\d\.]+)", t)
    if lm:
        land = float(lm.group(1))
    for a in areas:
        v = float(a)
        if land is not None and abs(v - land) < 0.01:
            continue
        building = v
        break
    if land is None and areas:
        land = float(areas[-1])

    # distribución (4LDK, 3DK, 1R...)
    lay = re.search(r"([1-9]\d?\s*[SLDKR]+)", t)
    layout = lay.group(1).replace(" ", "") if lay else _field(raw, "間取り")
    layout = zen2han(layout)

    year_raw, age = parse_year_built(_field(raw, "築年月") or _field(raw, "築年数") or t)
    parking, pdetail = parse_parking(
        _field(raw, "駐車場") or _field(raw, "車庫") or ("あり" if "駐車" in raw else ""))
    remarks = _field(raw, "備考")

    # contacto (teléfono, email, agencia) — están en el PDF
    mtel = re.search(r"0\d{1,3}[-‐－]\d{2,4}[-‐－]\d{3,4}", raw)
    tel = mtel.group(0).replace("‐", "-").replace("－", "-") if mtel else ""
    memail = re.search(r"[\w.\-]+@[\w.\-]+\.\w+", raw)
    email = memail.group(0) if memail else ""
    magency = re.search(r"\S*(?:株式会社|有限会社)\S*", raw)
    agency = magency.group(0) if magency else ""

    blob = raw
    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type=listing_type, prop_type="house",
        title=f"{name}（{address}）" if address else name,
        prefecture="兵庫県", city="洲本市",
        address_raw=address or "兵庫県洲本市",
        rent_yen=rent, sale_price_yen=sale,
        layout=layout, structure=structure, floors=floors,
        building_area_m2=building, land_area_m2=land,
        year_built=year_raw, age_years=age,
        parking=parking, parking_detail=pdetail,
        foreigner_ok=detect_foreigner_ok(blob),
        renovated=detect_renovated(blob),
        description_raw=remarks,
        status_note="",
        features={k: v for k, v in {
            "交通": access,
            "設備": " ".join(filter(None, [
                ("電気:" + _field(raw, "電気")) if _field(raw, "電気") else "",
                ("ガス:" + _field(raw, "ガス")) if _field(raw, "ガス") else "",
                ("水道:" + _field(raw, "水道")) if _field(raw, "水道") else "",
                ("下水道:" + _field(raw, "下水道")) if _field(raw, "下水道") else "",
            ])).strip(),
            "土地権利": _field(raw, "土地権利"),
            "備考": remarks,
            "contacto": agency,
            "contacto_tel": tel,
            "contacto_email": email,
        }.items() if v},
    )
    assign_area(lst)
    lst.area_key = lst.area_key or "sumoto"
    return lst


def fetch(client):
    results = []
    for pdf_url, ltype in _collect_pdf_links(client):
        text = _pdf_text(pdf_url)
        if not text:
            continue
        try:
            lst = _parse_pdf(text, pdf_url, ltype)
            if lst:
                results.append(lst)
        except Exception as e:
            print(f"  [sumonavi] error parseando {pdf_url}: {e}")
    return results
