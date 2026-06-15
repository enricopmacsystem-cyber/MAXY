-- Indirizzo completo clienti per mappa e scheda contatto

ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS address_line VARCHAR(300);
ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20);
ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS province VARCHAR(50);
ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS country VARCHAR(80);
ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7);
ALTER TABLE customer_cache ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7);
