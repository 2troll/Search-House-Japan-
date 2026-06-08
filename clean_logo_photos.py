# -*- coding: utf-8 -*-
"""
Limpia fotos que NO son de la casa en los anuncios de at-home.

Los bancos de casas municipales (p. ej. 南あわじ市) cuelgan en sus fichas el
LOGO del ayuntamiento o BANNERS de publicidad (ふるさと納税, sitios de turismo...).
Al descargarlos quedaron como "fotos" del anuncio.

Detección sin adivinar: una foto REAL de una casa es única. Si un mismo archivo
(mismos bytes) aparece en >= MIN_DUP anuncios distintos, es un logo/banner/plantilla.
Quitamos esas referencias de los anuncios y borramos los archivos repetidos.

Uso:  python clean_logo_photos.py            # limpia y re-exporta geojson
      python clean_logo_photos.py --dry      # solo informa, no toca nada
"""

import argparse
import glob
import hashlib
import json
import os
from collections import defaultdict

import config
import db

IMG_DIR = os.path.join(config.BASE_DIR, "web", "img", "athome")
MIN_DUP = 3  # mismo archivo en >=3 anuncios => no es una casa


def junk_basenames():
    """Devuelve el conjunto de nombres de archivo que son logos/banners."""
    by_hash = defaultdict(list)
    for f in glob.glob(os.path.join(IMG_DIR, "*.webp")):
        try:
            by_hash[hashlib.md5(open(f, "rb").read()).hexdigest()].append(os.path.basename(f))
        except OSError:
            pass
    junk = set()
    for h, files in by_hash.items():
        if len(files) >= MIN_DUP:
            junk.update(files)
    return junk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="solo informar")
    args = ap.parse_args()

    junk = junk_basenames()
    print(f"Archivos basura (logos/banners repetidos): {len(junk)}", flush=True)

    conn = db.get_conn()
    rows = conn.execute(
        "SELECT id, photos FROM listings WHERE source='athome' AND active=1 AND photos IS NOT NULL"
    ).fetchall()

    changed = removed_refs = emptied = 0
    updates = []
    for r in rows:
        try:
            ph = json.loads(r["photos"])
        except Exception:
            continue
        clean = [p for p in ph if os.path.basename(p) not in junk]
        if len(clean) != len(ph):
            removed_refs += len(ph) - len(clean)
            changed += 1
            if not clean:
                emptied += 1
            updates.append((json.dumps(clean, ensure_ascii=False), r["id"]))

    print(f"Anuncios afectados: {changed} | referencias quitadas: {removed_refs} "
          f"| se quedan sin foto: {emptied}", flush=True)

    if args.dry:
        conn.close()
        return

    conn.executemany("UPDATE listings SET photos=? WHERE id=?", updates)
    conn.commit()
    conn.close()

    # borra los archivos basura del disco (web/ y docs/) para liberar espacio
    deleted = 0
    for base in junk:
        for d in ("web/img/athome", "docs/img/athome"):
            p = os.path.join(config.BASE_DIR, d, base)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    deleted += 1
                except OSError:
                    pass
    print(f"Archivos borrados del disco: {deleted}", flush=True)

    n = db.export_geojson()
    print(f"GeoJSON re-exportado: {n} propiedades.", flush=True)


if __name__ == "__main__":
    main()
