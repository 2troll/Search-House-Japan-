#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh.py — re-extrae todas las fuentes, geocodifica, deduplica y exporta.

Uso:
    python3 refresh.py                # todas las fuentes ENABLED + CSV
    python3 refresh.py suminiko       # solo una/varias fuentes concretas
    python3 refresh.py --all          # incluye también las OPTIONAL_SOURCES
    python3 refresh.py --no-geocode   # salta la geocodificación (más rápido)

Pasos:
  1. init_db() crea las tablas si no existen.
  2. Para cada fuente: fetch(client) -> list[Listing].
  3. Geocodifica cada anuncio (con caché).
  4. upsert por source_url (deduplicación; actualiza last_seen, marca novedades).
  5. Marca active=0 los anuncios de esa fuente que ya no aparecen.
  6. Exporta web/data.geojson para el mapa.
"""

import sys

import db
import geocode
from sources.base import HttpClient
from sources.registry import ENABLED_SOURCES, ALL_SOURCES


def run(selected=None, use_all=False, do_geocode=True):
    db.init_db()
    client = HttpClient()

    sources = ALL_SOURCES if use_all else ENABLED_SOURCES
    if selected:
        sources = {k: v for k, v in ALL_SOURCES.items() if k in selected}
        if not sources:
            print(f"Ninguna fuente coincide con {selected}. Disponibles: {list(ALL_SOURCES)}")
            return

    conn = db.get_conn()
    totals = {"new": 0, "updated": 0, "total": 0}

    for slug, module in sources.items():
        print(f"\n=== Fuente: {slug} ({getattr(module, 'NAME', slug)}) ===")
        try:
            listings = module.fetch(client)
        except Exception as e:
            print(f"  ERROR al extraer {slug}: {e}")
            continue

        print(f"  {len(listings)} anuncios obtenidos. Geocodificando y guardando...")
        seen_urls = []
        for lst in listings:
            data = lst.as_dict()
            if do_geocode:
                geocode.geocode_listing(conn, data)
            status = db.upsert_listing(conn, data)
            totals[status] += 1
            totals["total"] += 1
            seen_urls.append(data["source_url"])

        # Marca como inactivos los que ya no aparecen en esta fuente.
        db.mark_inactive(conn, slug, seen_urls)
        conn.commit()
        print(f"  Guardados: {len(seen_urls)} (nuevos+actualizados).")

    conn.close()

    count = db.export_geojson()
    print(f"\nResumen: {totals['new']} nuevos, {totals['updated']} actualizados, "
          f"{totals['total']} procesados.")
    print(f"Exportadas {count} casas con coordenadas a web/data.geojson")
    print("Abre el mapa con:  python3 -m http.server 8000  ->  http://localhost:8000/web/")


def main():
    args = sys.argv[1:]
    use_all = "--all" in args
    do_geocode = "--no-geocode" not in args
    selected = [a for a in args if not a.startswith("--")]
    run(selected=selected or None, use_all=use_all, do_geocode=do_geocode)


if __name__ == "__main__":
    main()
