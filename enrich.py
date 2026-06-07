#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich.py — extracción PROFUNDA ficha a ficha de at-home.

Para cada anuncio de at-home de las zonas indicadas, ABRE la ficha de detalle,
descarga TODAS las fotos al sitio y extrae las condiciones (こだわり条件, 設備,
備考, 敷金/保証金...). Actualiza la base de datos y re-exporta el GeoJSON.

Uso:
    python3 enrich.py awaji            # Awaji (南あわじ + 洲本 + 淡路)
    python3 enrich.py minamiawaji sumoto
    python3 enrich.py --all            # todas las zonas (lento)

Es respetuoso: usa el HttpClient con rate limit y caché. Hazlo por fases.
"""

import io
import os
import re
import sys

from bs4 import BeautifulSoup

import config
import db
from sources.base import HttpClient
from sources.athome_akiya import IMG_DIR, _img_session

AWAJI = ["minamiawaji", "sumoto", "awaji_shi"]


def _download(url, bid, idx):
    os.makedirs(IMG_DIR, exist_ok=True)
    rel = f"img/athome/{bid}_{idx}.jpg"
    dest = os.path.join(IMG_DIR, f"{bid}_{idx}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return rel
    try:
        r = _img_session.get(url, timeout=config.HTTP_TIMEOUT)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            with open(dest, "wb") as f:
                f.write(r.content)
            return rel
    except Exception:
        pass
    return ""


def _detail_dict(soup):
    info = {}
    for tbl in soup.find_all("table"):
        for tr in tbl.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            for i in range(0, len(cells) - 1, 2):
                k, v = cells[i].strip(), cells[i + 1].strip()
                if k and k not in info:
                    info[k] = v
    return info


def enrich_listing(client, conn, row):
    url = row["source_url"]
    bid_m = re.search(r"/(\d+)\s*$", url)
    bid = bid_m.group(1) if bid_m else None
    html = client.get(url)
    if not html or not bid:
        return False
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.extract()

    # fotos: están en un JSON embebido ("image_url_fullsize":"//img...."), con las
    # barras escapadas (\/). El carrusel trae TODAS las fotos del anuncio.
    remote = []
    for u in re.findall(r'"image_url_fullsize":"([^"]+)"', html):
        u = u.replace("\\/", "/")
        if u.startswith("//"):
            u = "https:" + u
        if u not in remote:
            remote.append(u)
    if not remote:  # respaldo: miniaturas o src directos
        for u in re.findall(r'"image_url_thumbnail":"([^"]+)"', html):
            u = u.replace("\\/", "/")
            if u.startswith("//"):
                u = "https:" + u
            if u not in remote:
                remote.append(u)
    if not remote:
        for m in re.findall(r"(//img\.akiya-athome\.jp/[^\"'\s]+)", html):
            u = "https:" + m
            if u not in remote:
                remote.append(u)
    photos = []
    for i, u in enumerate(remote[:10]):  # hasta 10 fotos por casa
        local = _download(u, bid, i)
        if local:
            photos.append(local)

    # condiciones
    info = _detail_dict(soup)
    cond = info.get("こだわり 条件") or info.get("こだわり条件") or info.get("こだわりポイント") or ""
    equip = info.get("設備", "")
    remarks = info.get("備考", "")
    deposit = info.get("敷金/保証金", "")
    keymoney = info.get("権利金", "")
    maint = info.get("維持費等", "")

    import json
    feats = json.loads(row["features"]) if row["features"] else {}
    for k, v in {"条件": cond, "設備": equip, "備考": remarks,
                 "敷金保証金": deposit, "権利金": keymoney, "維持費": maint}.items():
        if v and v not in ("-", "/"):
            feats[k] = v

    sets, params = [], []
    if photos:
        sets.append("photos = ?"); params.append(json.dumps(photos, ensure_ascii=False))
    sets.append("features = ?"); params.append(json.dumps(feats, ensure_ascii=False))
    params.append(url)
    conn.execute(f"UPDATE listings SET {', '.join(sets)} WHERE source_url = ?", params)
    return bool(photos)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv:
        areas = None
    elif args == ["awaji"] or not args:
        areas = AWAJI
    else:
        areas = args

    client = HttpClient()
    conn = db.get_conn()
    if areas:
        ph = ", ".join("?" for _ in areas)
        rows = conn.execute(
            f"SELECT * FROM listings WHERE source='athome' AND area_key IN ({ph}) AND active=1",
            areas).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM listings WHERE source='athome' AND active=1").fetchall()

    print(f"Enriqueciendo {len(rows)} fichas de at-home (zonas: {areas or 'todas'})...")
    ok = 0
    for i, row in enumerate(rows, 1):
        try:
            if enrich_listing(client, conn, row):
                ok += 1
            if i % 10 == 0:
                conn.commit()
                print(f"  {i}/{len(rows)} ({ok} con fotos)")
        except Exception as e:
            print(f"  error en {row['source_url']}: {e}")
    conn.commit()
    conn.close()
    n = db.export_geojson()
    print(f"Hecho. {ok}/{len(rows)} con fotos. Exportadas {n} casas.")


if __name__ == "__main__":
    main()
