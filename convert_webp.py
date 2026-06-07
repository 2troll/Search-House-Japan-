#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convierte todas las fotos descargadas (.jpg) a WebP (ligero, misma resolución)
y actualiza las referencias en la base de datos. Resuelve el límite de espacio."""
import glob
import io
import json
import os

from PIL import Image

import db

Q, MAXDIM = 82, 1280
DIRS = ["web/img/athome", "docs/img/athome"]


def convert_dir(d):
    if not os.path.isdir(d):
        return 0, 0, 0
    jpgs = glob.glob(os.path.join(d, "*.jpg"))
    before = after = 0
    for j in jpgs:
        w = j[:-4] + ".webp"
        try:
            before += os.path.getsize(j)
            if not (os.path.exists(w) and os.path.getsize(w) > 500):
                im = Image.open(j).convert("RGB")
                im.thumbnail((MAXDIM, MAXDIM))
                im.save(w, "WEBP", quality=Q, method=4)
            after += os.path.getsize(w)
            os.remove(j)
        except Exception as e:
            print("  err", j, e)
    return len(jpgs), before, after


def main():
    for d in DIRS:
        n, b, a = convert_dir(d)
        if n:
            print(f"{d}: {n} jpg -> webp | {round(b/1e6)}MB -> {round(a/1e6)}MB")
    # actualizar DB: img/athome/*.jpg -> .webp
    conn = db.get_conn()
    rows = conn.execute("SELECT id, photos FROM listings WHERE photos LIKE '%img/athome/%.jpg%'").fetchall()
    for r in rows:
        photos = json.loads(r["photos"]) if r["photos"] else []
        photos = [(p[:-4] + ".webp" if p.startswith("img/athome/") and p.endswith(".jpg") else p) for p in photos]
        conn.execute("UPDATE listings SET photos=? WHERE id=?", (json.dumps(photos, ensure_ascii=False), r["id"]))
    conn.commit()
    conn.close()
    print(f"DB: {len(rows)} fichas actualizadas a .webp")
    n = db.export_geojson()
    print(f"Exportadas {n} casas")


if __name__ == "__main__":
    main()
