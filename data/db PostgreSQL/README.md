# 🔄 Guide de Migration SQLite → PostgreSQL

## 📍 Bases de données trouvées

```
✓ data/budget.db (principale)
✓ data/mandats.db (master mandats)
✓ data/mandats/budget_riptide_2025_26.db (Riptide 2025-26)
✓ data/mandats/budget_test.db (TEST)
```

## ✅ Dossier de sortie créé

```
data/db PostgreSQL/
├── budget.sql
├── mandats.sql
├── budget_riptide_2025_26.sql
├── budget_test.sql
└── IMPORT_ALL.sql
```

## 🚀 Comment Importer vers PostgreSQL

### Option 1 : Via Supabase Dashboard (recommandé pour Render.com)

1. Aller sur https://supabase.com → Dashboard
2. Cliquer **SQL Editor** → **New Query**
3. Copier le contenu de `data/db PostgreSQL/budget.sql` 
4. Coller et cliquer **Run**
5. Répéter pour les autres fichiers SQL

### Option 2 : Via PostgreSQL CLI

```bash
# Importer une seule base
psql -U username -d database_name -h host -f "data/db PostgreSQL/budget.sql"

# Importer toutes les bases
psql -U username -d database_name -h host -f "data/db PostgreSQL/IMPORT_ALL.sql"
```

### Option 3 : Via pgAdmin (interface graphique)

1. Ouvrir pgAdmin
2. Clic droit sur Database → **Restore**
3. Sélectionner `budget.sql`
4. Exécuter

---

## 📝 Exemple de Migration Manuelle

Si vous voulez générer les fichiers SQL vous-même:

```python
# Ce script est dans migrate_db.py
python migrate_db.py
```

### Ou en PowerShell (manuel):

```powershell
# 1. Exporter schéma SQLite
sqlite3 data/budget.db ".schema" > data/db PostgreSQL/schema_export.txt

# 2. Exporter données
sqlite3 data/budget.db ".dump" > data/db PostgreSQL/dump_export.sql

# 3. Adapter pour PostgreSQL (remplacer AUTOINCREMENT par SERIAL)
```

---

## ⚠️ Points importants lors de l'import

1. **Séquences** : PostgreSQL n'accepte pas `AUTOINCREMENT`, utilise `SERIAL`
2. **Transactions** : Les fichiers SQL sont wrappés dans `BEGIN TRANSACTION` / `COMMIT`
3. **Types** : `REAL` → `NUMERIC`, `TEXT` reste `TEXT`
4. **Indices** : Recréés automatiquement
5. **Clés étrangères** : Préservées lors de la migration

---

## ✅ Vérifier que l'import a réussi

```sql
-- Sur PostgreSQL
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Devrait retourner:
-- mandats
-- budget_nodes
-- yearly_budgets
-- budget_plans
-- transactions
-- attachments
-- etc.
```

---

## 🔗 Ressources

- [PostgreSQL Import](https://www.postgresql.org/docs/current/sql-copy.html)
- [Supabase Import](https://supabase.com/docs/guides/database/import-data)
- [pgAdmin Restore](https://www.pgadmin.org/docs/)
