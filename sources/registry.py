# -*- coding: utf-8 -*-
"""
Registro de fuentes activas.

>>> AÑADIR UNA FUENTE = añadir una línea aquí. <<<
Cada valor es un módulo con una función  fetch(client) -> list[Listing].

- ENABLED_SOURCES: se ejecutan en cada refresh.py.
- OPTIONAL_SOURCES: existen pero están desactivadas (estructura por verificar,
  o agregadores comerciales). Muévelas a ENABLED_SOURCES cuando quieras usarlas.
"""

from sources import suminiko, sumonavi, csv_import, awaji_city, homes_akiyabank

# Fuentes que se extraen por defecto.
ENABLED_SOURCES = {
    suminiko.SLUG:   suminiko,    # 南あわじ市 (público) — Fase 1, verificado
    sumonavi.SLUG:   sumonavi,    # 洲本市 (público) — Fase 2
    csv_import.SLUG: csv_import,  # importación manual (SUUMO/HOME'S 賃貸/at-home...)
}

# Fuentes disponibles pero desactivadas (revisa su docstring antes de activar).
OPTIONAL_SOURCES = {
    awaji_city.SLUG:      awaji_city,       # web municipal de 淡路市 (estructura cambia)
    homes_akiyabank.SLUG: homes_akiyabank,  # agregador comercial (usar con criterio)
}

ALL_SOURCES = {**ENABLED_SOURCES, **OPTIONAL_SOURCES}
