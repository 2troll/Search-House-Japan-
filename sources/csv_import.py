# -*- coding: utf-8 -*-
"""
Adaptador: importación manual por CSV.

Para los portales comerciales (SUUMO, HOME'S 賃貸, アットホーム, こだて賃貸…)
cuyos términos suelen PROHIBIR el scraping automático, NO raspamos: en su lugar
tú pegas/exportas los anuncios a un CSV y esta fuente los mezcla con el resto.

>>> CÓMO USARLO <<<
  1. Copia web/sample_import.csv a  imports/mis_casas.csv  (o edita el de ejemplo).
  2. Rellena una fila por casa. Solo 'source_url' y 'listing_type' son obligatorios.
  3. Ejecuta refresh.py: todas las filas se cargan y geocodifican como las demás.

Coloca tus CSV en la carpeta  imports/  (se leen todos los *.csv de ahí).
"""

import csv
import glob
import os

import config
from sources.base import (
    Listing, parse_price_yen, parse_area_m2, parse_parking,
    detect_foreigner_ok, parse_year_built, assign_area,
)

SLUG = "csv"
NAME = "Importación manual (CSV)"
IMPORTS_DIR = os.path.join(config.BASE_DIR, "imports")

# Columnas reconocidas del CSV (todas opcionales salvo source_url y listing_type).
# Acepta cabeceras en español o en el nombre del campo de la BD.
FIELD_ALIASES = {
    "url": "source_url", "enlace": "source_url", "source_url": "source_url",
    "tipo": "listing_type", "operacion": "listing_type", "listing_type": "listing_type",
    "titulo": "title", "title": "title",
    "direccion": "address_raw", "address": "address_raw", "address_raw": "address_raw",
    "municipio": "city", "city": "city",
    "alquiler": "rent_yen", "rent": "rent_yen", "rent_yen": "rent_yen",
    "precio_venta": "sale_price_yen", "sale_price": "sale_price_yen", "sale_price_yen": "sale_price_yen",
    "distribucion": "layout", "layout": "layout",
    "m2_edificio": "building_area_m2", "building_area_m2": "building_area_m2",
    "m2_terreno": "land_area_m2", "land_area_m2": "land_area_m2",
    "anio": "year_built", "year_built": "year_built",
    "estructura": "structure", "structure": "structure",
    "parking": "parking", "estacionamiento": "parking",
    "extranjero": "foreigner_ok", "foreigner_ok": "foreigner_ok",
    "reformada": "renovated", "renovated": "renovated",
    "fotos": "photos", "photos": "photos",
    "descripcion": "description_raw", "description": "description_raw",
}


def _normalize_row(row):
    data = {}
    for k, v in row.items():
        if k is None:
            continue
        key = FIELD_ALIASES.get(k.strip().lower())
        if key and v is not None and str(v).strip() != "":
            data[key] = str(v).strip()
    return data


def _row_to_listing(data):
    url = data.get("source_url")
    if not url:
        return None
    ltype = (data.get("listing_type") or "sale").lower()
    if ltype in ("alquiler", "rent", "賃貸"):
        ltype = "rent"
    elif ltype in ("venta", "sale", "売買"):
        ltype = "sale"

    rent = parse_price_yen(data.get("rent_yen", "")) if ltype == "rent" else None
    sale = parse_price_yen(data.get("sale_price_yen", "")) if ltype == "sale" else None
    year_raw, age = parse_year_built(data.get("year_built", ""))
    parking, pdetail = parse_parking(data.get("parking", ""))

    foreigner = data.get("foreigner_ok", "")
    if foreigner.lower() in ("si", "sí", "yes", "可"):
        foreigner = "yes"
    elif foreigner.lower() in ("no", "不可"):
        foreigner = "no"
    elif foreigner:
        foreigner = "negotiable"
    else:
        foreigner = detect_foreigner_ok(data.get("description_raw", ""))

    photos = [p.strip() for p in data.get("photos", "").split("|") if p.strip()]

    lst = Listing(
        source=SLUG, source_name=NAME, source_url=url,
        listing_type=ltype,
        title=data.get("title", data.get("address_raw", "Casa importada")),
        city=data.get("city", ""),
        address_raw=data.get("address_raw", data.get("city", "")),
        rent_yen=rent, sale_price_yen=sale,
        layout=data.get("layout", ""),
        building_area_m2=parse_area_m2(data.get("building_area_m2", "")),
        land_area_m2=parse_area_m2(data.get("land_area_m2", "")),
        year_built=year_raw, age_years=age,
        structure=data.get("structure", ""),
        parking=parking, parking_detail=pdetail,
        foreigner_ok=foreigner,
        renovated=1 if str(data.get("renovated", "")).lower() in ("1", "si", "sí", "yes", "true") else 0,
        photos=photos,
        description_raw=data.get("description_raw", ""),
    )
    assign_area(lst)
    return lst


def fetch(client):
    """Lee todos los imports/*.csv. (client no se usa: no hay red.)"""
    results = []
    if not os.path.isdir(IMPORTS_DIR):
        return results
    for path in sorted(glob.glob(os.path.join(IMPORTS_DIR, "*.csv"))):
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    lst = _row_to_listing(_normalize_row(row))
                    if lst:
                        results.append(lst)
        except Exception as e:
            print(f"  [csv] error leyendo {path}: {e}")
    return results
