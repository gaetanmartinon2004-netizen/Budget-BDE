-- PostgreSQL Migration SQL - TEMPLATE
-- Generated for: mandats.db (Master Mandats Registry)

BEGIN TRANSACTION;

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

COMMIT;

-- ============================================
-- NOTE: mandats.db is the master registry
-- Actual budget data is in mandats/*.db files
-- ============================================
