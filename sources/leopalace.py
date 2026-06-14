# -*- coding: utf-8 -*-
"""
Adaptador: Leopalace21 (レオパレス21) — alquileres amueblados para EXTRANJEROS,
con poca/cero entrada (su API trae 礼金/敷金/仲介 reales, casi siempre 0).

API REST (Spring Boot) descubierta:
  /api/properties/search?language=ja&contractType=chintai&prefectureCode={1..47}&page=N
  -> {count, apartments:[{apartmentNo, propertyName, address, latitude, longitude,
       buildDay, properties:[{rentFee, shikikin, reikin, brokerageFee, layout, size,...}]}]}
  Trae COORDENADAS inline (no hace falta geocodificar). Pagina de 2 en 2.

Leopalace tiene ~200k habitaciones; aquí tomamos una MUESTRA acotada por prefectura
(MAX_PAGES) para dar cobertura nacional de opción "extranjeros" sin inundar el banco.
"""

import time
import requests

import config
from sources.base import Listing, assign_area

SLUG = "leopalace"
NAME = "🌏 Leopalace21"
BASE = "https://www.leopalace21.com"
SEARCH = BASE + "/api/properties/search"
MAX_PAGES = 10          # ~20 edificios/prefectura (~940 total)
DELAY = 0.7

_sess = requests.Session()
_sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json",
})


def _months(v):
    """礼金/敷金 vienen en MESES (0.0, 1.0...). Para el front: 0 -> なし, si no 'Xヶ月'."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "なし" if f == 0 else (f"{f:g}ヶ月")


def _get(code, page):
    try:
        r = _sess.get(SEARCH, params={"language": "ja", "contractType": "chintai",
                                      "prefectureCode": code, "page": page},
                      timeout=config.HTTP_TIMEOUT)
        time.sleep(DELAY)
        return r.json() if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _apartment_to_listing(a):
    lat, lng = a.get("latitude"), a.get("longitude")
    addr = a.get("address") or a.get("addressJa") or ""
    if not addr:
        return None
    rooms = a.get("properties") or []
    # habitación de referencia: el alquiler más barato con precio
    best = None
    for r in rooms:
        rf = r.get("rentFee") or 0
        if rf and (best is None or rf < best.get("rentFee", 1e9)):
            best = r
    best = best or (rooms[0] if rooms else {})
    rent = best.get("rentFee") or None
    bd = str(a.get("buildDay") or "")          # 200401 -> 2004
    year = bd[:4] if len(bd) >= 4 else ""
    rt = a.get("route") or best.get("route") or {}
    station = ""
    if rt:
        station = f"{rt.get('lineName','')} {rt.get('stationName','')}駅 徒歩{rt.get('stationWalkingTime','')}分"
    apt = a.get("apartmentNo", "")
    url = (f"{BASE}/rooms/{a.get('prefectureNameParam','')}/{a.get('areaNameParam','')}/"
           f"{a.get('propertyNameParam','')}/#{apt}")

    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type="rent", prop_type="apartment",
        title=f"{a.get('propertyName','Leopalace')}（{addr[:16]}）",
        address_raw=addr,
        rent_yen=int(rent) if rent else None,
        management_fee_yen=int(best.get("maintenanceFee") or 0),
        key_money=_months(best.get("reikin")),
        deposit=_months(best.get("shikikin")),
        layout=best.get("layout") or "",
        building_area_m2=(float(best["size"]) if best.get("size") else None),
        year_built=(f"{year}年" if year else ""),
        foreigner_ok="yes",
        description_raw="Leopalace21 · amueblado · soporte multilingüe · poca/cero entrada",
        features={"交通": station, "物件種目": "賃貸 (Leopalace)",
                  "contacto": "Leopalace21 (multilingüe)", "contacto_web": url},
    )
    if year:
        from datetime import date
        try:
            lst.age_years = max(0, date.today().year - int(year))
        except ValueError:
            pass
    # coords directas (sin geocodificar)
    if lat and lng:
        lst.lat, lst.lng = lat, lng
        lst.geocode_source, lst.geocode_exact = "leopalace", 1
    assign_area(lst)
    return lst


def fetch(client):
    out, seen = [], set()
    for code in range(1, 48):
        for page in range(1, MAX_PAGES + 1):
            d = _get(code, page)
            apts = (d or {}).get("apartments") or []
            if not apts:
                break
            added = 0
            for a in apts:
                try:
                    lst = _apartment_to_listing(a)
                except Exception:
                    continue
                if lst and lst.area_key and lst.source_url not in seen:
                    seen.add(lst.source_url)
                    out.append(lst)
                    added += 1
            if added == 0:
                break
    print(f"  [leopalace] {len(out)} edificios (extranjeros, poca/cero entrada)")
    return out
