# Graph Report - .  (2026-06-10)

## Corpus Check
- Corpus is ~20,719 words - fits in a single context window. You may not need a graph.

## Summary
- 212 nodes · 434 edges · 17 communities (13 shown, 4 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.75)
- Token cost: 79,630 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Municipal scrapers & base helpers|Municipal scrapers & base helpers]]
- [[_COMMUNITY_Source adapters & Listing schema|Source adapters & Listing schema]]
- [[_COMMUNITY_Data pipeline & map-data bridge|Data pipeline & map-data bridge]]
- [[_COMMUNITY_Listing enrichment & photo download|Listing enrichment & photo download]]
- [[_COMMUNITY_Geocoding & area matching|Geocoding & area matching]]
- [[_COMMUNITY_Web app frontend (filters, map, costs)|Web app frontend (filters, map, costs)]]
- [[_COMMUNITY_SQLite store (DB layer)|SQLite store (DB layer)]]
- [[_COMMUNITY_SUUMO photo enrichment (threaded)|SUUMO photo enrichment (threaded)]]
- [[_COMMUNITY_Refresh orchestrator & HttpClient|Refresh orchestrator & HttpClient]]
- [[_COMMUNITY_GaijinPot scraper|GaijinPot scraper]]
- [[_COMMUNITY_SUUMO scraper & area parsing|SUUMO scraper & area parsing]]
- [[_COMMUNITY_UR housing photo enrichment|UR housing photo enrichment]]
- [[_COMMUNITY_WebP image conversion|WebP image conversion]]
- [[_COMMUNITY_RentBuy guide modal|Rent/Buy guide modal]]
- [[_COMMUNITY_i18n (ESEN)|i18n (ES/EN)]]
- [[_COMMUNITY_Project overview (README)|Project overview (README)]]

## God Nodes (most connected - your core abstractions)
1. `Listing` - 25 edges
2. `assign_area()` - 23 edges
3. `parse_area_m2()` - 19 edges
4. `parse_price_yen()` - 18 edges
5. `detect_foreigner_ok()` - 16 edges
6. `parse_year_built()` - 13 edges
7. `_parse_detail()` - 13 edges
8. `HttpClient` - 12 edges
9. `_parse_pdf()` - 11 edges
10. `_parse_detail()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `buyCost() purchase-cost model` --semantically_similar_to--> `Real stay-cost calculator (key feature)`  [INFERRED] [semantically similar]
  web/index.html → README.md
- `data.geojson fetch/loader` --shares_data_with--> `Extraction pipeline (refresh -> SQLite -> GeoJSON)`  [INFERRED]
  web/index.html → README.md
- `enrich_listing()` --calls--> `detect_foreigner_ok()`  [EXTRACTED]
  enrich.py → sources/base.py
- `enrich_listing()` --calls--> `parse_area_m2()`  [EXTRACTED]
  enrich.py → sources/base.py
- `enrich_listing()` --calls--> `parse_year_built()`  [EXTRACTED]
  enrich.py → sources/base.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Scrape-normalize-geocode-export data pipeline** — readme_refresh, readme_source_registry, readme_listing_dataclass, readme_geocode, readme_sqlite_db, readme_data_geojson [EXTRACTED 0.90]
- **stayCost model and its UI consumers** — index_staycost, index_filters_matches, index_detail_drawer, index_favorites_compare, index_ai_agent [EXTRACTED 0.90]
- **GeoJSON load-time enrichment** — index_geojson_loader, index_photo_cleaning, index_stigma_detection, index_spread_overlaps [EXTRACTED 0.90]

## Communities (17 total, 4 thin omitted)

### Community 0 - "Municipal scrapers & base helpers"
Cohesion: 0.11
Nodes (33): detect_foreigner_ok(), detect_pet(), detect_renovated(), parse_parking(), parse_year_built(), Convierte caracteres de ancho completo (０１２ＳＬＤＫ) a normales., Clasifica el campo 車庫/駐車場 -> yes | nearby | no | unknown., Busca menciones a extranjeros. Si no hay nada -> 'unknown' (NO descartar). (+25 more)

### Community 1 - "Source adapters & Listing schema"
Cohesion: 0.14
Nodes (21): fetch(), _get(), _parse_block(), 4.8万円' -> 48000 · 'なし'/'-' -> 0 · '3,000円' -> 3000 · '' -> None., _txt(), _yen_man(), fetch(), assign_area() (+13 more)

### Community 2 - "Data pipeline & map-data bridge"
Cohesion: 0.12
Nodes (21): AREA_LABELS (zone labels, sync with TARGET_AREAS), data.geojson fetch/loader, cleanPhotos() junk-image filter, spreadOverlaps() de-stacking of same-coordinate markers, Casas Japon single-file web app, config.py TARGET_AREAS (search zones), Manual CSV import (commercial portals), web/data.geojson (generated map data) (+13 more)

### Community 3 - "Listing enrichment & photo download"
Cohesion: 0.18
Nodes (17): _detail_dict(), _download(), enrich_listing(), main(), _download_photo(), fetch(), _field(), _parse_card() (+9 more)

### Community 4 - "Geocoding & area matching"
Cohesion: 0.17
Nodes (13): junk_basenames(), main(), Devuelve el conjunto de nombres de archivo que son logos/banners., match_area(), Devuelve el bloque de TARGET_AREAS que coincida con `text` (una dirección)., _cache_get(), _cache_put(), geocode() (+5 more)

### Community 5 - "Web app frontend (filters, map, costs)"
Cohesion: 0.19
Nodes (15): AI real-estate agent (Free Pollinations / Pro Claude), Editable fee assumptions (localStorage), buyCost() purchase-cost model, Live currency conversion (er-api), Listing detail drawer + gallery (openDetail), Entry/first-month cost filter (entryCost), Favorites + compare view (toggleFav/renderCompare), Filter engine matches()/apply() (+7 more)

### Community 6 - "SQLite store (DB layer)"
Cohesion: 0.23
Nodes (11): export_geojson(), get_conn(), init_db(), _is_new(), mark_inactive(), _now(), Marca active=0 las casas de `source` cuya url no se haya visto en este refresh., True si first_seen es de los últimos `days` días (para el filtro 'novedades'). (+3 more)

### Community 7 - "SUUMO photo enrichment (threaded)"
Cohesion: 0.24
Nodes (9): extract_photos(), _fetch_one(), _get(), main(), Rate, Devuelve [plano, fotos de la casa...] SOLO de este anuncio. Sin BeautifulSoup., (hilo trabajador) descarga + extrae. No toca la BD., Limitador GLOBAL de ritmo: como mucho `rps` peticiones/segundo en total,     da (+1 more)

### Community 8 - "Refresh orchestrator & HttpClient"
Cohesion: 0.29
Nodes (4): main(), run(), HttpClient, GET con caché, rate limit, robots y reintentos. Devuelve texto o None.

### Community 9 - "GaijinPot scraper"
Cohesion: 0.27
Nodes (9): fetch(), _fullsize(), _get(), _ld_blocks(), _parse_detail(), _Rate, Quita la variante de tamaño: .../9-cco707/_w300_h300_x.jpeg -> .../9-cco707.jpeg, _session() (+1 more)

### Community 10 - "SUUMO scraper & area parsing"
Cohesion: 0.29
Nodes (10): _clean_num(), parse_area_m2(), Extrae el primer número de un texto (tolera espacios dentro: '401. 38')., Extrae metros cuadrados de '401. 38 ㎡（121坪）' -> 401.38., _city_slugs(), fetch(), _get(), _parse_page() (+2 more)

### Community 11 - "UR housing photo enrichment"
Cohesion: 0.31
Nodes (7): fetch_photos(), main(), _parse_id(), Rate, did = '80_1130' -> shisya=80, danchi=113, shikibetu=0., _session(), _work()

## Knowledge Gaps
- **13 isolated node(s):** `Buscador de casas baratas en Japon (project overview)`, `GitHub Pages publishing (static web)`, `Spanish filter panel (rent, parking, layout, zone...)`, `imports/ directory (drop CSVs here)`, `Python dependencies (requests, beautifulsoup4, lxml, pypdfium2)` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Listing` connect `Source adapters & Listing schema` to `Municipal scrapers & base helpers`, `GaijinPot scraper`, `SUUMO scraper & area parsing`, `Listing enrichment & photo download`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `assign_area()` connect `Source adapters & Listing schema` to `Municipal scrapers & base helpers`, `Refresh orchestrator & HttpClient`, `SUUMO scraper & area parsing`, `Listing enrichment & photo download`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `HttpClient` connect `Refresh orchestrator & HttpClient` to `Municipal scrapers & base helpers`, `Listing enrichment & photo download`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **What connects `Devuelve el conjunto de nombres de archivo que son logos/banners.`, `Devuelve el bloque de TARGET_AREAS que coincida con `text` (una dirección).`, `Inserta o actualiza un anuncio usando source_url como clave única.      `data` e` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Municipal scrapers & base helpers` be split into smaller, more focused modules?**
  _Cohesion score 0.11411411411411411 - nodes in this community are weakly interconnected._
- **Should `Source adapters & Listing schema` be split into smaller, more focused modules?**
  _Cohesion score 0.1396011396011396 - nodes in this community are weakly interconnected._
- **Should `Data pipeline & map-data bridge` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._