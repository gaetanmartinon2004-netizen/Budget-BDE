-- PostgreSQL Migration SQL - TEMPLATE
-- Generated for: budget.db
-- Instructions: 
--   1. Copy and adapt the schemas below for your mandats
--   2. Export your SQLite data as CSV and import to PostgreSQL
--   3. Or use: sqlite3 budget.db ".mode csv" then import

BEGIN TRANSACTION;

-- Main Budget Nodes
CREATE TABLE IF NOT EXISTS mandats (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mandat_db_files (
    mandat_id INTEGER PRIMARY KEY,
    db_filename TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (mandat_id) REFERENCES mandats(id)
);

CREATE TABLE IF NOT EXISTS budget_nodes (
    id SERIAL PRIMARY KEY,
    mandat_id INTEGER NOT NULL,
    parent_id INTEGER,
    name TEXT NOT NULL,
    pole_color TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (mandat_id) REFERENCES mandats(id),
    FOREIGN KEY (parent_id) REFERENCES budget_nodes(id),
    UNIQUE(mandat_id, parent_id, name)
);

CREATE TABLE IF NOT EXISTS yearly_budgets (
    mandat_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    flow_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    PRIMARY KEY (mandat_id, year, flow_type),
    FOREIGN KEY (mandat_id) REFERENCES mandats(id)
);

CREATE TABLE IF NOT EXISTS budget_plans (
    id SERIAL PRIMARY KEY,
    mandat_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    flow_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    FOREIGN KEY (mandat_id) REFERENCES mandats(id),
    FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    mandat_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    flow_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    label TEXT,
    description TEXT,
    date TEXT NOT NULL,
    payment_method TEXT,
    order_number TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (mandat_id) REFERENCES mandats(id),
    FOREIGN KEY (node_id) REFERENCES budget_nodes(id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

COMMIT;

-- ============================================
-- INSTRUCTIONS FOR DATA IMPORT
-- ============================================
--
-- If you have data in SQLite that needs to be migrated:
--
-- 1. Export from SQLite as CSV:
--    sqlite3 budget.db "SELECT * FROM mandats;" > mandats.csv
--
-- 2. Import to PostgreSQL:
--    COPY mandats FROM 'mandats.csv' (FORMAT CSV);
--
-- 3. Update sequences (important!):
--    SELECT setval('mandats_id_seq', (SELECT MAX(id) FROM mandats) + 1);
--    SELECT setval('budget_nodes_id_seq', (SELECT MAX(id) FROM budget_nodes) + 1);
--    SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions) + 1);
--    SELECT setval('attachments_id_seq', (SELECT MAX(id) FROM attachments) + 1);
--    SELECT setval('budget_plans_id_seq', (SELECT MAX(id) FROM budget_plans) + 1);
