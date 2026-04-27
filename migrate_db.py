#!/usr/bin/env python3
"""
Migration Script: SQLite → PostgreSQL
Exporte les données SQLite existantes en format SQL PostgreSQL
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

def escape_sql_value(val):
    """Échappe une valeur pour SQL."""
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return f"'{val.replace(chr(39), chr(39)+chr(39))}'"  # Échappe les quotes
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    return f"'{str(val)}'"


def get_sqlite_schema(db_path):
    """Extrait le schéma SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Récupère toutes les tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        schema[table] = columns
    
    conn.close()
    return schema, tables


def sqlite_to_postgres_schema(sqlite_type):
    """Convertit un type SQLite en type PostgreSQL."""
    type_upper = sqlite_type.upper()
    
    if "INT" in type_upper:
        return "INTEGER"
    elif "REAL" in type_upper or "FLOAT" in type_upper:
        return "NUMERIC"
    elif "TEXT" in type_upper:
        return "TEXT"
    elif "BLOB" in type_upper:
        return "BYTEA"
    return "TEXT"  # Par défaut


def convert_sqlite_to_postgres(db_path, output_sql_path):
    """Convertit une base SQLite en SQL PostgreSQL."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Récupère toutes les tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    sql_statements = []
    
    for table_name in tables:
        # Récupère la définition de la table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        
        # Construit CREATE TABLE pour PostgreSQL
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        col_defs = []
        
        for col in columns_info:
            col_name = col[1]
            col_type = col[2]
            is_pk = col[5]
            
            pg_type = sqlite_to_postgres_schema(col_type)
            
            # Gère les clés primaires
            if is_pk:
                col_def = f"  {col_name} SERIAL PRIMARY KEY"
            else:
                col_def = f"  {col_name} {pg_type}"
            
            col_defs.append(col_def)
        
        create_table_sql += ",\n".join(col_defs) + "\n);\n"
        sql_statements.append(create_table_sql)
        
        # Récupère les données
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            # Récupère les noms de colonnes
            col_names = [col[1] for col in columns_info]
            col_names_str = ", ".join(col_names)
            
            for row in rows:
                values_str = ", ".join([escape_sql_value(val) for val in row])
                insert_sql = f"INSERT INTO {table_name} ({col_names_str}) VALUES ({values_str});\n"
                sql_statements.append(insert_sql)
    
    conn.close()
    
    # Écrit dans le fichier de sortie
    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write("-- PostgreSQL Migration Dump\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- Migration from SQLite\n\n")
        f.write("BEGIN TRANSACTION;\n\n")
        f.writelines(sql_statements)
        f.write("\nCOMMIT;\n")
    
    print(f"✓ Exported: {output_sql_path}")


def main():
    # Bases SQLite à migrer
    databases = [
        ("data/budget.db", "data/db PostgreSQL/budget.sql"),
        ("data/mandats.db", "data/db PostgreSQL/mandats.sql"),
        ("data/mandats/budget_riptide_2025_26.db", "data/db PostgreSQL/budget_riptide_2025_26.sql"),
        ("data/mandats/budget_test.db", "data/db PostgreSQL/budget_test.sql"),
    ]
    
    # Crée le dossier de sortie
    output_dir = Path("data/db PostgreSQL")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔄 Migration SQLite → PostgreSQL SQL Dumps\n")
    
    for sqlite_path, sql_output_path in databases:
        if Path(sqlite_path).exists():
            print(f"Processing: {sqlite_path}")
            convert_sqlite_to_postgres(sqlite_path, sql_output_path)
        else:
            print(f"⚠ Not found: {sqlite_path}")
    
    # Crée un script de fusion pour importer toutes les données
    merge_script = "data/db PostgreSQL/IMPORT_ALL.sql"
    with open(merge_script, 'w', encoding='utf-8') as f:
        f.write("-- Import all databases to PostgreSQL\n")
        f.write("-- Usage: psql -U user -d database -a -f IMPORT_ALL.sql\n\n")
        for _, sql_output_path in databases:
            if Path(sql_output_path).exists():
                f.write(f"\\i '{sql_output_path}'\n")
    
    print(f"\n✓ Created: {merge_script}")
    print("\n✅ Migration complete!")
    print(f"\n📁 Output directory: data/db PostgreSQL/")
    print("\n📋 Usage:")
    print("  1. Edit data/db PostgreSQL/*.sql to verify")
    print("  2. On PostgreSQL: psql -U user -d dbname -f data/db\\ PostgreSQL/IMPORT_ALL.sql")
    print("  3. Or import each file individually")


if __name__ == "__main__":
    main()
