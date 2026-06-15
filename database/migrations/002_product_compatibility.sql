-- Compatibilità tra prodotti
-- Tipi: accessory, alternative, spare_part, complementary

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
