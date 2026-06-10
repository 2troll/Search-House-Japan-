#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich_initcost.py — extrae el COSTE DE ENTRADA REAL (初期費用) abriendo la ficha
individual de cada anuncio, en vez de estimarlo.

Problema que resuelve: la lista de SUUMO/at-home solo trae el alquiler (y a veces
礼金/敷金). El total real de entrada (鍵交換, クリーニング, 火災保険, 仲介手数料,
保証会社…) vive en la FICHA de detalle. Este script la abre, extrae cada concepto
y lo guarda en features, recalculando un 初期費用 real.

Diseño:
  - RESUMABLE: salta los anuncios ya enriquecidos (features['_ic'] == 1). Se puede
    ejecutar muchas veces; va rellenando poco a poco (los portales limitan el ritmo).
  - EDUCADO: pausa entre peticiones, User-Agent de navegador, caché por URL.
  - INCREMENTAL: --limit N procesa solo N por ejecución; --source elige la fuente;
    --order cheap prioriza las más baratas (las que más confunden al usuario).

Uso:
    python3 enrich_initcost.py --source suumo --limit 300 --order cheap
    python3 enrich_initcost.py --source athome_rent --limit 200
"""

import argparse
import html
import json
import re
import sys
import time

import requests

import config
import db

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
DELAY = 1.8
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})

# label -> clave que guardamos en features
LABELS = [
    ("礼金", "礼金"), ("敷金", "敷金"), ("保証金", "保証金"),
    ("敷引・償却", "敷引"), ("敷引", "敷引"), ("償却", "償却"),
    ("管理費・共益費", "管理費"), ("共益費", "管理費"),
    ("仲介手数料", "仲介手数料"), ("火災保険", "火災保険"),
    ("保証会社", "保証会社"), ("保証委託", "保証会社"),
    ("鍵交換", "鍵交換"), ("クリーニング", "クリーニング"),
    ("初期費用", "初期費用"), ("その他一時金", "その他一時金"),
]
VALUE = (r'([0-9][0-9.,]*\s*万?円(?:[~〜][0-9][0-9.,]*\s*万?円)?'
         r'|賃料の?[0-9.]+\s*[ヶか月％%]+|[0-9.]+\s*[ヶか]?月分?'
         r'|なし|無料|不要|別途|実費|-)')


def _to_yen(v, rent=None):
    """Convierte un valor textual a yenes (aprox). None si no se puede."""
    if not v:
        return None
    v = v.replace(",", "").strip()
    if v in ("-", "なし", "無料", "不要", "0", "0円"):
        return 0
    m = re.search(r"([\d.]+)\s*万円", v)
    if m:
        return int(round(float(m.group(1)) * 10000))
    m = re.search(r"([\d.]+)\s*円", v)
    if m:
        return int(float(m.group(1)))
    if rent:
        m = re.search(r"([\d.]+)\s*[ヶか]?月", v)
        if m:
            return int(round(float(m.group(1)) * rent))
        m = re.search(r"賃料の?([\d.]+)\s*[％%]", v)
        if m:
            return int(round(float(m.group(1)) / 100 * rent))
    return None


def parse_fees(page_html):
    """Devuelve {clave: valor_texto} con los conceptos de coste de la ficha."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", page_html))
    t = re.sub(r"\s+", " ", t)
    out = {}
    for label, key in LABELS:
        if key in out:
            continue
        m = re.search(re.escape(label) + r"\s*[:：]?\s*" + VALUE, t)
        if m:
            out[key] = m.group(1).strip()
    return out


def compute_initial(fees, rent, mgmt):
    """Suma un 初期費用 real con lo que se haya podido extraer (honesto: solo lo presente)."""
    if not rent:
        return None, []
    total = rent + (mgmt or 0)          # 1.er mes de alquiler + gastos
    used = ["1er mes"]
    for key in ("礼金", "敷金", "保証金", "鍵交換", "クリーニング", "火災保険",
                "仲介手数料", "保証会社", "その他一時金"):
        if key in fees:
            y = _to_yen(fees[key], rent)
            if y:
                total += y
                used.append(f"{key} {y}")
    return total, used


def fetch(url):
    for _ in range(2):
        try:
            r = _sess.get(url, timeout=config.HTTP_TIMEOUT)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.content.decode("utf-8", errors="replace")
        except requests.RequestException:
            time.sleep(DELAY)
    return None


def run(source, limit, order):
    conn = db.get_conn()
    conn.row_factory = __import__("sqlite3").Row
    order_sql = "rent_yen ASC" if order == "cheap" else "id ASC"
    rows = conn.execute(
        f"SELECT id, source_url, rent_yen, management_fee_yen, features "
        f"FROM listings WHERE source=? AND active=1 AND listing_type='rent' "
        f"AND source_url LIKE 'http%' ORDER BY {order_sql}",
        (source,)).fetchall()

    todo = []
    for r in rows:
        try:
            ft = json.loads(r["features"]) if r["features"] else {}
        except Exception:
            ft = {}
        if ft.get("_ic"):
            continue          # ya enriquecido (resumable)
        todo.append((r, ft))
    print(f"{source}: {len(rows)} anuncios, {len(todo)} sin enriquecer. Procesando {min(limit,len(todo))}…")

    done = ok = 0
    for r, ft in todo[:limit]:
        page = fetch(r["source_url"])
        done += 1
        if not page:
            continue
        fees = parse_fees(page)
        if fees:
            # Guardamos solo los COMPONENTES reales que sí aparecen en el HTML estático.
            # NO calculamos un total 初期費用: la web esconde 仲介/火災/保証 en su
            # calculadora JS, así que sumar lo poco visible da un total ENGAÑOSO (bajo).
            for k, v in fees.items():
                if k != "初期費用":
                    ft[k] = v
            # si la ficha trae 礼金/敷金 explícitos, sustituye los de la lista
            # (normalizando '-' -> 'なし' para no romper el detector de cero entrada).
            def _norm(x):
                return "なし" if (x or "").strip() in ("-", "ー", "−") else x
            for src_key, col in (("礼金", "key_money"), ("敷金", "deposit")):
                if src_key in fees:
                    conn.execute(f"UPDATE listings SET {col}=? WHERE id=?", (_norm(fees[src_key]), r["id"]))
            ok += 1
        ft["_ic"] = 1
        conn.execute("UPDATE listings SET features=? WHERE id=?",
                     (json.dumps(ft, ensure_ascii=False), r["id"]))
        if done % 25 == 0:
            conn.commit()
            print(f"  {done}/{min(limit,len(todo))} (con datos: {ok})")
    conn.commit()
    conn.close()
    print(f"Hecho: {done} fichas abiertas, {ok} con costes extraídos.")
    print("Exporta con:  python3 -c 'import db; db.export_geojson()'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="suumo")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--order", choices=["cheap", "id"], default="cheap")
    a = ap.parse_args()
    db.init_db()
    run(a.source, a.limit, a.order)


if __name__ == "__main__":
    main()
