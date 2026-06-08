# -*- coding: utf-8 -*-
"""
Enriquecedor de apartamentos UR (UR都市機構, vivienda pública).

El listado de UR solo trae 1 foto. Su propia API de detalle (pública) devuelve
la galería completa del danchi (12-17 fotos, incl. plano). Las fotos se sirven
desde UR (URLs remotas: no ocupan espacio).

API:  POST .../chintai/api/bukken/detail/detail_bukken/
      datos: shisya, danchi, shikibetu, mode=init, id  (derivados de la URL)

Uso:  python enrich_ur.py                 # todos los UR con <3 fotos
      python enrich_ur.py --workers 6 --rps 3
Reanudable y con tope de velocidad global (educado con UR).
"""

import argparse
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import config
import db

API = "https://chintai.r6.ur-net.go.jp/chintai/api/bukken/detail/detail_bukken/"
JUNK = re.compile(r"/common/|logo|banner|icon|noimage|no_image|spacer|dummy", re.I)

_local = threading.local()


def _session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": config.USER_AGENT, "Referer": "https://www.ur-net.go.jp/"})
        _local.s = s
    return s


class Rate:
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


def _parse_id(url):
    m = re.search(r"/(\d+_\d+)\.html", url or "")
    return m.group(1) if m else None


def fetch_photos(did, rate):
    """did = '80_1130' -> shisya=80, danchi=113, shikibetu=0."""
    sh, suf = did.split("_")[0], did.split("_")[1]
    danchi, shik = suf[:-1], suf[-1]
    rate.wait()
    try:
        r = _session().post(API, data={"shisya": sh, "danchi": danchi, "shikibetu": shik,
                                        "mode": "init", "id": did}, timeout=12)
        data = json.loads(r.content.decode("utf-8-sig"))
    except Exception:
        return []
    out, seen = [], set()
    for blk in data if isinstance(data, list) else []:
        for im in blk.get("img", []):
            p = im.get("画像パス") or ""
            if p.startswith("http") and not JUNK.search(p) and p not in seen:
                seen.add(p)
                out.append(p)
    return out[:14]


def _work(lid, url, rate):
    did = _parse_id(url)
    return lid, (fetch_photos(did, rate) if did else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--min-photos", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--rps", type=float, default=3.0)
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()

    conn = db.get_conn()
    rows = conn.execute("SELECT id, source_url, photos FROM listings "
                        "WHERE source='ur' AND active=1").fetchall()
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

    print(f"A enriquecer: {len(todo)} de {len(rows)} UR "
          f"({args.workers} hilos, {args.rps} req/s)", flush=True)
    rate = Rate(args.rps)
    done = enriched = 0
    pending = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_work, lid, url, rate) for lid, url in todo]
        for fut in as_completed(futs):
            try:
                lid, photos = fut.result()
            except Exception:
                lid, photos = None, []
            done += 1
            if lid is not None and photos:
                pending.append((json.dumps(photos, ensure_ascii=False), lid))
                enriched += 1
            if len(pending) >= 25:
                conn.executemany("UPDATE listings SET photos=? WHERE id=?", pending)
                conn.commit()
                pending.clear()
            if done % 50 == 0:
                print(f"  {done}/{len(todo)} (con galería: {enriched})", flush=True)
    if pending:
        conn.executemany("UPDATE listings SET photos=? WHERE id=?", pending)
        conn.commit()
    conn.close()
    print(f"Hecho. {enriched}/{done} UR con galería real.", flush=True)
    if not args.no_export:
        print(f"GeoJSON re-exportado: {db.export_geojson()} propiedades.", flush=True)


if __name__ == "__main__":
    main()
