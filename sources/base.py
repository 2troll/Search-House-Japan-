# -*- coding: utf-8 -*-
"""
Infraestructura común para todos los adaptadores de fuentes.

Contiene:
  - HttpClient: cliente HTTP "educado" (respeta robots.txt, limita velocidad,
    cachea en disco, User-Agent descriptivo, reintentos suaves).
  - Listing: dataclass con el ESQUEMA NORMALIZADO. Cada adaptador devuelve
    una lista de Listing.
  - Helpers para parsear texto japonés (precios, áreas, parking, etc.).
  - SOURCES: registro de adaptadores activos (lo lee refresh.py).

>>> CÓMO AÑADIR UNA FUENTE NUEVA <<<
  1. Crea sources/mi_fuente.py con una función  fetch(client) -> list[Listing].
  2. Impórtala abajo y añádela al diccionario SOURCES.
  ¡Eso es todo! refresh.py la recorrerá automáticamente.
"""

import hashlib
import os
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field, asdict
from datetime import date
from urllib.parse import urlparse

import requests

import config


# ==========================================================================
#  ESQUEMA NORMALIZADO
# ==========================================================================
@dataclass
class Listing:
    source: str
    source_name: str
    source_url: str
    listing_type: str = "sale"      # "rent" | "sale"
    title: str = ""

    prefecture: str = ""
    city: str = ""
    area_key: str = ""
    address_raw: str = ""
    lat: float = None
    lng: float = None
    geocode_source: str = ""
    geocode_exact: int = 1

    rent_yen: int = None
    management_fee_yen: int = None
    deposit: str = ""
    key_money: str = ""
    sale_price_yen: int = None

    layout: str = ""
    building_area_m2: float = None
    land_area_m2: float = None
    year_built: str = ""
    age_years: int = None
    structure: str = ""
    floors: str = ""

    parking: str = "unknown"        # yes | nearby | no | unknown
    parking_detail: str = ""
    foreigner_ok: str = "unknown"   # yes | negotiable | no | unknown
    pet_ok: str = "unknown"
    renovated: int = 0

    photos: list = field(default_factory=list)
    description_raw: str = ""
    features: dict = field(default_factory=dict)
    status_note: str = ""
    raw: str = ""

    def as_dict(self):
        return asdict(self)


# ==========================================================================
#  CLIENTE HTTP EDUCADO (rate limit + robots.txt + caché en disco)
# ==========================================================================
class HttpClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self._last_request = {}          # dominio -> timestamp de la última petición
        self._robots = {}                # dominio -> RobotFileParser
        os.makedirs(config.CACHE_DIR, exist_ok=True)

    # ----- robots.txt --------------------------------------------------
    def _robots_allows(self, url):
        if not config.RESPECT_ROBOTS:
            return True
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(domain + "/robots.txt")
            try:
                rp.read()
            except Exception:
                # Si no hay robots.txt accesible, no bloqueamos (lo trataremos como permitido).
                rp = None
            self._robots[domain] = rp
        rp = self._robots[domain]
        if rp is None:
            return True
        try:
            return rp.can_fetch(config.USER_AGENT, url)
        except Exception:
            return True

    # ----- rate limit --------------------------------------------------
    def _throttle(self, url):
        domain = urlparse(url).netloc
        last = self._last_request.get(domain)
        if last is not None:
            wait = config.REQUEST_DELAY_SECONDS - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_request[domain] = time.time()

    # ----- caché en disco ----------------------------------------------
    def _cache_path(self, url):
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(config.CACHE_DIR, h + ".html")

    def _cache_get(self, url):
        p = self._cache_path(url)
        if os.path.exists(p):
            age = time.time() - os.path.getmtime(p)
            if age < config.CACHE_TTL_SECONDS:
                with open(p, encoding="utf-8") as f:
                    return f.read()
        return None

    def _cache_put(self, url, text):
        with open(self._cache_path(url), "w", encoding="utf-8") as f:
            f.write(text)

    # ----- petición principal ------------------------------------------
    def get(self, url, use_cache=True):
        """GET con caché, rate limit, robots y reintentos. Devuelve texto o None."""
        if use_cache:
            cached = self._cache_get(url)
            if cached is not None:
                return cached

        if not self._robots_allows(url):
            print(f"  [robots] BLOQUEADO por robots.txt, se omite: {url}")
            return None

        last_err = None
        for attempt in range(config.MAX_RETRIES):
            self._throttle(url)
            try:
                resp = self.session.get(url, timeout=config.HTTP_TIMEOUT)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or resp.encoding
                    text = resp.text
                    self._cache_put(url, text)
                    return text
                elif resp.status_code in (404, 410):
                    return None
                else:
                    last_err = f"HTTP {resp.status_code}"
            except requests.RequestException as e:
                last_err = str(e)
            # backoff exponencial suave
            time.sleep(config.RETRY_BACKOFF_SECONDS * (2 ** attempt))
        print(f"  [http] fallo tras {config.MAX_RETRIES} intentos ({last_err}): {url}")
        return None


# ==========================================================================
#  HELPERS DE PARSEO (texto japonés -> valores normalizados)
# ==========================================================================
_NUM = re.compile(r"[\d,\.]+")


def _clean_num(s):
    """Extrae el primer número de un texto (tolera espacios dentro: '401. 38')."""
    if not s:
        return None
    s = s.replace(" ", "").replace("　", "").replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_price_yen(text):
    """Convierte un texto de precio japonés a yenes (int).

    Soporta '950万円', '9,500,000円', '3.5万円', '35,000円/月'.
    Devuelve None si no encuentra número.
    """
    if not text:
        return None
    t = text.replace(",", "").replace("　", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", t)
    if m:
        return int(round(float(m.group(1)) * 10000))
    m = re.search(r"(\d+(?:\.\d+)?)\s*円", t)
    if m:
        return int(round(float(m.group(1))))
    n = _clean_num(t)
    return int(round(n)) if n is not None else None


def parse_area_m2(text):
    """Extrae metros cuadrados de '401. 38 ㎡（121坪）' -> 401.38."""
    if not text:
        return None
    # nos quedamos con la parte antes de '㎡' o 'm' si existe
    t = text.split("㎡")[0].split("m")[0]
    return _clean_num(t)


def parse_parking(text):
    """Clasifica el campo 車庫/駐車場 -> yes | nearby | no | unknown."""
    if not text:
        return "unknown", ""
    t = text.strip()
    if any(k in t for k in ("近隣", "近く", "周辺", "徒歩")):
        return "nearby", t
    if any(k in t for k in ("なし", "無", "不可", "×")):
        return "no", t
    if any(k in t for k in ("あり", "有", "可", "台")):
        return "yes", t
    return "unknown", t


def detect_foreigner_ok(text):
    """Busca menciones a extranjeros. Si no hay nada -> 'unknown' (NO descartar)."""
    if not text:
        return "unknown"
    if any(k in text for k in ("外国人歓迎", "外国人可", "外国人相談可", "外国籍可")):
        return "yes"
    if any(k in text for k in ("外国人相談", "外国人応相談")):
        return "negotiable"
    if any(k in text for k in ("外国人不可", "外国籍不可")):
        return "no"
    return "unknown"


def detect_renovated(text):
    """1 si el texto menciona reforma/renovación, 0 si no."""
    if not text:
        return 0
    return 1 if any(k in text for k in ("リフォーム", "リノベ", "改装済", "改修済")) else 0


def detect_pet(text):
    if not text:
        return "unknown"
    if any(k in text for k in ("ペット可", "ペット相談")):
        return "yes"
    if "ペット不可" in text:
        return "no"
    return "unknown"


# Mapea eras japonesas a año occidental de inicio (para calcular 築年).
_ERA = {"R": 2018, "令和": 2018, "H": 1988, "平成": 1988, "S": 1925, "昭和": 1925}


def parse_year_built(text):
    """Devuelve (texto_crudo, age_years). Soporta '平成18年', 'H18', '1995年', '築20年'."""
    if not text:
        return "", None
    raw = text.strip()
    this_year = date.today().year

    # 築NN年 (antigüedad directa)
    m = re.search(r"築\s*(\d+)\s*年", raw)
    if m:
        return raw, int(m.group(1))

    # Año occidental: 1995年 / 1995
    m = re.search(r"(19|20)\d{2}", raw)
    if m:
        y = int(m.group())
        return raw, max(0, this_year - y)

    # Era japonesa: 平成18 / H18 / R3 / 令和3
    m = re.search(r"(令和|平成|昭和|[RHS])\s*(\d+)", raw)
    if m:
        era, n = m.group(1), int(m.group(2))
        base = _ERA.get(era)
        if base:
            y = base + n  # nota: el año 1 de cada era empieza en `base+1`
            return raw, max(0, this_year - y)

    return raw, None


def assign_area(listing):
    """Rellena area_key/city/prefecture/center según la dirección o el título.

    Si no se puede ubicar el municipio exacto, deja area_key vacío.
    Devuelve el bloque de zona (o None).
    """
    text = " ".join(filter(None, [listing.address_raw, listing.title, listing.city]))
    area = config.match_area(text)
    if area:
        listing.area_key = area["key"]
        listing.city = listing.city or area["ja"]
        listing.prefecture = listing.prefecture or area["pref"]
    return area
