# -*- coding: utf-8 -*-
"""
Adaptador: GaijinPot Apartments / Real Estate Japan (USO PERSONAL).

Es LA plataforma de alquiler en INGLÉS pensada para extranjeros (misma empresa
sirve apartments.gaijinpot.com y realestate.co.jp). Muchas inmobiliarias listan
aquí pisos "foreigner friendly" (sin 礼金, sin avalista, sin comisión), con
CONTACTO directo del agente, dirección, fotos y plano.

Pensado para ayudarte a TI a encontrar vivienda (no para redistribuir). Lee las
páginas públicas en inglés que tú mismo puedes ver, con pausas educadas. Las
fotos se sirven desde su CDN (no se descargan, no ocupan espacio).

Datos limpios desde el JSON-LD (schema.org) de cada ficha:
  Product.offers.price, Residence.address + accommodationFloorPlan.layoutImage,
  RealEstateAgent.name/description, TrainStation.name, y la tabla de specs.
"""

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from sources.base import Listing

SLUG = "gaijinpot"
NAME = "GaijinPot / Real Estate Japan (inglés · extranjeros)"
BASE = "https://apartments.gaijinpot.com"

# Prefecturas de Kansai -> (nombre japonés, area_key de config.TARGET_AREAS)
PREFS = {
    "osaka": ("大阪府", "osaka_rural"),
    "kyoto": ("京都府", "kyoto_north"),
    "hyogo": ("兵庫県", "hyogo"),
    "nara": ("奈良県", "nara"),
    "shiga": ("滋賀県", "shiga"),
    "wakayama": ("和歌山県", "wakayama_shi"),
}
MAX_PAGES = 4        # páginas de listado por prefectura (~15 fichas/página)
WORKERS = 6
RPS = 3.0            # tope global de peticiones/seg (educado)

_local = threading.local()
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def _session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"})
        _local.s = s
    return s


class _Rate:
    def __init__(self, rps):
        self.interval = 1.0 / rps
        self.lock = threading.Lock()
        self.next = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next)
            self.next = t + self.interval
            d = t - now
        if d > 0:
            time.sleep(d)


def _get(url, rate):
    for _ in range(2):
        rate.wait()
        try:
            r = _session().get(url, timeout=15)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
        except requests.RequestException:
            pass
    return None


def _fullsize(u):
    """Quita la variante de tamaño: .../9-cco707/_w300_h300_x.jpeg -> .../9-cco707.jpeg"""
    return re.sub(r"/_w\d+_h\d+[^/]*\.(jpe?g|png)$", r".\1", u, flags=re.I)


def _ld_blocks(soup):
    out = {}
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string)
        except Exception:
            continue
        for blk in (data if isinstance(data, list) else [data]):
            t = blk.get("@type")
            if t:
                out.setdefault(t, blk)
    return out


def _specs(soup):
    out = {}
    for dl in soup.select("dl, table"):
        ks = dl.find_all(["dt", "th"])
        vs = dl.find_all(["dd", "td"])
        for a, b in zip(ks, vs):
            k = a.get_text(strip=True)
            v = b.get_text(" ", strip=True)
            if k and v and k not in out:
                out[k] = v
    return out


def _parse_detail(did, html, pref_ja, area_key):
    soup = BeautifulSoup(html, "lxml")
    ld = _ld_blocks(soup)
    sp = _specs(soup)
    url = f"{BASE}/en/rent/view/{did}"

    # precio
    rent = None
    prod = ld.get("Product", {})
    offers = prod.get("offers", {}) if isinstance(prod, dict) else {}
    if isinstance(offers, dict) and offers.get("price"):
        try:
            rent = int(float(offers["price"]))
        except (TypeError, ValueError):
            rent = None

    # dirección (inglés) y barrio
    res = ld.get("Residence", {})
    addr = res.get("address", {}) if isinstance(res, dict) else {}
    locality = addr.get("addressLocality", "")
    region = addr.get("addressRegion", "")
    location = sp.get("Location") or " ".join(filter(None, [locality, region]))

    # tipo / layout / m² / planta / edificio
    h1 = soup.find("h1")
    h1t = h1.get_text(" ", strip=True) if h1 else ""
    mlay = re.search(r"(\d*\s*[SLDKR]{1,4})\s*(Apartment|Mansion|House|Studio)", h1t)
    layout = (mlay.group(1).replace(" ", "") if mlay else "")
    ptype = "house" if re.search(r"House|Detached", sp.get("Type", "") + h1t, re.I) else "apartment"
    size = None
    msz = re.search(r"([\d.]+)\s*m", sp.get("Size", ""))
    if msz:
        size = float(msz.group(1))
    building = sp.get("Building Name", "")

    # estación
    station = ""
    st = ld.get("TrainStation", {})
    if isinstance(st, dict) and st.get("name"):
        station = st["name"] + " Station"

    # agente / contacto
    agent = ld.get("RealEstateAgent", {})
    agent_name = agent.get("name", "") if isinstance(agent, dict) else ""
    agent_desc = (agent.get("description", "") or "")[:400] if isinstance(agent, dict) else ""

    # fotos: plano primero + fotos del CDN, a tamaño completo y sin duplicados
    photos, seen = [], set()
    fp = res.get("accommodationFloorPlan", {}) if isinstance(res, dict) else {}
    if isinstance(fp, dict) and fp.get("layoutImage"):
        f = _fullsize(fp["layoutImage"])
        photos.append(f)
        seen.add(f)
    for m in re.findall(r"https://media\.realestate\.co\.jp/img/store/[^\s\"']+?\.(?:jpe?g|png)", html, re.I):
        f = _fullsize(m)
        if f not in seen:
            seen.add(f)
            photos.append(f)
    photos = photos[:14]

    title = building or (f"{layout} en {locality}".strip() if layout else locality) or "Rental"
    return Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type="rent", prop_type=ptype,
        title=title, prefecture=pref_ja, city=locality, area_key=area_key,
        address_raw=location,
        rent_yen=rent, layout=layout, building_area_m2=size,
        floors=sp.get("Floor", ""),
        foreigner_ok="yes",   # plataforma para extranjeros
        photos=photos,
        description_raw=f"GaijinPot/RealEstateJapan · {h1t}",
        features={
            "交通": station,
            "contacto": agent_name or "Ver agente en el anuncio (inglés)",
            "contacto_web": url,
            "条件": agent_desc,
        },
    )


def fetch(client):
    rate = _Rate(RPS)
    # 1) recoge ids de las páginas de listado por prefectura
    pairs = []          # (id, pref_ja, area_key)
    seen_ids = set()
    for slug, (pref_ja, area_key) in PREFS.items():
        for page in range(1, MAX_PAGES + 1):
            html = _get(f"{BASE}/en/rent/{slug}?page={page}", rate)
            if not html:
                break
            ids = re.findall(r"/en/rent/view/(\d+)", html)
            new = [i for i in dict.fromkeys(ids) if i not in seen_ids]
            if not new:
                break
            for i in new:
                seen_ids.add(i)
                pairs.append((i, pref_ja, area_key))

    print(f"  [gaijinpot] {len(pairs)} fichas a leer...", flush=True)

    # 2) lee cada ficha en paralelo (con tope de velocidad)
    results = []

    def work(did, pref_ja, area_key):
        html = _get(f"{BASE}/en/rent/view/{did}", rate)
        if not html:
            return None
        try:
            return _parse_detail(did, html, pref_ja, area_key)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(work, *p) for p in pairs]
        for fut in as_completed(futs):
            lst = fut.result()
            if lst and lst.rent_yen:
                results.append(lst)
    print(f"  [gaijinpot] {len(results)} alquileres válidos.", flush=True)
    return results
