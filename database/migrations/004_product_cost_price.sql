-- Costo acquisto per calcolo margine (Commercial Copilot)

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS cost_price NUMERIC(12, 2) CHECK (cost_price >= 0);

CREATE INDEX IF NOT EXISTS idx_products_category_manufacturer
    ON products (category, manufacturer);
