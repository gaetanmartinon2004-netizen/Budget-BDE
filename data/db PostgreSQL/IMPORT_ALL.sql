-- IMPORT ALL DATABASES - Master Script
-- Usage: psql -U username -d database_name -f IMPORT_ALL.sql

-- Step 1: Import schemas
\i 'mandats.sql'
\i 'budget.sql'
\i 'budget_riptide_2025_26.sql'
\i 'budget_test.sql'

-- Step 2: Reset sequences to MAX(id)
SELECT setval('mandats_id_seq', COALESCE((SELECT MAX(id) FROM mandats), 1) + 1);
SELECT setval('budget_nodes_id_seq', COALESCE((SELECT MAX(id) FROM budget_nodes), 1) + 1);
SELECT setval('budget_plans_id_seq', COALESCE((SELECT MAX(id) FROM budget_plans), 1) + 1);
SELECT setval('transactions_id_seq', COALESCE((SELECT MAX(id) FROM transactions), 1) + 1);
SELECT setval('attachments_id_seq', COALESCE((SELECT MAX(id) FROM attachments), 1) + 1);

-- Done
\echo 'All tables created successfully!'
\echo 'Tables:'
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
