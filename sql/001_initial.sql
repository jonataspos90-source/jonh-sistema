-- John Sistemas • PostgreSQL 14+ • quantidades sempre em kg, L ou unidade.
BEGIN;
CREATE TABLE IF NOT EXISTS users (
 id BIGSERIAL PRIMARY KEY,
 name VARCHAR(120) NOT NULL,
 email VARCHAR(180) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role VARCHAR(12) NOT NULL DEFAULT 'operator' CHECK (role IN ('admin','operator','viewer')),
 active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS products (
 id BIGSERIAL PRIMARY KEY,
 name VARCHAR(180) NOT NULL,
 types TEXT[] NOT NULL CHECK (cardinality(types)>0 AND types <@ ARRAY['Produto Acabado','Revenda','Embalagem','Uso e Consumo','Subproduto','Insumo']::text[]),
 purchase_unit VARCHAR(15) NOT NULL DEFAULT 'pacote',
 package_qty NUMERIC(18,6) NOT NULL CHECK (package_qty>0),
 package_unit VARCHAR(3) NOT NULL CHECK (package_unit IN ('mg','g','kg','ml','l','un')),
 base_unit VARCHAR(2) NOT NULL CHECK (base_unit IN ('kg','l','un')),
 purchase_price NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (purchase_price>=0),
 fc NUMERIC(14,6) NOT NULL DEFAULT 1 CHECK (fc>=1),
 test_gross NUMERIC(18,6),
 test_net NUMERIC(18,6),
 CHECK ((test_gross IS NULL AND test_net IS NULL) OR (test_gross IS NOT NULL AND test_net IS NOT NULL AND test_gross>=test_net AND test_net>0)),
 min_stock NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (min_stock>=0),
 stock NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (stock>=0),
 avg_cost NUMERIC(20,8) NOT NULL DEFAULT 0 CHECK (avg_cost>=0),
 practiced_price NUMERIC(20,6),
 last_cost_at TIMESTAMPTZ,
 active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (practiced_price IS NULL OR practiced_price>=0)
);
CREATE TABLE IF NOT EXISTS recipes (
 id BIGSERIAL PRIMARY KEY,
 product_id BIGINT NOT NULL UNIQUE REFERENCES products(id) ON DELETE RESTRICT,
 yield_qty NUMERIC(20,6) NOT NULL CHECK (yield_qty>0),
 margin NUMERIC(9,4) NOT NULL DEFAULT 30 CHECK (margin>=0 AND margin<100),
 pricing_mode VARCHAR(8) NOT NULL DEFAULT 'margin' CHECK (pricing_mode IN ('margin','markup')),
 active BOOLEAN NOT NULL DEFAULT TRUE,
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS recipe_items (
 id BIGSERIAL PRIMARY KEY,
 recipe_id BIGINT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
 product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
 net_qty NUMERIC(20,6) NOT NULL CHECK (net_qty>0),
 UNIQUE(recipe_id,product_id)
);
CREATE TABLE IF NOT EXISTS stock_movements (
 id BIGSERIAL PRIMARY KEY,
 batch_id UUID NOT NULL,
 product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
 kind VARCHAR(20) NOT NULL CHECK (kind IN ('purchase','sale','internal','adjust','loss','production_in','production_out')),
 delta NUMERIC(20,6) NOT NULL CHECK (delta<>0),
 before_qty NUMERIC(20,6) NOT NULL,
 after_qty NUMERIC(20,6) NOT NULL CHECK (after_qty>=0),
 unit_cost NUMERIC(20,8) NOT NULL DEFAULT 0,
 value_amount NUMERIC(20,6) NOT NULL DEFAULT 0,
 reason TEXT,
 actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK (after_qty=before_qty+delta)
);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product ON stock_movements (product_id,created_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS idx_stock_movements_batch ON stock_movements (batch_id);
CREATE TABLE IF NOT EXISTS sales (
 id BIGSERIAL PRIMARY KEY,
 movement_id BIGINT UNIQUE REFERENCES stock_movements(id) ON DELETE RESTRICT,
 product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
 quantity NUMERIC(20,6) NOT NULL CHECK (quantity>0),
 unit_price NUMERIC(20,6) NOT NULL CHECK (unit_price>=0),
 revenue NUMERIC(20,6) NOT NULL,
 cost_total NUMERIC(20,6) NOT NULL,
 actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sales_created ON sales(created_at DESC);
COMMIT;
