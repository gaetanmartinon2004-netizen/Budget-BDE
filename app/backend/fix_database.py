#!/usr/bin/env python
import re

# Read the database.py file
with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: The _copy_rows call for budget_nodes to include pole_color
old1 = '            "SELECT id, mandat_id, parent_id, name, created_at, deleted_at FROM budget_nodes WHERE mandat_id = ? ORDER BY id",'
new1 = '            "SELECT id, mandat_id, parent_id, name, pole_color, created_at, deleted_at FROM budget_nodes WHERE mandat_id = ? ORDER BY id",'

if old1 in content:
    content = content.replace(old1, new1)
    print('✓ Fixed SELECT statement for budget_nodes copy')
else:
    print('✗ SELECT pattern not found')

# Fix 2: The INSERT statement 
old2 = '            "INSERT INTO budget_nodes (id, mandat_id, parent_id, name, created_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?)",'
new2 = '            "INSERT INTO budget_nodes (id, mandat_id, parent_id, name, pole_color, created_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",'

if old2 in content:
    content = content.replace(old2, new2)
    print('✓ Fixed INSERT statement for budget_nodes copy')
else:
    print('✗ INSERT pattern not found')

# Write the file back
with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nAll fixes applied successfully!')
