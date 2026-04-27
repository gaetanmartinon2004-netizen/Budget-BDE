-- PostgreSQL Migration SQL - TEMPLATE
-- Generated for: budget_riptide_2025_26.db (Riptide 2025-26)

BEGIN TRANSACTION;

-- Mandate metadata
CREATE TABLE IF NOT EXISTS mandats (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Budget structure
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

-- Budget allocations
CREATE TABLE IF NOT EXISTS yearly_budgets (
    mandat_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    flow_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    PRIMARY KEY (mandat_id, year, flow_type),
    FOREIGN KEY (mandat_id) REFERENCES mandats(id)
);

-- Budget plans
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

-- Transactions
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

-- Justificatifs
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
-- IMPORT INSTRUCTIONS FOR RIPTIDE 2025-26
-- ============================================
-- 
-- This file contains the schema for the Riptide 2025-26 mandate
-- To import your existing data:
--
-- 1. Export from SQLite:
--    sqlite3 data/mandats/budget_riptide_2025_26.db ".dump" > riptide_export.sql
--
-- 2. Adapt the dump (replace AUTOINCREMENT with SERIAL)
--
-- 3. Import to PostgreSQL:
--    psql -d your_db -f budget_riptide_2025_26.sql
--
-- 4. Update sequences:
--    SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions));
