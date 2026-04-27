# 📊 Guide Complet de Migration SQLite → PostgreSQL

## 🎯 Objectif
Migrer vos données SQLite existantes vers PostgreSQL (Supabase) pour le déploiement sur Render.com

## 📁 Fichiers Disponibles

```
data/db PostgreSQL/
├── README.md                      ← Guide d'import (ce fichier)
├── budget.sql                     ← Schéma principal
├── mandats.sql                    ← Registre des mandats
├── budget_riptide_2025_26.sql     ← Données Riptide 2025-26
├── budget_test.sql                ← Données TEST
└── IMPORT_ALL.sql                 ← Script d'import unifié
```

## 🔧 Méthodes d'Import

### ✅ Méthode 1 : Supabase Dashboard (Recommandé - le plus simple)

**Étapes :**

1. Aller sur [Supabase Dashboard](https://app.supabase.com)
2. Sélectionner votre projet
3. Aller à **SQL Editor** → **New Query**
4. Copier le contenu de `data/db PostgreSQL/IMPORT_ALL.sql`
5. Coller et cliquer **Run**

**Avantages :**
- Pas besoin d'installer d'outils
- Interface visuelle
- Feedback immédiat

---

### ✅ Méthode 2 : PostgreSQL CLI (psql)

**Prérequis :**
```bash
# Installer PostgreSQL (ou juste psql)
# macOS:
brew install postgresql

# Windows:
# https://www.postgresql.org/download/windows/

# Linux:
sudo apt install postgresql-client
```

**Étapes :**

```bash
# 1. Récupérer votre DATABASE_URL depuis Supabase
#    Dashboard → Settings → Database → Connection string
#    Copier l'URI type: postgresql://user:pass@host:5432/dbname

# 2. Exécuter le script d'import
psql "postgresql://user:password@db.project.supabase.co:5432/postgres" \
  -f data/db\ PostgreSQL/IMPORT_ALL.sql

# Ou importer fichier par fichier:
psql $DATABASE_URL -f data/db\ PostgreSQL/mandats.sql
psql $DATABASE_URL -f data/db\ PostgreSQL/budget.sql
psql $DATABASE_URL -f data/db\ PostgreSQL/budget_riptide_2025_26.sql
psql $DATABASE_URL -f data/db\ PostgreSQL/budget_test.sql
```

---

### ✅ Méthode 3 : pgAdmin (Interface Graphique)

1. Installer [pgAdmin](https://www.pgadmin.org/)
2. Se connecter à votre serveur PostgreSQL
3. Clic droit **Databases** → **Query Tool**
4. Copier-coller le contenu des fichiers .sql

---

### ✅ Méthode 4 : Importation des Données Existantes

Si vous avez des données dans les .db SQLite actuels:

```bash
# 1. Exporter de SQLite en CSV
sqlite3 data/mandats.db "SELECT * FROM mandats;" > /tmp/mandats.csv
sqlite3 data/budget.db "SELECT * FROM budget_nodes;" > /tmp/budget_nodes.csv

# 2. Importer en PostgreSQL
psql $DATABASE_URL -c "\COPY mandats FROM '/tmp/mandats.csv' CSV"
psql $DATABASE_URL -c "\COPY budget_nodes FROM '/tmp/budget_nodes.csv' CSV"

# 3. Resynchroniser les sequences
psql $DATABASE_URL -c "SELECT setval('mandats_id_seq', (SELECT MAX(id) FROM mandats) + 1);"
psql $DATABASE_URL -c "SELECT setval('budget_nodes_id_seq', (SELECT MAX(id) FROM budget_nodes) + 1);"
```

---

## ⚠️ Points Importants

### 1️⃣ Séquences (IDs auto-incréments)
Après l'import, **les séquences doivent être réinitialisées** :
```sql
-- Ceci est fait automatiquement dans IMPORT_ALL.sql
SELECT setval('mandats_id_seq', COALESCE((SELECT MAX(id) FROM mandats), 1) + 1);
SELECT setval('budget_nodes_id_seq', COALESCE((SELECT MAX(id) FROM budget_nodes), 1) + 1);
```

### 2️⃣ Conversions de Types
| SQLite | PostgreSQL |
|--------|-----------|
| INTEGER PRIMARY KEY AUTOINCREMENT | SERIAL PRIMARY KEY |
| REAL | NUMERIC |
| TEXT | TEXT |
| BLOB | BYTEA |

### 3️⃣ Clés Étrangères
Les clés étrangères sont conservées. Vérifier l'ordre d'import :
- ✅ **mandats.sql** en premier (tables maître)
- ✅ Puis **budget_*.sql** (qui référencent mandats)

---

## ✅ Vérifier que l'Import a Réussi

```sql
-- Lister toutes les tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Devrait retourner:
-- attachments
-- budget_nodes
-- budget_plans
-- mandat_db_files
-- mandats
-- transactions
-- yearly_budgets

-- Vérifier les données
SELECT COUNT(*) FROM mandats;
SELECT COUNT(*) FROM transactions;
SELECT COUNT(*) FROM budget_nodes;
```

---

## 🚀 Utilisation avec l'Application

Une fois importé sur PostgreSQL (Supabase), configurez votre app :

```bash
# 1. Configurer DATABASE_URL sur Render.com:
export DATABASE_URL="postgresql://user:pass@db.supabase.co:5432/postgres"

# 2. L'app détectera automatiquement le mode PostgreSQL
# via: if using_postgres(): get_connection()

# 3. Redémarrer l'app
# Les données seront disponibles
```

---

## 🔄 Migrer les Données Existantes (Avancé)

Si vos .db SQLite contiennent déjà des données :

### Option A : Export SQL Complet

```bash
# Exporter le dump complet SQLite
sqlite3 data/mandats.db ".dump" > /tmp/sqlite_dump.sql

# Adapter pour PostgreSQL:
# 1. Remplacer: AUTOINCREMENT → rien (SERIAL gère l'auto-incr)
# 2. Remplacer: ? → %s (dans les INSERT si multi-valeurs)
# 3. Remplacer: PRAGMA → supprimer (non supporté PG)

# Importer
psql $DATABASE_URL -f /tmp/sqlite_dump_adapted.sql
```

### Option B : Utilisez le Script Python

```bash
# Si vous avez Python 3 installé:
python export_db_simple.py

# Génère les fichiers SQL complètement adaptés
# dans data/db PostgreSQL/
```

---

## 🐛 Troubleshooting

### ❌ "Relation already exists"
```bash
# Videz les tables existantes
psql $DATABASE_URL -c "DROP TABLE IF EXISTS transactions, attachments, budget_plans, budget_nodes, yearly_budgets, mandat_db_files, mandats CASCADE;"

# Puis réimportez
psql $DATABASE_URL -f data/db\ PostgreSQL/IMPORT_ALL.sql
```

### ❌ "Permission denied"
- Vérifier que l'utilisateur PostgreSQL a les droits CREATE
- Supabase free tier : utiliser l'utilisateur `postgres` par défaut

### ❌ "Foreign key constraint failed"
- Vérifier l'ordre d'import (mandats d'abord)
- Ou désactiver temporairement les contraintes :
```sql
SET CONSTRAINTS ALL DEFERRED;
-- puis importer
-- puis
SET CONSTRAINTS ALL IMMEDIATE;
```

### ❌ "Sequence not found"
- Les séquences sont créées automatiquement par SERIAL
- Si erreur, recréer manuellement :
```sql
CREATE SEQUENCE mandats_id_seq;
ALTER TABLE mandats ALTER COLUMN id SET DEFAULT nextval('mandats_id_seq');
```

---

## 📞 Support

- **Supabase Docs** : https://supabase.com/docs/guides/database/import-data
- **PostgreSQL Docs** : https://www.postgresql.org/docs/current/sql-copy.html
- **Issues** : Ouvrir une issue sur le repo GitHub

---

**Status** : ✅ Prêt pour migration
