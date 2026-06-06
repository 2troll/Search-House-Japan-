# 🏠 Buscador de casas baratas en Japón (空き家 / 賃貸)

Herramienta **personal** para buscar casas (戸建て) baratas en alquiler o venta en
los bancos de casas vacías (`空き家バンク`) japoneses, con **mapa interactivo** y
**filtros en español**.

Extrae anuncios de fuentes públicas/municipales, los normaliza en una base de
datos **SQLite local**, geocodifica las direcciones japonesas a coordenadas y los
muestra sobre un mapa **Leaflet + OpenStreetMap** (sin API keys) con una vista de
lista sincronizada.

> Uso personal, sin redistribución de datos. La extracción es **responsable**:
> respeta `robots.txt`, limita la velocidad (≥3 s entre peticiones al mismo
> dominio), usa un User-Agent identificable y cachea en disco.

---

## 📦 Estructura del proyecto

```
config.py            # ⚙️  TARGET_AREAS (zonas) y ajustes de extracción  ← EDITA AQUÍ
geocode.py           # direcciones japonesas → lat/lng (GSI + Nominatim + caché)
refresh.py           # re-extrae todas las fuentes, deduplica y exporta el GeoJSON
sample_import.csv    # plantilla para importar anuncios a mano (portales comerciales)
requirements.txt

/db
  schema.sql         # esquema SQLite (tabla listings + geocode_cache)
  __init__.py        # helpers: init_db, upsert, export_geojson...
  listings.sqlite    # (se genera; no se versiona)

/sources             # 🔌 un adaptador por fuente
  base.py            # HttpClient educado + dataclass Listing + parseo japonés
  registry.py        # 📋 lista de fuentes activas  ← AÑADE FUENTES AQUÍ
  suminiko.py        # 南あわじ市 空き家バンク (público) — verificado
  sumonavi.py        # 洲本市 空き家バンク (público) — verificado
  wakayama_portal.py # わかやま住まいポータル: toda Wakayama (público) — verificado
  awaji_city.py      # 淡路市 (opcional, desactivado)
  homes_akiyabank.py # agregador LIFULL HOME'S (opcional, desactivado)
  csv_import.py      # importación manual por CSV (SUUMO/at-home/HOME'S 賃貸...)

/imports             # pon aquí tus CSV (imports/*.csv)
/web
  index.html         # 🗺️  mapa Leaflet + panel de filtros (UI en español)
  data.geojson       # (se genera) lo que lee el mapa
/cache               # caché HTTP en disco (se genera; no se versiona)
```

---

## 🚀 Instalación

Requiere **Python 3.9+**.

```bash
pip install -r requirements.txt
```

(Solo `requests`, `beautifulsoup4` y `lxml`. `playwright` es opcional y hoy no
hace falta para ninguna fuente.)

---

## ▶️ Uso

**1. Extraer y actualizar los datos:**

```bash
python3 refresh.py                # todas las fuentes activas (+ tus CSV)
python3 refresh.py suminiko       # solo una fuente concreta
python3 refresh.py --all          # incluye también las fuentes opcionales
python3 refresh.py --no-geocode   # salta la geocodificación (más rápido)
```

Esto crea/actualiza `db/listings.sqlite` y exporta `web/data.geojson`.

**2. Abrir el mapa** (hace falta un servidor local porque el navegador no deja
leer `data.geojson` con `file://`):

```bash
python3 -m http.server 8000
# luego abre:  http://localhost:8000/web/
```

El panel de filtros (izquierda) y el mapa (derecha) se actualizan en vivo. En el
móvil el panel se pliega tocando el botón **“Filtros ▾”**.

---

## 🗺️ Filtros disponibles (en la interfaz, en español)

- **Alquiler máximo** — slider 0–60.000, por defecto **¥40.000/mes**.
- **Operación** — Alquiler / Venta / Ambos.
- **Solo con parking** (`駐車場`) — con opción de incluir parking “cercano”.
- **Extranjero** — “Incluir desconocidos” o “Solo 外国人相談可”.
- **Distribución** (`間取り`) — multiselección (1K, 2DK, 3LDK…).
- **Antigüedad máxima** — slider de años.
- **Solo reformadas** (`リフォーム/リノベ済`).
- **Solo novedades** (casas vistas por primera vez en los últimos 14 días).
- **Zona** — un chip por municipio de `TARGET_AREAS`.
- **Búsqueda de texto libre.**

Los marcadores muestran el **precio**, se colorean de **verde (barato) a rojo
(caro)** y usan forma distinta para alquiler (cuadrado) y venta (redondeado). Al
pulsar uno se abre la ficha con foto, datos y **“Ver anuncio original”**.

---

## ✏️ Editar las zonas de búsqueda (`TARGET_AREAS`)

Abre **`config.py`** y edita la lista `TARGET_AREAS`. Cada municipio es un bloque:

```python
{"key": "shirahama", "ja": "白浜町", "es": "Shirahama",
 "pref": "和歌山県", "center": [33.6856, 135.3430]},
```

- `key`: identificador interno (sin espacios), lo usan los filtros.
- `ja`: nombre japonés EXACTO (se usa para clasificar y geocodificar).
- `es`: nombre que se muestra en la interfaz.
- `pref`: prefectura.
- `center`: `[lat, lng]` aproximado; ubicación de respaldo si una casa no se
  puede geocodificar con exactitud.

Para **añadir** un municipio copia un bloque y cambia los datos; para **quitarlo**,
bórralo. Si añades una etiqueta nueva, ponla también en `AREA_LABELS` dentro de
`web/index.html` para que se vea bonita (si no, se mostrará la `key`).

---

## 🔌 Añadir una fuente nueva

Cada fuente es un **archivo independiente** en `/sources`. Para añadir una:

1. Crea `sources/mi_fuente.py` con esta forma mínima:

   ```python
   from sources.base import Listing, assign_area

   SLUG = "mi_fuente"
   NAME = "Mi fuente bonita"

   def fetch(client):
       html = client.get("https://ejemplo.jp/casas")   # respeta robots + rate limit
       results = []
       # ... parsea y crea objetos Listing ...
       lst = Listing(source=SLUG, source_name=NAME,
                     source_url="https://ejemplo.jp/casa/1",
                     listing_type="sale", title="...", address_raw="兵庫県...")
       assign_area(lst)          # clasifica el municipio según TARGET_AREAS
       results.append(lst)
       return results
   ```

2. Regístrala en **`sources/registry.py`**:

   ```python
   from sources import mi_fuente
   ENABLED_SOURCES = { ..., mi_fuente.SLUG: mi_fuente }
   ```

`refresh.py` la recorrerá automáticamente, geocodificará y deduplicará por
`source_url`. El `HttpClient` ya se encarga de `robots.txt`, el rate limit, el
User-Agent y la caché: úsalo siempre con `client.get(url)`.

Los campos del objeto `Listing` (el esquema normalizado) están en
`sources/base.py`; hay helpers para parsear precios (`parse_price_yen`), áreas
(`parse_area_m2`), parking, antigüedad (`parse_year_built`), etc.

---

## 📥 Importar anuncios a mano (portales comerciales)

SUUMO, HOME'S 賃貸, アットホーム o こだて賃貸 **suelen prohibir el scraping** en sus
términos. Para esos casos **no** se raspan: se importan a mano.

1. Copia `sample_import.csv` a `imports/mis_casas.csv`.
2. Rellena una fila por casa (cabeceras en español; solo `url` y `tipo` son
   obligatorios). Varias fotos se separan con `|`.
3. Ejecuta `python3 refresh.py` — tus casas se mezclan con el resto y se
   geocodifican igual.

Puedes tener varios `imports/*.csv`; se leen todos.

---

## 🧭 Fuentes incluidas

| Slug                | Fuente                                          | Estado |
|---------------------|-------------------------------------------------|--------|
| `suminiko`          | 住みニコ — 南あわじ市 空き家バンク (público)         | ✅ activa (incluye 福良 y 沼島) |
| `sumonavi`          | 洲本移住ナビ — 洲本市 空き家バンク (público)         | ✅ activa |
| `wakayama_portal`   | わかやま住まいポータル — **toda Wakayama** (público) | ✅ activa (白浜/串本/那智勝浦/田辺/和歌山市) |
| `csv`               | Importación manual (CSV)                        | ✅ activa |
| `awaji_city`        | 淡路市 (web municipal)                            | ⚪ opcional (sin listado limpio; usa CSV) |
| `homes_akiyabank`   | LIFULL HOME'S 空き家バンク (agregador)              | ⚪ opcional (bloquea bots: solo enlaces/CSV) |

`wakayama_portal` cubre **todos los municipios de Wakayama** de `TARGET_AREAS`
con una sola fuente: pagina el listado de la prefectura, se queda solo con tus
zonas objetivo y solo entonces descarga la ficha completa (戸建て, descarta
マンション/アパート).

Las opcionales se activan moviéndolas de `OPTIONAL_SOURCES` a `ENABLED_SOURCES`
en `sources/registry.py`, o ejecutando `python3 refresh.py --all`. Nota: HOME'S
responde 403/202 a las peticiones automáticas, así que la dejamos desactivada
para respetar sus términos (usa enlaces o el importador CSV para esa fuente).

---

## 🤝 Geocodificación

1. **GSI / 国土地理院** (gratis, sin API key) como primera opción.
2. **Nominatim** (OpenStreetMap, máx. 1 req/s) como respaldo.
3. Si nada resuelve, la casa se centra en el municipio (`center` de
   `TARGET_AREAS`) y se marca como **“ubicación aproximada”** (no se descarta).

Todo se cachea en la tabla `geocode_cache`.

---

## ⚠️ Buenas prácticas (recordatorio)

Respeta `robots.txt` y los términos de cada sitio; limita la velocidad;
identifica el User-Agent; cachea; prioriza los bancos municipales (públicos) y
usa la importación manual para los portales comerciales que prohíben el scraping.
Es una herramienta de **uso personal**, sin redistribución de datos.
