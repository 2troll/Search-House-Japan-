# -*- coding: utf-8 -*-
"""
Registro de fuentes activas.

>>> AÑADIR UNA FUENTE = añadir una línea aquí. <<<
Cada valor es un módulo con una función  fetch(client) -> list[Listing].

- ENABLED_SOURCES: se ejecutan en cada refresh.py.
- OPTIONAL_SOURCES: existen pero están desactivadas (estructura por verificar,
  o agregadores comerciales). Muévelas a ENABLED_SOURCES cuando quieras usarlas.
"""

from sources import (suminiko, sumonavi, csv_import, awaji_city,
                     homes_akiyabank, wakayama_portal, athome_akiya, ur_chintai, suumo,
                     gaijinpot, athome_chintai)

# Fuentes que se extraen por defecto.
ENABLED_SOURCES = {
    athome_akiya.SLUG:    athome_akiya,    # agregador nacional: Nara, Kyoto, Osaka, Fukui, Hyogo, Wakayama
    ur_chintai.SLUG:      ur_chintai,      # APARTAMENTOS UR (público, admite extranjeros) en Kansai
    suumo.SLUG:           suumo,           # SUUMO 賃貸 (uso personal): apartamentos/casas de alquiler en Kansai
    gaijinpot.SLUG:       gaijinpot,       # GaijinPot/RealEstateJapan (INGLÉS, extranjeros) — alquiler Kansai
    suminiko.SLUG:        suminiko,        # 南あわじ市 (público) — Fase 1, verificado
    sumonavi.SLUG:        sumonavi,        # 洲本市 (público) — Fase 2
    wakayama_portal.SLUG: wakayama_portal, # toda Wakayama (白浜/串本/那智勝浦/田辺/和歌山市)
    athome_chintai.SLUG:  athome_chintai,  # at-home 賃貸: ALQUILERES Wakayama, Fukui y Awaji (otras agencias)
    csv_import.SLUG:      csv_import,       # importación manual (SUUMO/HOME'S 賃貸/at-home...)
}

# Fuentes disponibles pero desactivadas (revisa su docstring antes de activar).
OPTIONAL_SOURCES = {
    # 淡路市: su web municipal no expone un listado limpio (las fichas viven en
    # awaji-teijyu.jp sin estructura estable). De momento, mejor usar CSV para
    # casas concretas de 淡路市. Actívala solo si verificas la estructura.
    awaji_city.SLUG:      awaji_city,
    # homes_akiyabank bloquea las peticiones automáticas (HTTP 403/202): respeta
    # sus términos y usa solo los enlaces / la importación CSV para esa fuente.
    homes_akiyabank.SLUG: homes_akiyabank,  # agregador comercial (bloquea bots)
}

ALL_SOURCES = {**ENABLED_SOURCES, **OPTIONAL_SOURCES}
