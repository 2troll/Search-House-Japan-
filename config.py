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
TARGET_AREAS = [
    # --- Wakayama (和歌山県) — costa sur ---
    {"key": "shirahama",    "ja": "白浜町",   "es": "Shirahama",     "pref": "和歌山県", "center": [33.6856, 135.3430]},
    {"key": "kushimoto",    "ja": "串本町",   "es": "Kushimoto",     "pref": "和歌山県", "center": [33.4719, 135.7757]},
    {"key": "nachikatsuura","ja": "那智勝浦町","es": "Nachikatsuura",  "pref": "和歌山県", "center": [33.6300, 135.9400]},
    {"key": "tanabe",       "ja": "田辺市",   "es": "Tanabe",        "pref": "和歌山県", "center": [33.7297, 135.3780]},
    {"key": "wakayama_shi", "ja": "和歌山市", "es": "Wakayama",      "pref": "和歌山県", "center": [34.2260, 135.1675]},

    # --- Hyogo / Awaji (兵庫県・淡路島) ---
    # 南あわじ市 incluye 福良 (Fukura) y la isla 沼島 (Nushima).
    {"key": "minamiawaji",  "ja": "南あわじ市","es": "Minami-Awaji",  "pref": "兵庫県",   "center": [34.2944, 134.7799]},
    {"key": "sumoto",       "ja": "洲本市",   "es": "Sumoto",        "pref": "兵庫県",   "center": [34.3429, 134.8954]},
    {"key": "awaji_shi",    "ja": "淡路市",   "es": "Awaji",         "pref": "兵庫県",   "center": [34.4439, 134.9150]},
]

# Mapa rápido  nombre japonés -> bloque de zona (lo usan los adaptadores).
AREAS_BY_JA = {a["ja"]: a for a in TARGET_AREAS}


def match_area(text):
    """Devuelve el bloque de TARGET_AREAS cuyo nombre japonés aparezca en `text`.

    Sirve para clasificar una casa en su municipio a partir de su dirección.
    Devuelve None si no coincide ninguna zona objetivo.
    """
    if not text:
        return None
    for a in TARGET_AREAS:
        if a["ja"] in text:
            return a
    return None


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
