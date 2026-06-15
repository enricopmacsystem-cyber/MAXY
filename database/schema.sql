-- Schema prodotti per Tech Distributor Assistant
-- PostgreSQL 14+

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internal_code   VARCHAR(50) NOT NULL UNIQUE,
    manufacturer    VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    category        VARCHAR(200) NOT NULL,
    availability    INTEGER NOT NULL DEFAULT 0 CHECK (availability >= 0),
    price           NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    cost_price      NUMERIC(12, 2) CHECK (cost_price >= 0),
    manual_url      TEXT,
    datasheet_url   TEXT,
    search_vector   TSVECTOR,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_internal_code
    ON products (internal_code);

CREATE INDEX IF NOT EXISTS idx_products_manufacturer
    ON products (manufacturer);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products (category);

CREATE INDEX IF NOT EXISTS idx_products_search_vector
    ON products USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_products_description_trgm
    ON products USING GIN (description gin_trgm_ops);

CREATE OR REPLACE FUNCTION products_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('italian', coalesce(NEW.internal_code, '')), 'A') ||
        setweight(to_tsvector('italian', coalesce(NEW.manufacturer, '')), 'B') ||
        setweight(to_tsvector('italian', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('italian', coalesce(NEW.category, '')), 'C');
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS products_search_vector_trigger ON products;

CREATE TRIGGER products_search_vector_trigger
BEFORE INSERT OR UPDATE ON products
FOR EACH ROW
EXECUTE PROCEDURE products_search_vector_update();

-- Compatibilità tra prodotti
CREATE TABLE IF NOT EXISTS product_compatibility (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    related_product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    compatibility_type  VARCHAR(30) NOT NULL CHECK (
        compatibility_type IN ('accessory', 'alternative', 'spare_part', 'complementary')
    ),
    notes               TEXT,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_product_compatibility UNIQUE (product_id, related_product_id, compatibility_type),
    CONSTRAINT chk_product_compatibility_distinct CHECK (product_id <> related_product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_compatibility_product_id
    ON product_compatibility (product_id);

CREATE INDEX IF NOT EXISTS idx_product_compatibility_related_product_id
    ON product_compatibility (related_product_id);

CREATE INDEX IF NOT EXISTS idx_product_compatibility_type
    ON product_compatibility (compatibility_type);

-- Storico ordini
CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number    VARCHAR(50) NOT NULL UNIQUE,
    order_date      DATE NOT NULL,
    customer_code   VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_customer_code ON orders (customer_code);

CREATE TABLE IF NOT EXISTS order_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity        NUMERIC(10, 2) NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(12, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_order_lines_order_product UNIQUE (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_order_lines_order_id ON order_lines (order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product_id ON order_lines (product_id);

CREATE TABLE IF NOT EXISTS product_order_stats (
    product_id          UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    order_count         INTEGER NOT NULL DEFAULT 0 CHECK (order_count >= 0),
    line_count          INTEGER NOT NULL DEFAULT 0 CHECK (line_count >= 0),
    total_quantity      NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (total_quantity >= 0),
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_cooccurrence (
    product_id              UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    related_product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    cooccurrence_count      INTEGER NOT NULL CHECK (cooccurrence_count > 0),
    correlation_percent     NUMERIC(5, 2) NOT NULL CHECK (
        correlation_percent > 0 AND correlation_percent <= 100
    ),
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (product_id, related_product_id),
    CONSTRAINT chk_product_cooccurrence_distinct CHECK (product_id <> related_product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_cooccurrence_product_id
    ON product_cooccurrence (product_id);

CREATE INDEX IF NOT EXISTS idx_product_cooccurrence_correlation
    ON product_cooccurrence (product_id, correlation_percent DESC);
