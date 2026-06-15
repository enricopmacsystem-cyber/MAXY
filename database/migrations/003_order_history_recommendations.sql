-- Storico ordini e righe ordine

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number    VARCHAR(50) NOT NULL UNIQUE,
    order_date      DATE NOT NULL,
    customer_code   VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_order_date
    ON orders (order_date DESC);

CREATE INDEX IF NOT EXISTS idx_orders_customer_code
    ON orders (customer_code);

CREATE TABLE IF NOT EXISTS order_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity        NUMERIC(10, 2) NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(12, 2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_order_lines_order_product UNIQUE (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_order_lines_order_id
    ON order_lines (order_id);

CREATE INDEX IF NOT EXISTS idx_order_lines_product_id
    ON order_lines (product_id);

-- Statistiche frequenza acquisto (calcolate da ETL)
CREATE TABLE IF NOT EXISTS product_order_stats (
    product_id          UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    order_count         INTEGER NOT NULL DEFAULT 0 CHECK (order_count >= 0),
    line_count          INTEGER NOT NULL DEFAULT 0 CHECK (line_count >= 0),
    total_quantity      NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (total_quantity >= 0),
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Co-occorrenze e correlazione percentuale (calcolate da ETL)
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
