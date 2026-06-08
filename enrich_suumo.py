# -*- coding: utf-8 -*-
"""
Enriquecedor de fichas de SUUMO (USO PERSONAL).

El listado de SUUMO solo trae 1 miniatura por edificio. Este script abre la
página de detalle de cada anuncio y extrae TODAS las fotos reales del inmueble
—incluido el 間取り図 (plano/"mapa de la casa")— directamente del HTML, sin
adivinar nada. Las fotos se sirven desde SUUMO (URLs remotas: no ocupan espacio).

Filtra logos de agencia (front_kaisha) y se queda solo con las imágenes cuyo
identificador coincide con el del propio anuncio (no de anuncios relacionados).

Uso:
    python enrich_suumo.py            # enriquece TODO SUUMO (lento, ~horas)
    python enrich_suumo.py --max 300  # solo los 300 alquileres más baratos
    python enrich_suumo.py --rent-max 60000 --max 400
Es reanudable: salta los anuncios que ya tienen varias fotos.
"""

import argparse
import re
import sys
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup

import config
import db

BASE = "https://suumo.jp"
DELAY = 1.6  # pausa educada entre peticiones a SUUMO

_sess = requests.Session()
_sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
})

# fotos de entorno (super, conbini...) o material no-vivienda: fuera, para no ensuciar
AMENITY = re.compile(r"スーパー|コンビニ|ドラ[ッック]+グ|ドラッグ|ホームセンター|"
                     r"周辺|駅前|その他施設|学校|病院|公園|銀行|郵便|ショッピング")
JUNK = re.compile(r"front_kaisha|_kaisha|_tgk|/common/|logo|banner|spacer|nowprinting|"
                  r"now_printing|noimage|no_image", re.I)


def _get(url):
    for _ in range(2):
        try:
            r = _sess.get(url, timeout=config.HTTP_TIMEOUT)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            time.sleep(DELAY)
    return None


def _img_url(im):
    for a in ("rel", "data-src", "data-original", "src"):
        v = im.get(a)
        if isinstance(v, list):
            v = v[0] if v else None
        if v and v.startswith("http"):
            return v
    return None


def extract_photos(html, cap=12):
    """Devuelve [floor_plan..., fotos de la casa...] solo de ESTE anuncio."""
    soup = BeautifulSoup(html, "lxml")
    gal = soup.select_one("#js-view_gallery") or soup
    items = []
    for im in gal.find_all("img"):
        u = _img_url(im)
        if u and "bukken" in u and not JUNK.search(u):
            items.append((im.get("alt") or "", u))
    if not items:
        return []
    # id del inmueble = el más frecuente entre las imágenes /bukken/NNN/<id>/
    ids = [re.search(r"/bukken/\d+/(\d+)/", u) for _, u in items]
    counts = Counter(m.group(1) for m in ids if m)
    if not counts:
        return []
    main = counts.most_common(1)[0][0]
    # SUUMO sirve cada foto en dos tamaños (..._Xo.jpg grande / ..._Xt.jpg mini);
    # colapsamos por base y preferimos la grande para no duplicar (p. ej. el plano).
    floor, house, seen_base = [], [], {}
    def base(u):
        return re.sub(r"[ot]\.jpg$", ".jpg", u)
    for alt, u in items:
        m = re.search(r"/bukken/\d+/(\d+)/", u)
        if not m or m.group(1) != main:
            continue
        if AMENITY.search(alt):
            continue  # entorno (super/conbini...): fuera, solo la casa
        b = base(u)
        big = u.endswith("o.jpg")
        bucket = floor if "間取" in alt else house
        if b in seen_base:
            # si ya teníamos la mini y llega la grande, la sustituimos
            idx, lst = seen_base[b]
            if big and not lst[idx].endswith("o.jpg"):
                lst[idx] = u
            continue
        bucket.append(u)
        seen_base[b] = (len(bucket) - 1, bucket)
    return (floor + house)[:cap]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="límite de anuncios (0 = todos)")
    ap.add_argument("--rent-max", type=int, default=0, help="solo alquiler <= este ¥")
    ap.add_argument("--min-photos", type=int, default=3,
                    help="salta anuncios que ya tengan al menos estas fotos")
    args = ap.parse_args()

    conn = db.get_conn()
    q = "SELECT id, source_url, photos FROM listings WHERE source='suumo' AND active=1"
    params = []
    if args.rent_max:
        q += " AND rent_yen IS NOT NULL AND rent_yen <= ?"
        params.append(args.rent_max)
    q += " ORDER BY rent_yen ASC"
    rows = conn.execute(q, params).fetchall()

    todo = []
    import json
    for r in rows:
        try:
            ph = json.loads(r["photos"]) if r["photos"] else []
        except Exception:
            ph = []
        if len(ph) >= args.min_photos:
            continue
        todo.append(r["id"])
        if args.max and len(todo) >= args.max:
            break

    print(f"A enriquecer: {len(todo)} de {len(rows)} anuncios SUUMO", flush=True)
    done = enriched = 0
    for lid in todo:
        row = conn.execute("SELECT source_url FROM listings WHERE id=?", (lid,)).fetchone()
        url = row["source_url"]
        # normaliza a la página de ficha (sin querystring de campaña)
        page = re.sub(r"\?.*$", "", url)
        html = _get(page)
        done += 1
        if html:
            photos = extract_photos(html)
            if photos:
                import json as _j
                conn.execute("UPDATE listings SET photos=? WHERE id=?",
                             (_j.dumps(photos, ensure_ascii=False), lid))
                conn.commit()
                enriched += 1
        if done % 20 == 0:
            print(f"  {done}/{len(todo)}  (con fotos nuevas: {enriched})", flush=True)
    conn.close()
    print(f"Hecho. {enriched}/{done} anuncios con galería real.", flush=True)
    n = db.export_geojson()
    print(f"GeoJSON re-exportado: {n} propiedades.", flush=True)


if __name__ == "__main__":
    main()
