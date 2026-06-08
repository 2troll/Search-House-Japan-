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
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

import config
import db

BASE = "https://suumo.jp"

# Cada hilo usa su propia sesión (requests.Session no es 100% thread-safe).
_local = threading.local()
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def _session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": _UA, "Accept-Language": "ja,en;q=0.8"})
        _local.s = s
    return s


class Rate:
    """Limitador GLOBAL de ritmo: como mucho `rps` peticiones/segundo en total,
    da igual cuántos hilos haya. Mantiene el scraping educado con SUUMO."""
    def __init__(self, rps):
        self.interval = 1.0 / rps
        self.lock = threading.Lock()
        self.next = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            t = max(now, self.next)
            self.next = t + self.interval
            delay = t - now
        if delay > 0:
            time.sleep(delay)


# fotos de entorno (super, conbini...) o material no-vivienda: fuera, para no ensuciar
AMENITY = re.compile(r"スーパー|コンビニ|ドラ[ッック]+グ|ドラッグ|ホームセンター|"
                     r"周辺|駅前|その他施設|学校|病院|公園|銀行|郵便|ショッピング")
JUNK = re.compile(r"front_kaisha|_kaisha|_tgk|/common/|logo|banner|spacer|nowprinting|"
                  r"now_printing|noimage|no_image", re.I)


def _get(url, rate=None):
    for _ in range(2):
        if rate:
            rate.wait()
        try:
            r = _session().get(url, timeout=12)  # corto: páginas lentas no estancan el lote
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
    return None


# Imagen de inmueble en SUUMO: .../bukken/NNN/<id>/<id>_<sufijo>.jpg
# El <sufijo> codifica el TIPO sin necesidad de leer el alt (parseo por regex,
# 100x más rápido que BeautifulSoup sobre 450 KB):
#   'c'  -> 間取り図 (plano / "mapa de la casa")
#   's…' -> entorno (super, conbini, estación...): se descarta
#   'g', '1','2',…,'r' -> exterior y habitaciones reales de la vivienda
# Cada foto viene en dos tamaños: 'o' (grande) y 't' (mini) -> nos quedamos la grande.
_IMG_RE = re.compile(r"https://img\d+\.suumo\.com/[^\"'\s]*?/bukken/\d+/(\d+)/\1_([0-9a-z]+)\.jpg", re.I)


def extract_photos(html, cap=12):
    """Devuelve [plano, fotos de la casa...] SOLO de este anuncio. Sin BeautifulSoup."""
    if not html:
        return []
    matches = _IMG_RE.findall(html)
    if not matches:
        return []
    # id del inmueble = el más frecuente (los anuncios relacionados aportan pocas)
    main = Counter(i for i, _ in matches).most_common(1)[0][0]
    floor, house, seen = [], [], set()
    for i, suf in matches:
        if i != main:
            continue
        key = suf[:-1] if suf[-1] in "ot" else suf   # quita el char de tamaño
        if key.startswith("s"):
            continue                                 # entorno: fuera
        if key in seen:
            continue
        seen.add(key)
        url = f"https://img01.suumo.com/front/gazo/fr/bukken/{main[-3:]}/{main}/{main}_{key}o.jpg"
        (floor if key == "c" else house).append(url)
    return (floor + house)[:cap]


def _fetch_one(lid, url, rate):
    """(hilo trabajador) descarga + extrae. No toca la BD."""
    page = re.sub(r"\?.*$", "", url)  # ficha sin querystring de campaña
    html = _get(page, rate)
    return lid, (extract_photos(html) if html else [])


def main():
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="límite de anuncios (0 = todos)")
    ap.add_argument("--rent-max", type=int, default=0, help="solo alquiler <= este ¥")
    ap.add_argument("--min-photos", type=int, default=3,
                    help="salta anuncios que ya tengan al menos estas fotos")
    ap.add_argument("--workers", type=int, default=5, help="hilos concurrentes")
    ap.add_argument("--rps", type=float, default=3.0, help="tope global de peticiones/seg")
    ap.add_argument("--no-export", action="store_true", help="no re-exportar geojson al final")
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
    for r in rows:
        try:
            ph = json.loads(r["photos"]) if r["photos"] else []
        except Exception:
            ph = []
        if len(ph) >= args.min_photos:
            continue
        todo.append((r["id"], r["source_url"]))
        if args.max and len(todo) >= args.max:
            break

    est = len(todo) / max(args.rps, 0.1) / 60.0
    print(f"A enriquecer: {len(todo)} de {len(rows)} anuncios SUUMO "
          f"({args.workers} hilos, {args.rps} req/s, ~{est:.0f} min)", flush=True)

    rate = Rate(args.rps)
    done = enriched = 0
    pending = []  # (lid, photos_json) por escribir en lote
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_fetch_one, lid, url, rate) for lid, url in todo]
        for fut in as_completed(futs):
            try:
                lid, photos = fut.result()
            except Exception:
                lid, photos = None, []
            done += 1
            if lid is not None and photos:
                pending.append((json.dumps(photos, ensure_ascii=False), lid))
                enriched += 1
            if len(pending) >= 25:  # escritura en lote (un solo hilo escribe)
                conn.executemany("UPDATE listings SET photos=? WHERE id=?", pending)
                conn.commit()
                pending.clear()
            if done % 50 == 0:
                print(f"  {done}/{len(todo)}  (con galería: {enriched})", flush=True)
    if pending:
        conn.executemany("UPDATE listings SET photos=? WHERE id=?", pending)
        conn.commit()
    conn.close()
    print(f"Hecho. {enriched}/{done} anuncios con galería real.", flush=True)
    if not args.no_export:
        n = db.export_geojson()
        print(f"GeoJSON re-exportado: {n} propiedades.", flush=True)


if __name__ == "__main__":
    main()
