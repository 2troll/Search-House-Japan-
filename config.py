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

    # --- Kobe / Hyogo (resto de 兵庫県, p. ej. apartamentos UR) ---
    {"key": "hyogo", "es": "Kobe / Hyogo", "pref": "兵庫県", "pref_code": "28",
     "match": ["兵庫県"], "center": [34.6900, 135.1950]},

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

    # --- Catch-all de prefectura entera (van al FINAL: las zonas-ciudad de arriba
    # tienen prioridad; lo que no encaje en ellas cae aquí). ---
    {"key": "wakayama", "es": "Wakayama (toda)", "pref": "和歌山県", "pref_code": "30",
     "match": ["和歌山県"], "center": [34.2306, 135.1708]},
    {"key": "fukui",    "es": "Fukui (toda)",    "pref": "福井県",   "pref_code": "18",
     "match": ["福井県"], "center": [36.0644, 136.2196]},

    # --- TODO JAPÓN: el resto de prefecturas (catch-all por prefectura) ---
    {"key": "tokyo",     "es": "Tokio",     "pref": "東京都",   "pref_code": "13", "match": ["東京都"],   "center": [35.6895, 139.6917]},
    {"key": "kanagawa",  "es": "Kanagawa",  "pref": "神奈川県", "pref_code": "14", "match": ["神奈川県"], "center": [35.4478, 139.6425]},
    {"key": "saitama",   "es": "Saitama",   "pref": "埼玉県",   "pref_code": "11", "match": ["埼玉県"],   "center": [35.8569, 139.6489]},
    {"key": "chiba",     "es": "Chiba",     "pref": "千葉県",   "pref_code": "12", "match": ["千葉県"],   "center": [35.6073, 140.1063]},
    {"key": "ibaraki",   "es": "Ibaraki",   "pref": "茨城県",   "pref_code": "08", "match": ["茨城県"],   "center": [36.3418, 140.4468]},
    {"key": "tochigi",   "es": "Tochigi",   "pref": "栃木県",   "pref_code": "09", "match": ["栃木県"],   "center": [36.5657, 139.8836]},
    {"key": "gunma",     "es": "Gunma",     "pref": "群馬県",   "pref_code": "10", "match": ["群馬県"],   "center": [36.3912, 139.0609]},
    {"key": "aichi",     "es": "Aichi (Nagoya)", "pref": "愛知県", "pref_code": "23", "match": ["愛知県"], "center": [35.1802, 136.9066]},
    {"key": "shizuoka",  "es": "Shizuoka",  "pref": "静岡県",   "pref_code": "22", "match": ["静岡県"],   "center": [34.9769, 138.3831]},
    {"key": "gifu",      "es": "Gifu",      "pref": "岐阜県",   "pref_code": "21", "match": ["岐阜県"],   "center": [35.3912, 136.7223]},
    {"key": "nagano",    "es": "Nagano",    "pref": "長野県",   "pref_code": "20", "match": ["長野県"],   "center": [36.6513, 138.1810]},
    {"key": "yamanashi", "es": "Yamanashi", "pref": "山梨県",   "pref_code": "19", "match": ["山梨県"],   "center": [35.6642, 138.5684]},
    {"key": "niigata",   "es": "Niigata",   "pref": "新潟県",   "pref_code": "15", "match": ["新潟県"],   "center": [37.9026, 139.0236]},
    {"key": "toyama",    "es": "Toyama",    "pref": "富山県",   "pref_code": "16", "match": ["富山県"],   "center": [36.6953, 137.2113]},
    {"key": "ishikawa",  "es": "Ishikawa (Kanazawa)", "pref": "石川県", "pref_code": "17", "match": ["石川県"], "center": [36.5947, 136.6256]},
    {"key": "yamaguchi", "es": "Yamaguchi", "pref": "山口県",   "pref_code": "35", "match": ["山口県"],   "center": [34.1859, 131.4714]},
    {"key": "kochi",     "es": "Kochi (Shikoku)", "pref": "高知県", "pref_code": "39", "match": ["高知県"], "center": [33.5597, 133.5311]},
    {"key": "fukuoka",   "es": "Fukuoka",   "pref": "福岡県",   "pref_code": "40", "match": ["福岡県"],   "center": [33.6064, 130.4181]},
    {"key": "saga",      "es": "Saga",      "pref": "佐賀県",   "pref_code": "41", "match": ["佐賀県"],   "center": [33.2494, 130.2988]},
    {"key": "nagasaki",  "es": "Nagasaki",  "pref": "長崎県",   "pref_code": "42", "match": ["長崎県"],   "center": [32.7448, 129.8737]},
    {"key": "kumamoto",  "es": "Kumamoto",  "pref": "熊本県",   "pref_code": "43", "match": ["熊本県"],   "center": [32.7898, 130.7417]},
    {"key": "oita",      "es": "Oita",      "pref": "大分県",   "pref_code": "44", "match": ["大分県"],   "center": [33.2382, 131.6126]},
    {"key": "miyazaki",  "es": "Miyazaki",  "pref": "宮崎県",   "pref_code": "45", "match": ["宮崎県"],   "center": [31.9111, 131.4239]},
    {"key": "kagoshima", "es": "Kagoshima", "pref": "鹿児島県", "pref_code": "46", "match": ["鹿児島県"], "center": [31.5602, 130.5581]},
    {"key": "okinawa",   "es": "Okinawa",   "pref": "沖縄県",   "pref_code": "47", "match": ["沖縄県"],   "center": [26.2124, 127.6809]},
    {"key": "fukushima", "es": "Fukushima", "pref": "福島県",   "pref_code": "07", "match": ["福島県"],   "center": [37.7503, 140.4676]},
    {"key": "yamagata",  "es": "Yamagata",  "pref": "山形県",   "pref_code": "06", "match": ["山形県"],   "center": [38.2404, 140.3633]},
    {"key": "miyagi",    "es": "Miyagi (Sendai)", "pref": "宮城県", "pref_code": "04", "match": ["宮城県"], "center": [38.2688, 140.8721]},
    {"key": "akita",     "es": "Akita",     "pref": "秋田県",   "pref_code": "05", "match": ["秋田県"],   "center": [39.7186, 140.1024]},
    {"key": "iwate",     "es": "Iwate",     "pref": "岩手県",   "pref_code": "03", "match": ["岩手県"],   "center": [39.7036, 141.1527]},
    {"key": "aomori",    "es": "Aomori",    "pref": "青森県",   "pref_code": "02", "match": ["青森県"],   "center": [40.8244, 140.7400]},
    {"key": "hokkaido",  "es": "Hokkaido",  "pref": "北海道",   "pref_code": "01", "match": ["北海道"],   "center": [43.0642, 141.3469]},
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
