-- Esquema de la base de datos SQLite del buscador de casas.
-- Una fila = un anuncio normalizado. La clave para deduplicar es source_url.

CREATE TABLE IF NOT EXISTS listings (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source             TEXT,        -- slug de la fuente: "suminiko", "homes_akiyabank", "csv"...
    source_name        TEXT,        -- nombre legible de la fuente
    source_url         TEXT UNIQUE, -- url del anuncio original (clave de deduplicación)
    scraped_at         TEXT,
    first_seen         TEXT,
    last_seen          TEXT,
    active             INTEGER DEFAULT 1,  -- 1 si sigue apareciendo, 0 si desapareció

    listing_type       TEXT,        -- "rent" | "sale"
    prop_type          TEXT,        -- "house" | "apartment" | "land" | ""
    title              TEXT,

    prefecture         TEXT,
    city               TEXT,
    area_key           TEXT,        -- key de TARGET_AREAS (para filtrar por zona)
    address_raw        TEXT,
    lat                REAL,
    lng                REAL,
    geocode_source     TEXT,        -- "gsi" | "nominatim" | "city" | "manual"
    geocode_exact      INTEGER DEFAULT 1, -- 1 ubicación exacta, 0 centrada en el municipio

    rent_yen           INTEGER,     -- alquiler mensual (NULL si venta)
    management_fee_yen INTEGER,     -- 管理費・共益費
    deposit            TEXT,        -- 敷金
    key_money          TEXT,        -- 礼金
    sale_price_yen     INTEGER,     -- precio de venta (NULL si alquiler)

    layout             TEXT,        -- 間取り (3DK, 2LDK...)
    building_area_m2   REAL,        -- 建物面積 / 専有面積
    land_area_m2       REAL,        -- 土地面積
    year_built         TEXT,        -- 築年 (texto crudo)
    age_years          INTEGER,     -- antigüedad calculada en años (NULL si desconocido)
    structure          TEXT,        -- 木造 など
    floors             TEXT,

    parking            TEXT,        -- "yes" | "nearby" | "no" | "unknown"
    parking_detail     TEXT,
    foreigner_ok       TEXT,        -- "yes" | "negotiable" | "no" | "unknown"
    pet_ok             TEXT,        -- "yes" | "no" | "unknown"
    renovated          INTEGER DEFAULT 0,  -- 1/0 (リフォーム/リノベ済)

    photos             TEXT,        -- JSON: lista de urls
    description_raw    TEXT,
    features           TEXT,        -- JSON con extras
    status_note        TEXT,        -- 空室 / 商談中 など
    raw                TEXT         -- html/json crudo para depurar
);

CREATE INDEX IF NOT EXISTS idx_listings_active   ON listings(active);
CREATE INDEX IF NOT EXISTS idx_listings_type     ON listings(listing_type);
CREATE INDEX IF NOT EXISTS idx_listings_area     ON listings(area_key);

-- Caché de geocodificación: dirección -> coordenadas.
CREATE TABLE IF NOT EXISTS geocode_cache (
    address_raw TEXT PRIMARY KEY,
    lat         REAL,
    lng         REAL,
    source      TEXT
);
