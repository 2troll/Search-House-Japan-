# -*- coding: utf-8 -*-
"""
Configuración global del buscador de casas.

>>> ESTE ES EL ARCHIVO QUE MÁS VAS A TOCAR <<<
Aquí defines las zonas que te interesan (TARGET_AREAS) y los ajustes
de extracción (velocidad, User-Agent, etc.). Está todo comentado en español.
"""

import os

# --------------------------------------------------------------------------
# 1. ZONAS OBJETIVO  (LISTA EDITABLE)
# --------------------------------------------------------------------------
# Añade o quita municipios libremente. Cada entrada tiene:
#   - "key":   identificador interno corto (sin espacios), lo usan los filtros.
#   - "ja":    nombre japonés EXACTO del municipio (se usa para geocodificar
#              y para filtrar por "city").
#   - "es":    nombre legible en español/romaji (se muestra en la interfaz).
#   - "pref":  prefectura japonesa.
#   - "center": [lat, lng] aproximado del municipio. Se usa como ubicación
#              de respaldo cuando una casa no se puede geocodificar con exactitud.
#
# Para AÑADIR un municipio nuevo basta con copiar un bloque y cambiar los datos.
#
# Campos opcionales que usan algunos adaptadores:
#   - "match":     lista de subcadenas japonesas; la casa entra en la zona si su
#                  dirección contiene CUALQUIERA de ellas. Si no se pone, se usa "ja".
#   - "pref_code": código JIS de la prefectura (lo usa el adaptador at-home para
#                  saber qué prefectura raspar). Wakayama=30, Hyogo=28, Nara=29,
#                  Kyoto=26, Osaka=27, Fukui=18, Shiga=25.
TARGET_AREAS = [
    # --- Wakayama (和歌山県) — costa sur ---
    {"key": "shirahama",    "ja": "白浜町",   "es": "Shirahama",     "pref": "和歌山県", "pref_code": "30", "center": [33.6856, 135.3430]},
    {"key": "kushimoto",    "ja": "串本町",   "es": "Kushimoto",     "pref": "和歌山県", "pref_code": "30", "center": [33.4719, 135.7757]},
    {"key": "nachikatsuura","ja": "那智勝浦町","es": "Nachikatsuura",  "pref": "和歌山県", "pref_code": "30", "center": [33.6300, 135.9400]},
    {"key": "tanabe",       "ja": "田辺市",   "es": "Tanabe",        "pref": "和歌山県", "pref_code": "30", "center": [33.7297, 135.3780]},
    {"key": "wakayama_shi", "ja": "和歌山市", "es": "Wakayama",      "pref": "和歌山県", "pref_code": "30", "center": [34.2260, 135.1675]},

    # --- Hyogo / Awaji (兵庫県・淡路島) ---
    # 南あわじ市 incluye 福良 (Fukura) y la isla 沼島 (Nushima).
    {"key": "minamiawaji",  "ja": "南あわじ市","es": "Minami-Awaji",  "pref": "兵庫県",   "pref_code": "28", "center": [34.2944, 134.7799]},
    {"key": "sumoto",       "ja": "洲本市",   "es": "Sumoto",        "pref": "兵庫県",   "pref_code": "28", "center": [34.3429, 134.8954]},
    {"key": "awaji_shi",    "ja": "淡路市",   "es": "Awaji",         "pref": "兵庫県",   "pref_code": "28", "center": [34.4439, 134.9150]},

    # --- Nara (奈良県) — TODA la prefectura (zonas rurales) ---
    {"key": "nara", "es": "Nara (toda)", "pref": "奈良県", "pref_code": "29",
     "match": ["奈良県"], "center": [34.4880, 135.8048]},

    # --- Kyoto — TODA la prefectura (Kansai) ---
    {"key": "kyoto_north", "es": "Kyoto", "pref": "京都府", "pref_code": "26",
     "match": ["京都府"], "center": [35.1000, 135.5000]},

    # --- Osaka — TODA la prefectura (Kansai) ---
    {"key": "osaka_rural", "es": "Osaka", "pref": "大阪府", "pref_code": "27",
     "match": ["大阪府"], "center": [34.6900, 135.5200]},

    # --- Fukui — Obama y Wakasa (福井県 若狭) ---
    {"key": "fukui_obama", "es": "Obama / Wakasa", "pref": "福井県", "pref_code": "18",
     "match": ["小浜市", "若狭町", "おおい町", "高浜町", "美浜町", "大飯郡", "三方"],
     "center": [35.4955, 135.7463]},

    # --- Más zonas rurales (prefecturas enteras) ---
    {"key": "shiga",    "es": "Shiga (lago Biwa)", "pref": "滋賀県", "pref_code": "25",
     "match": ["滋賀県"], "center": [35.3292, 136.0570]},
    {"key": "mie",      "es": "Mie",               "pref": "三重県", "pref_code": "24",
     "match": ["三重県"], "center": [34.4900, 136.3000]},
    {"key": "okayama",  "es": "Okayama (rural)",   "pref": "岡山県", "pref_code": "33",
     "match": ["岡山県"], "center": [34.9000, 133.8000]},
    {"key": "tottori",  "es": "Tottori",           "pref": "鳥取県", "pref_code": "31",
     "match": ["鳥取県"], "center": [35.3600, 134.2000]},

    # --- Chugoku / Shikoku (más campo) ---
    {"key": "hiroshima", "es": "Hiroshima (rural)", "pref": "広島県", "pref_code": "34",
     "match": ["広島県"], "center": [34.5000, 132.8000]},
    {"key": "shimane",   "es": "Shimane",           "pref": "島根県", "pref_code": "32",
     "match": ["島根県"], "center": [35.2000, 132.7000]},
    {"key": "kagawa",    "es": "Kagawa (Shikoku)",  "pref": "香川県", "pref_code": "37",
     "match": ["香川県"], "center": [34.2000, 133.9000]},
    {"key": "tokushima", "es": "Tokushima (Shikoku)","pref": "徳島県", "pref_code": "36",
     "match": ["徳島県"], "center": [33.9000, 134.3000]},
    {"key": "ehime",     "es": "Ehime (Shikoku)",   "pref": "愛媛県", "pref_code": "38",
     "match": ["愛媛県"], "center": [33.7500, 132.9000]},
]

# Mapa rápido  nombre japonés -> bloque de zona (lo usan los adaptadores).
AREAS_BY_JA = {a.get("ja"): a for a in TARGET_AREAS if a.get("ja")}


def match_area(text):
    """Devuelve el bloque de TARGET_AREAS que coincida con `text` (una dirección).

    Usa la lista "match" si existe (cualquier subcadena), o el nombre "ja".
    Sirve para clasificar una casa en su zona a partir de su dirección.
    Devuelve None si no coincide ninguna zona objetivo.
    """
    if not text:
        return None
    for a in TARGET_AREAS:
        needles = a.get("match") or ([a["ja"]] if a.get("ja") else [])
        if any(n in text for n in needles):
            return a
    return None


# Lista única de códigos de prefectura a raspar en at-home (derivada de TARGET_AREAS).
PREF_CODES = sorted({a["pref_code"] for a in TARGET_AREAS if a.get("pref_code")})


# --------------------------------------------------------------------------
# 2. PREFERENCIAS DE BÚSQUEDA POR DEFECTO
# --------------------------------------------------------------------------
# Estos valores solo se usan como AYUDA / defaults de la interfaz; el filtrado
# real ocurre en el navegador (web/index.html). Cambiar aquí no afecta a la
# base de datos, solo documenta tu perfil.
DEFAULTS = {
    "max_rent_yen": 40000,      # alquiler máximo por defecto (¥/mes)
    "require_parking": True,    # exigir 駐車場
    "house_type_only": True,    # solo 戸建て (casa unifamiliar)
}

# --------------------------------------------------------------------------
# 3. AJUSTES DE EXTRACCIÓN (scraping responsable)
# --------------------------------------------------------------------------
# User-Agent descriptivo e identificable, como pide la buena práctica.
USER_AGENT = "akiya-personal-tool/1.0 (uso personal; +contacto: pagos.euros73@gmail.com)"

# Segundos mínimos entre peticiones AL MISMO dominio (mínimo recomendado 2-3 s).
REQUEST_DELAY_SECONDS = 3.0

# Reintentos suaves ante errores de red.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0

# Tiempo de espera por petición.
HTTP_TIMEOUT = 20

# Respetar robots.txt antes de raspar cualquier URL (True = recomendado).
RESPECT_ROBOTS = True

# --------------------------------------------------------------------------
# 4. RUTAS DE ARCHIVOS
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "listings.sqlite")
CACHE_DIR = os.path.join(BASE_DIR, "cache")        # caché HTTP en disco
GEOJSON_OUT = os.path.join(BASE_DIR, "web", "data.geojson")

# TTL de la caché HTTP en segundos (24 h). Evita repetir peticiones.
CACHE_TTL_SECONDS = 24 * 3600

# Máximo de páginas a recorrer por prefectura en at-home (60 anuncios/página).
# Súbelo para más cobertura (más lento). 25 páginas ≈ 1.500 casas por prefectura.
ATHOME_MAX_PAGES = 20
