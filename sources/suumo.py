# -*- coding: utf-8 -*-
"""
Adaptador: SUUMO (賃貸) — alquileres (apartamentos y casas) para USO PERSONAL.

Pensado para ayudarte a TI a encontrar vivienda (no para redistribuir). Lee las
páginas públicas de resultados de SUUMO (no prohibidas por su robots.txt), con
pausas educadas y un User-Agent de navegador. Las fotos se sirven desde SUUMO
(no se descargan, no ocupan espacio).

Por cada edificio toma la habitación MÁS BARATA como referencia (precio, 間取り,
m²), con sus estaciones de tren y dirección.
"""

import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from sources.base import Listing, assign_area

SLUG = "suumo"
NAME = "SUUMO 賃貸"
BASE = "https://suumo.jp"

# Prefecturas objetivo (slug de SUUMO). Edita esta lista para añadir/quitar.
# La variable de entorno SUUMO_PREFS="tokyo,chiba" la sobreescribe (la usa
# expand_japan.sh para raspar prefectura a prefectura en ciclos).
import os as _os
SUUMO_PREFS = ["osaka", "hyogo", "kyoto", "nara", "shiga", "wakayama", "fukui"]
if _os.environ.get("SUUMO_PREFS"):
    SUUMO_PREFS = [p.strip() for p in _os.environ["SUUMO_PREFS"].split(",") if p.strip()]
# Algunas prefecturas usan un slug distinto en SUUMO (romanización antigua / sufijo).
_SLUG_MAP = {"hokkaido": "hokkaido_", "gunma": "gumma"}
SUUMO_PREFS = [_SLUG_MAP.get(p, p) for p in SUUMO_PREFS]
MAX_PAGES = 3          # páginas por ciudad (20 edificios/página)
DELAY = 2.5            # pausa entre peticiones (educado)

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


def _city_slugs(pref):
    """Saca los slugs sc_<ciudad> de la página de selección de ciudad."""
    html = _get(f"{BASE}/chintai/{pref}/city/")
    slugs = []
    if html:
        for m in re.findall(rf"/chintai/{pref}/(sc_[a-z0-9]+)/", html):
            if m not in slugs:
                slugs.append(m)
    return slugs


def _rent_yen(text):
    # En SUUMO el ALQUILER siempre se muestra en 万円 (p.ej. "7.5万円"); el 管理費
    # va en 円 sueltos ("7,500円"). Solo aceptamos 万円 para no confundir el
    # 管理費 con la renta (bug que dejaba rentas tipo 7.500¥).
    m = re.search(r"([\d.]+)\s*万円", text or "")
    if m:
        return int(round(float(m.group(1)) * 10000))
    return None


def _adm_yen(text):
    """管理費/共益費: '7,110円' -> 7110 · '-' -> 0."""
    m = re.search(r"([\d,]+)\s*円", text or "")
    return int(m.group(1).replace(",", "")) if m else 0


def _km(text):
    """Normaliza 敷金/礼金 para el front (moneyField entiende '8万円'/'なし'/'Xヶ月').
    SUUMO usa '-' para 'nada' -> lo pasamos a 'なし' (si no, moneyField usaría el
    valor por defecto en vez de 0)."""
    t = (text or "").strip()
    if not t or t in ("-", "ー", "−") or "なし" in t:
        return "なし"
    return t


def _parse_page(html, pref):
    out = []
    soup = BeautifulSoup(html, "lxml")
    for c in soup.find_all(class_="cassetteitem"):
        title = c.find(class_="cassetteitem_content-title")
        name = title.get_text(strip=True) if title else ""
        addr_el = c.find(class_="cassetteitem_detail-col1")
        address = addr_el.get_text(" ", strip=True) if addr_el else ""
        sta_el = c.find(class_="cassetteitem_detail-col2")
        stations = sta_el.get_text(" / ", strip=True) if sta_el else ""
        kind_el = c.find(class_="cassetteitem_content-label")
        kind = kind_el.get_text(strip=True) if kind_el else ""
        prop_type = "house" if ("一戸建" in kind or "戸建" in name) else "apartment"
        img = c.find("img", {"rel": True}) or c.find("img")
        photo = ""
        if img:
            photo = img.get("rel") or img.get("data-src") or img.get("src") or ""
            if isinstance(photo, list):
                photo = photo[0]

        # 築年 y 階建 (en la columna 3 del detalle del edificio: "築2年 | 15階建")
        col3 = c.find(class_="cassetteitem_detail-col3")
        built_txt = col3.get_text(" ", strip=True) if col3 else ""
        age_years = None
        year_built = ""
        mb = re.search(r"築\s*(\d+)\s*年", built_txt)
        if mb:
            age_years = int(mb.group(1)); year_built = f"築{age_years}年"
        elif "新築" in built_txt:
            age_years = 0; year_built = "新築"
        mf = re.search(r"(\d+)\s*階建", built_txt)
        floors = mf.group(0) if mf else ""

        # recorre todas las habitaciones: guarda la más barata y el RANGO real
        best = None
        rents = []
        for tr in c.select("table.cassetteitem_other tbody tr, tbody.js-cassette_link tr"):
            rent_el = tr.find(class_=re.compile("cassetteitem_other-emphasis|cassetteitem_price--rent"))
            if not rent_el:
                continue
            rent = _rent_yen(rent_el.get_text())
            mad = tr.find(class_="cassetteitem_madori")
            men = tr.find(class_="cassetteitem_menseki")
            link = tr.find("a", href=re.compile("/chintai/"))
            adm = tr.find(class_=re.compile("cassetteitem_price--adm"))
            dep = tr.find(class_=re.compile("cassetteitem_price--dep"))
            gra = tr.find(class_=re.compile("cassetteitem_price--gra"))
            room = {
                "rent": rent,
                "layout": mad.get_text(strip=True) if mad else "",
                "area": men.get_text(strip=True) if men else "",
                "url": urljoin(BASE, link["href"]) if link and link.get("href") else "",
                "mgmt": _adm_yen(adm.get_text()) if adm else 0,
                "deposit": _km(dep.get_text()) if dep else "",   # 敷金
                "key": _km(gra.get_text()) if gra else "",       # 礼金
            }
            if rent:
                rents.append(rent)
            if rent and (best is None or rent < best["rent"]):
                best = room
        if not best:
            continue
        # rango honesto: si el edificio tiene habitaciones a precios distintos
        feats = {"交通": stations, "contacto": "Ver anuncio en SUUMO (inmobiliaria)"}
        if rents and max(rents) > min(rents):
            feats["rent_range"] = f"{min(rents):,}円～{max(rents):,}円"
        if built_txt:
            feats["築年月"] = year_built or built_txt

        from sources.base import parse_area_m2
        lst = Listing(
            source=SLUG, source_name=NAME,
            source_url=best["url"] or f"{BASE}/chintai/{pref}/",
            listing_type="rent", prop_type=prop_type,
            title=f"{name}（{address.split('区')[0][:10]}）" if name else name,
            address_raw=address,
            rent_yen=best["rent"],
            management_fee_yen=best["mgmt"],
            deposit=best["deposit"], key_money=best["key"],
            layout=best["layout"],
            building_area_m2=parse_area_m2(best["area"]),
            year_built=year_built, age_years=age_years, floors=floors,
            photos=[photo] if photo and photo.startswith("http") else [],
            description_raw=f"SUUMO · {kind}",
            features=feats,
        )
        assign_area(lst)
        out.append(lst)
    return out


def fetch(client):
    results = []
    seen = set()
    for pref in SUUMO_PREFS:
        for slug in _city_slugs(pref):
            for page in range(1, MAX_PAGES + 1):
                html = _get(f"{BASE}/chintai/{pref}/{slug}/?page={page}")
                if not html:
                    break
                page_items = _parse_page(html, pref)
                if not page_items:
                    break
                for lst in page_items:
                    key = lst.source_url
                    if key and key not in seen:
                        seen.add(key)
                        results.append(lst)
    return results
