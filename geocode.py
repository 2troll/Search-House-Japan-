# -*- coding: utf-8 -*-
"""
Geocodificación de direcciones japonesas -> (lat, lng).

Estrategia:
  1. API gratuita del Geospatial Information Authority of Japan (GSI / 国土地理院).
     Sin API key. https://msearch.gsi.go.jp/address-search/AddressSearch?q=...
  2. Fallback: Nominatim (OpenStreetMap), máx. 1 petición/segundo, UA propio.
  3. Si nada funciona, se usa el centro del municipio (TARGET_AREAS) y se marca
     la casa como "sin ubicación exacta" (geocode_exact = 0).

Todo se cachea en la tabla geocode_cache para no repetir peticiones.
"""

import time

import requests

import config
import db

GSI_URL = "https://msearch.gsi.go.jp/address-search/AddressSearch"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

_session = requests.Session()
_session.headers.update({"User-Agent": config.USER_AGENT})
_last_nominatim = [0.0]  # rate limit Nominatim (1 req/s)


def _cache_get(conn, address):
    row = conn.execute(
        "SELECT lat, lng, source FROM geocode_cache WHERE address_raw = ?", (address,)
    ).fetchone()
    if row and row["lat"] is not None:
        return row["lat"], row["lng"], row["source"]
    return None


def _cache_put(conn, address, lat, lng, source):
    conn.execute(
        "INSERT OR REPLACE INTO geocode_cache (address_raw, lat, lng, source) VALUES (?, ?, ?, ?)",
        (address, lat, lng, source),
    )
    conn.commit()


def _geocode_gsi(address):
    try:
        r = _session.get(GSI_URL, params={"q": address}, timeout=config.HTTP_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if data:
                lng, lat = data[0]["geometry"]["coordinates"]
                return lat, lng
    except Exception:
        pass
    return None


def _geocode_nominatim(address):
    # rate limit: 1 petición por segundo
    wait = 1.0 - (time.time() - _last_nominatim[0])
    if wait > 0:
        time.sleep(wait)
    _last_nominatim[0] = time.time()
    try:
        r = _session.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "jp"},
            timeout=config.HTTP_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def geocode(conn, address, fallback_area_key=None):
    """Devuelve (lat, lng, source, exact).

    `fallback_area_key` es la key de TARGET_AREAS usada para centrar la casa en
    el municipio si la geocodificación exacta falla.
    """
    address = (address or "").strip()
    if address:
        cached = _cache_get(conn, address)
        if cached:
            lat, lng, source = cached
            return lat, lng, source, 1

        result = _geocode_gsi(address)
        source = "gsi"
        if result is None:
            result = _geocode_nominatim(address)
            source = "nominatim"

        if result is not None:
            lat, lng = result
            _cache_put(conn, address, lat, lng, source)
            return lat, lng, source, 1

    # Fallback: centro del municipio.
    if fallback_area_key:
        area = next((a for a in config.TARGET_AREAS if a["key"] == fallback_area_key), None)
        if area:
            lat, lng = area["center"]
            return lat, lng, "city", 0

    return None, None, "", 0


def geocode_listing(conn, listing_dict):
    """Rellena lat/lng/geocode_source/geocode_exact en un dict de anuncio."""
    lat, lng, source, exact = geocode(
        conn,
        listing_dict.get("address_raw", ""),
        listing_dict.get("area_key"),
    )
    listing_dict["lat"] = lat
    listing_dict["lng"] = lng
    listing_dict["geocode_source"] = source
    listing_dict["geocode_exact"] = exact
    return listing_dict
