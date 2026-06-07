# -*- coding: utf-8 -*-
"""
Adaptador: UR賃貸 (UR都市機構) — APARTAMENTOS públicos en alquiler.

UR es vivienda pública: **admite extranjeros, sin agencia, sin 礼金 (key money),
sin avalista (保証人) y sin comisión**. Ideal para el usuario. Cubre toda la zona
de Kansai (Osaka, Kobe/Hyogo, Kyoto, Nara, Shiga...).

API (descubierta del frontend de UR):
  - Códigos de área:  GET  https://chintai.r6.ur-net.go.jp/chintai/rent/<tdfk>.json
  - Listado:          POST https://chintai.r6.ur-net.go.jp/chintai/api/bukken/search/list_bukken/
                      datos: tdfk, area, mode=init, pageIndex, rent_low, rent_high
Las fotos se sirven desde el propio UR (cargan cross-origin), no hace falta descargarlas.
"""

import re
import json as _json

import requests
from bs4 import BeautifulSoup

import config
from sources.base import Listing, assign_area

SLUG = "ur"
NAME = "UR賃貸（UR都市機構・公共・admite extranjeros）"
API = "https://chintai.r6.ur-net.go.jp"
WWW = "https://www.ur-net.go.jp"

# Prefecturas de Kansai (código JIS) -> prefectura japonesa para clasificar.
UR_PREFS = {
    "27": "大阪府", "28": "兵庫県", "26": "京都府",
    "29": "奈良県", "25": "滋賀県", "30": "和歌山県",
}

_sess = requests.Session()
_sess.headers.update({"User-Agent": config.USER_AGENT, "Referer": WWW + "/"})


def _areas(tdfk):
    """Devuelve los códigos de área de una prefectura (del JSON rent)."""
    try:
        r = _sess.get(f"{API}/chintai/rent/{tdfk}.json", timeout=config.HTTP_TIMEOUT)
        data = _json.loads(r.content.decode("utf-8-sig"))
        for x in data:
            if x.get("category") == "skcs":
                return sorted({s["area"] for s in x.get("skcsList", [])})
    except Exception:
        pass
    return ["01", "02", "03", "04", "05"]  # respaldo


def _rent_low(text):
    """'49,600円～101,900円' -> 49600 (la más barata)."""
    m = re.search(r"([\d,]+)\s*円", text or "")
    return int(m.group(1).replace(",", "")) if m else None


def _list_area(tdfk, area):
    """Lista los danchi de un área. La API repite resultados al paginar, así que
    paramos cuando una página no aporta IDs nuevos."""
    out, seen = [], set()
    for page in range(0, 15):
        try:
            r = _sess.post(
                f"{API}/chintai/api/bukken/search/list_bukken/",
                data={"tdfk": tdfk, "area": area, "mode": "init",
                      "pageIndex": page, "rent_low": "0", "rent_high": "9999999"},
                timeout=config.HTTP_TIMEOUT,
            )
            data = _json.loads(r.content.decode("utf-8-sig"))
        except Exception:
            break
        if not isinstance(data, list) or not data:
            break
        new = [d for d in data if d.get("id") not in seen]
        for d in new:
            seen.add(d["id"])
        out.extend(new)
        if not new:  # esta página no añade nada nuevo -> fin
            break
    return out


def fetch(client):
    results = []
    seen = set()
    for tdfk, pref in UR_PREFS.items():
        for area in _areas(tdfk):
            for d in _list_area(tdfk, area):
                did = d.get("id")
                if not did or did in seen:
                    continue
                seen.add(did)
                name = d.get("name", "")
                city = d.get("skcs", "")
                access = BeautifulSoup(d.get("access", ""), "lxml").get_text(" / ", strip=True)
                url = WWW + (d.get("bukkenUrl") or "")
                img = d.get("image") or ""
                lst = Listing(
                    source=SLUG, source_name=NAME, source_url=url,
                    listing_type="rent", prop_type="apartment",
                    title=f"{name}（{city}）" if city else name,
                    prefecture=pref, city=city,
                    address_raw=f"{pref}{city}{name}",
                    rent_yen=_rent_low(d.get("rent", "")),
                    layout="", structure="",
                    parking="unknown",
                    foreigner_ok="yes",  # UR admite extranjeros
                    photos=[img] if img.startswith("http") else [],
                    description_raw=f"UR賃貸 · {d.get('rent','')} {d.get('commonfee','')}",
                    status_note="",
                    features={
                        "交通": access,
                        "contacto": "UR都市機構 (vivienda pública)",
                        "条件": "Admite extranjeros · sin 礼金 (key money) · sin avalista · sin comisión de agencia",
                        "renta_rango": d.get("rent", ""),
                        "共益費": d.get("commonfee", ""),
                    },
                )
                assign_area(lst)
                results.append(lst)
    return results
