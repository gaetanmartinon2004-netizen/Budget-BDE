"""Database initialization and connection."""

import os
import psycopg2
from psycopg2 import sql


def initialize_database():
    """Initialize the database connection and schema."""
    print("[DB] initialize_database() called")
    
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        _initialize_postgres_database(database_url)
    else:
        print("[DB] DATABASE_URL not set, skipping PostgreSQL initialization")


def _initialize_postgres_database(database_url: str):
    """Initialize PostgreSQL database with schema."""
    print("[DB] Initializing PostgreSQL database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("[DB] Connected to PostgreSQL successfully")
        
        # Create tables
        _create_postgres_schema(cursor)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("[DB] ✅ Tables created successfully")
        
    except Exception as e:
        print(f"[DB] ⚠️  Could not initialize PostgreSQL at startup: {e}")
        print("[DB] Application will continue, but database operations may fail")
        # Don't raise - allow app to start anyway


def _create_postgres_schema(cursor):
    """Create all required PostgreSQL tables."""
    
    # Mandats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mandats (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            date_debut DATE,
            date_fin DATE,
            active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[DB] ✓ Table 'mandats' created/verified")
    
    # Budget nodes (hierarchical category structure)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_nodes (
            id SERIAL PRIMARY KEY,
            mandat_id INTEGER NOT NULL REFERENCES mandats(id) ON DELETE CASCADE,
            parent_id INTEGER REFERENCES budget_nodes(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            pole_color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            UNIQUE(mandat_id, parent_id, name)
        );
    """)
    print("[DB] ✓ Table 'budget_nodes' created/verified")
    
    # Budget plans (forecast)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_plans (
            id SERIAL PRIMARY KEY,
            mandat_id INTEGER NOT NULL REFERENCES mandats(id) ON DELETE CASCADE,
            node_id INTEGER NOT NULL REFERENCES budget_nodes(id) ON DELETE CASCADE,
            year INTEGER,
            flow_type CHAR(1),
            amount NUMERIC(12, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[DB] ✓ Table 'budget_plans' created/verified")
    
    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            mandat_id INTEGER NOT NULL REFERENCES mandats(id) ON DELETE CASCADE,
            node_id INTEGER NOT NULL REFERENCES budget_nodes(id) ON DELETE CASCADE,
            flow_type CHAR(1) NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            label TEXT NOT NULL,
            description TEXT,
            date DATE,
            payment_method TEXT,
            order_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[DB] ✓ Table 'transactions' created/verified")
    
    # Attachments table (for justificatifs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attachments (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            original_filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("[DB] ✓ Table 'attachments' created/verified")
