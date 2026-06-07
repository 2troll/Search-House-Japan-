# -*- coding: utf-8 -*-
"""
Helpers de la base de datos SQLite.

- init_db():       crea las tablas a partir de schema.sql.
- get_conn():      abre una conexión.
- upsert_listing():inserta o actualiza un anuncio por source_url (deduplicación).
- mark_inactive(): marca como inactivas las casas que ya no aparecen.
- export_geojson():vuelca las casas activas a web/data.geojson para el mapa.
"""

import json
import os
import sqlite3
from datetime import datetime, date

import config

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Columnas que acepta upsert_listing (deben existir en la tabla listings).
LISTING_COLUMNS = [
    "source", "source_name", "source_url", "scraped_at", "first_seen", "last_seen",
    "active", "listing_type", "prop_type", "title", "prefecture", "city", "area_key", "address_raw",
    "lat", "lng", "geocode_source", "geocode_exact", "rent_yen", "management_fee_yen",
    "deposit", "key_money", "sale_price_yen", "layout", "building_area_m2", "land_area_m2",
    "year_built", "age_years", "structure", "floors", "parking", "parking_detail",
    "foreigner_ok", "pet_ok", "renovated", "photos", "description_raw", "features",
    "status_note", "raw",
]


def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()
    conn = get_conn()
    conn.executescript(schema)
    conn.commit()
    conn.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def upsert_listing(conn, data):
    """Inserta o actualiza un anuncio usando source_url como clave única.

    `data` es un dict con cualquier subconjunto de LISTING_COLUMNS.
    Devuelve "new" si la fila es nueva, "updated" si ya existía.
    """
    url = data.get("source_url")
    if not url:
        raise ValueError("upsert_listing requiere source_url")

    now = _now()
    cur = conn.execute("SELECT id, first_seen FROM listings WHERE source_url = ?", (url,))
    row = cur.fetchone()

    # Solo conservamos claves válidas.
    payload = {k: v for k, v in data.items() if k in LISTING_COLUMNS}
    payload["scraped_at"] = now
    payload["last_seen"] = now
    payload["active"] = 1

    # Listas/dicts -> JSON.
    for jf in ("photos", "features"):
        if isinstance(payload.get(jf), (list, dict)):
            payload[jf] = json.dumps(payload[jf], ensure_ascii=False)

    if row is None:
        payload["first_seen"] = now
        cols = list(payload.keys())
        placeholders = ", ".join("?" for _ in cols)
        conn.execute(
            f"INSERT INTO listings ({', '.join(cols)}) VALUES ({placeholders})",
            [payload[c] for c in cols],
        )
        return "new"
    else:
        # No tocamos first_seen al actualizar.
        payload.pop("first_seen", None)
        cols = list(payload.keys())
        assignments = ", ".join(f"{c} = ?" for c in cols)
        conn.execute(
            f"UPDATE listings SET {assignments} WHERE source_url = ?",
            [payload[c] for c in cols] + [url],
        )
        return "updated"


def mark_inactive(conn, source, seen_urls):
    """Marca active=0 las casas de `source` cuya url no se haya visto en este refresh."""
    if seen_urls:
        placeholders = ", ".join("?" for _ in seen_urls)
        conn.execute(
            f"UPDATE listings SET active = 0 WHERE source = ? AND source_url NOT IN ({placeholders})",
            [source] + list(seen_urls),
        )
    else:
        conn.execute("UPDATE listings SET active = 0 WHERE source = ?", (source,))


def _is_new(first_seen, days=14):
    """True si first_seen es de los últimos `days` días (para el filtro 'novedades')."""
    if not first_seen:
        return False
    try:
        d = datetime.fromisoformat(first_seen).date()
    except ValueError:
        return False
    return (date.today() - d).days <= days


def export_geojson(path=None):
    """Vuelca las casas activas con coordenadas a un FeatureCollection GeoJSON."""
    path = path or config.GEOJSON_OUT
    conn = get_conn()
    rows = conn.execute("SELECT * FROM listings WHERE active = 1").fetchall()
    conn.close()

    features = []
    for r in rows:
        r = dict(r)
        if r.get("lat") is None or r.get("lng") is None:
            continue  # sin coordenadas no se puede pintar en el mapa
        photos = json.loads(r["photos"]) if r.get("photos") else []
        try:
            features = json.loads(r["features"]) if r.get("features") else {}
        except (ValueError, TypeError):
            features = {}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
            "properties": {
                "id": r["id"],
                "source": r["source"],
                "source_name": r["source_name"],
                "source_url": r["source_url"],
                "listing_type": r["listing_type"],
                "prop_type": r["prop_type"],
                "title": r["title"],
                "prefecture": r["prefecture"],
                "city": r["city"],
                "area_key": r["area_key"],
                "address_raw": r["address_raw"],
                "geocode_exact": r["geocode_exact"],
                "rent_yen": r["rent_yen"],
                "management_fee_yen": r["management_fee_yen"],
                "deposit": r["deposit"],
                "key_money": r["key_money"],
                "sale_price_yen": r["sale_price_yen"],
                "layout": r["layout"],
                "building_area_m2": r["building_area_m2"],
                "land_area_m2": r["land_area_m2"],
                "year_built": r["year_built"],
                "age_years": r["age_years"],
                "structure": r["structure"],
                "floors": r["floors"],
                "parking": r["parking"],
                "parking_detail": r["parking_detail"],
                "foreigner_ok": r["foreigner_ok"],
                "pet_ok": r["pet_ok"],
                "renovated": r["renovated"],
                "photos": photos,
                "features": features,
                "description_raw": r["description_raw"],
                "status_note": r["status_note"],
                "is_new": _is_new(r["first_seen"]),
                "first_seen": r["first_seen"],
            },
        })

    fc = {"type": "FeatureCollection", "features": features}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)
    return len(features)
