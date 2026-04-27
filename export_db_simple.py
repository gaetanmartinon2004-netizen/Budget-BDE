#!/usr/bin/env python3
"""
Minimal SQLite to PostgreSQL SQL converter
Uses only Python stdlib (sqlite3)
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def escape_identifier(name):
    """Échappe un identifiant SQL."""
    return f'"{name}"'

def escape_literal(value):
    """Échappe une valeur littérale SQL."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    # String
    s = str(value)
    return "'" + s.replace("'", "''") + "'"

def get_table_schemas(db_path):
    """Récupère les schémas des tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schemas = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        schemas[table] = cursor.fetchall()
    
    conn.close()
    return tables, schemas

def sqlite_to_postgres_type(sqlite_type):
    """Convertit SQLite type en PostgreSQL type."""
    if not sqlite_type:
        return "TEXT"
    
    t = sqlite_type.upper()
    if "INT" in t:
        return "INTEGER"
    elif "REAL" in t or "FLOA" in t:
        return "NUMERIC"
    elif "BLOB" in t:
        return "BYTEA"
    return "TEXT"

def convert_db(db_path, output_path):
    """Convertit une base SQLite en SQL PostgreSQL."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables, schemas = get_table_schemas(db_path)
    
    sql_lines = []
    sql_lines.append("-- PostgreSQL Migration Dump")
    sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
    sql_lines.append(f"-- Source: {db_path}")
    sql_lines.append("")
    sql_lines.append("BEGIN TRANSACTION;")
    sql_lines.append("")
    
    # Crée les tables
    for table_name in tables:
        columns = schemas[table_name]
        sql_lines.append(f"CREATE TABLE IF NOT EXISTS {escape_identifier(table_name)} (")
        
        col_defs = []
        for col in columns:
            col_id, col_name, col_type, notnull, dflt_value, pk = col
            
            pg_type = sqlite_to_postgres_type(col_type)
            
            if pk:
                col_def = f"  {escape_identifier(col_name)} SERIAL PRIMARY KEY"
            else:
                col_def = f"  {escape_identifier(col_name)} {pg_type}"
            
            col_defs.append(col_def)
        
        sql_lines.append(",\n".join(col_defs))
        sql_lines.append(");")
        sql_lines.append("")
    
    # Insère les données
    for table_name in tables:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            columns = [col[1] for col in schemas[table_name]]
            col_names = ", ".join([escape_identifier(c) for c in columns])
            
            for row in rows:
                values = ", ".join([escape_literal(v) for v in row])
                sql_lines.append(f"INSERT INTO {escape_identifier(table_name)} ({col_names}) VALUES ({values});")
    
    sql_lines.append("")
    sql_lines.append("COMMIT;")
    
    conn.close()
    
    # Écrit le fichier
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))
    
    print(f"✓ {output_path}")

def main():
    databases = [
        ("data/budget.db", "data/db PostgreSQL/budget.sql"),
        ("data/mandats.db", "data/db PostgreSQL/mandats.sql"),
        ("data/mandats/budget_riptide_2025_26.db", "data/db PostgreSQL/budget_riptide_2025_26.sql"),
        ("data/mandats/budget_test.db", "data/db PostgreSQL/budget_test.sql"),
    ]
    
    print("🔄 SQLite → PostgreSQL SQL Export\n")
    
    out_dir = Path("data/db PostgreSQL")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for db_path, sql_path in databases:
        if Path(db_path).exists():
            print(f"Processing: {db_path}")
            convert_db(db_path, sql_path)
        else:
            print(f"⚠️  Not found: {db_path}")
    
    print("\n✅ Export complete!")
    print(f"📁 Output: data/db PostgreSQL/")

if __name__ == "__main__":
    main()
