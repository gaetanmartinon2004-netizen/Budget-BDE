#!/usr/bin/env python3
import re
from pathlib import Path

# Lire database.py et identifier les fonctions définies et appelées
db_file = Path('app/backend/database.py')
content = db_file.read_text()

# Trouver toutes les fonctions définies
funcs_defined = set(re.findall(r'^def\s+(\w+)', content, re.MULTILINE))
print(f"Total fonctions: {len(funcs_defined)}")

# Chercher les références croisées pour les sync functions
sync_funcs = [
    '_sync_all_mandat_databases',
    '_sync_single_mandat_database', 
    '_sync_mandat_db_from_source',
    '_build_node_path_indexes',
    '_normalize_key',
    '_ensure_node_path',
    '_find_child_node'
]

print("\nFonctions potentiellement mortes:")
for func in sync_funcs:
    count = content.count(f'{func}(')
    count_def = content.count(f'def {func}')
    if count_def > 0:
        print(f"  {func}: defined={count_def}, called={count}")
        if count == count_def:
            print(f"    ^ DEAD CODE (seulement la définition)")

# Identifier les templates qui ne sont pas routés
print("\nTemplates HTML:")
for tpl in Path('app/frontend/templates').glob('*.html'):
    print(f"  {tpl.name}")

print("\nRoutes existantes:")
api_file = Path('app/backend/api.py')
routes = re.findall(r'@app\.route\(["\']([^"\']+)', api_file.read_text())
for route in sorted(set(routes)):
    print(f"  {route}")
