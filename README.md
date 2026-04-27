# BDE Trésorerie - Pilotage par Mandat

Application de gestion de trésorerie pour BDE (Bureau Des Étudiants) avec support multi-mandats et 3 vues principales.

**Version:** 2.0 | **Statut:** Production | **Dernière mise à jour:** Avril 2026

---

## 🚀 Démarrage Rapide (30 secondes)

### Windows
```powershell
.\run.bat
```

### Linux / macOS
```bash
python -m venv .venv
source .venv/bin/activate  # ou: .venv\Scripts\activate sur Windows Git Bash
pip install -r requirements.txt
python main.py
```

L'application se lance automatiquement dans votre navigateur par défaut.

---

## 📊 Fonctionnalités

### 📈 Vue Pilotage
- Comparaison **Prévisionnel vs Réel** par catégorie
- Affichage hiérarchique (Pôles > Catégories > Sous-catégories)
- Calcul automatique des écarts
- Indicateurs de performance (vert/orange/rouge)

### 💰 Vue Transactions
- Saisie de transactions avec classification
- Recherche et filtrage (date, type, catégorie, montant)
- Gestion des pièces jointes (justificatifs)
- Édition en ligne rapide (inline editing)
- Numéro d'ordre pour suivi comptable

### 🗂️ Vue Structure
- Gestion de l'arborescence des catégories
- Création/suppression de catégories
- Support de profondeur infinie
- Approche hiérarchique flexible

---

## 🏗️ Architecture Technique

### Structure du Projet
```
Budget BDE/
├── app/
│   ├── backend/
│   │   ├── api.py              # Routes Bottle (endpoints HTTP)
│   │   ├── database.py         # Schéma SQLite, migrations
│   │   ├── models.py           # Objets métier (Mandat, Transaction, etc.)
│   │   ├── services.py         # Logique métier
│   │   ├── justificatifs.py    # Gestion des fichiers attachés
│   │   └── paths.py            # Utilitaires chemins fichiers
│   └── frontend/
│       ├── static/
│       │   ├── css/style.css   # Styles (thème dark)
│       │   └── js/app.js       # Application client-side
│       └── templates/
│           ├── index.html       # Page accueil
│           ├── dashboard.html   # Vue Pilotage
│           ├── transactions.html # Vue Transactions
│           └── structure.html    # Vue Structure
├── main.py                      # Point d'entrée
├── requirements.txt             # Dépendances Python
├── run.bat / run.ps1           # Scripts de lancement
└── build.bat                    # Script de build/packaging
```

### Stack Technologique
- **Backend:** Python 3.12 + Bottle (micro-framework web)
- **Frontend:** HTML5 + CSS3 + JavaScript Vanilla
- **Base de Données:** SQLite (fichiers .db dans data/)
- **Packaging:** PyInstaller (pour distribution EXE)
- **UI Desktop:** pywebview (wrapper Electron-like)

### Architecture Base de Données
```sql
-- Mandats (périodes de gestion: ex: 2025-2026)
mandats(id, name, date_debut, date_fin, active, created_at)

-- Catégories hiérarchiques (arbre de budget)
budget_nodes(id, mandat_id, parent_id, name, created_at, deleted_at)
  UNIQUE(mandat_id, parent_id, name)

-- Prévisions budgétaires
budget_plans(id, mandat_id, node_id, year, flow_type, amount)
  flow_type ∈ {D=Dépense, R=Recette}

-- Transactions réelles
transactions(id, mandat_id, node_id, flow_type, amount, label, description, 
             date, payment_method, order_number, created_at, deleted_at)

-- Pièces jointes (justificatifs)
attachments(id, transaction_id, file_path, created_at, deleted_at)
```

### Bases de Données du Projet
- **data/mandats.db** - Métadonnées centrales (mandats actifs, mappings)
- **data/budget.db** - DB "legacy" (migration/backup)
- **data/mandats/*.db** - Une base par mandat (indépendante, complète)
- **Build EXE/mandats/*.db** - Copies packagées pour distribution

---

## 💻 Utilisation

### Gestion des Mandats
1. Un **mandat** représente une période (ex: 2025-2026)
2. Chaque mandat a sa propre structure de catégories et transactions
3. Sélectionner le mandat actif dans l'en-tête

### Créer un Budget Prévisionnel
1. Aller dans la **Vue Pilotage**
2. Cliquer sur une catégorie dans l'arbre
3. Entrer le montant prévu et le type (D/R)

### Enregistrer une Transaction
1. Aller dans la **Vue Transactions**
2. Cliquer **+ Nouvelle Transaction**
3. Remplir: libellé, montant, type, date, catégorie
4. Ajouter pièce jointe (optionnel)
5. Enregistrer

### Analyser les Écarts
1. Aller dans la **Vue Pilotage**
2. Sélectionner l'année à analyser
3. Observer les indicateurs par catégorie:
   - **Vert** = Sous-budget
   - **Orange** = Neutre
   - **Rouge** = Dépassement

---

## 🔌 API REST

### Mandats
```
GET  /api/mandats                      - Liste tous les mandats
GET  /api/mandat/active                - Mandat actuellement actif
POST /api/mandat                        - Créer un nouveau mandat
PUT  /api/mandat/<id>                  - Modifier un mandat
POST /api/mandat/active                - Définir le mandat actif
DELETE /api/mandat/<id>                - Supprimer un mandat
```

### Catégories/Structure
```
GET  /api/structure/<mandat_id>        - Arbre complet des catégories
POST /api/node                         - Créer une catégorie
DELETE /api/node/<mandat_id>/<node_id> - Supprimer une catégorie
```

### Transactions
```
GET  /api/transactions/<mandat_id>?filters     - Liste + filtres
POST /api/transaction                          - Créer
PUT  /api/transaction/<mandat_id>/<trans_id>  - Modifier
DELETE /api/transaction/<mandat_id>/<trans_id> - Supprimer
GET  /api/transaction/<mandat_id>/<trans_id>  - Détail
```

### Budgets & Dashboard
```
POST /api/budget-plan                  - Enregistrer prévision
GET  /api/dashboard/<mandat_id>?year=  - Analyse performance
```

---

## 📦 Dépendances

```
bottle==0.12.25      # Micro-framework web
pywebview==6.2.1     # Wrapper UI desktop
```

Aucune autre dépendance externe requise. SQLite est inclus.

---

## 🛠️ Build & Distribution

### Créer l'EXE (Windows)
```powershell
.\build.bat
```

Génère: `Build EXE/BDE Tresorerie.exe` + bases de données

### Distribuer
Copier le dossier `Build EXE/` complet sur les machines cibles. Tout est inclus (exe, .db, justificatifs/).

---

## 📋 Checklist Déploiement

- [ ] Python 3.12+ installé
- [ ] `pip install -r requirements.txt`
- [ ] `python main.py` se lance sans erreurs
- [ ] Les 3 vues (Pilotage, Transactions, Structure) chargent
- [ ] Créer/modifier/supprimer mandat fonctionne
- [ ] Transactions enregistrement/recherche OK
- [ ] EXE généré avec build.bat (si distribution Windows)

---

## 🔑 Points Clés de Conception

### Mandats Indépendants
Chaque mandat a sa propre base SQLite complète (nodes, plans, transactions). Aucun clonage auto entre mandats.

### Journal SQLite en DELETE
Utilise `PRAGMA journal_mode = DELETE` pour avoir un seul fichier .db par base (pas de .db-wal/.db-shm).

### Noms de Fichiers Normalisés
Fichiers mandat: `budget_<nom_slugifié>.db` (ex: `budget_mandat_2025_2026.db`)

### Soft Delete
Transactions et catégories utilisent `deleted_at` pour suppression logique (traçabilité).

### Hiérarchie Infinie
Les catégories peuvent être imbriquées à volonté (parent_id = None = racine).

---

## 📚 Fichiers de Configuration

- **requirements.txt** - Dépendances Python
- **build.bat** - Script PyInstaller (génère l'EXE)
- **run.bat / run.ps1** - Lanceurs (mode dev + desktop)

---

## 🐛 Troubleshooting

### "Port 8080 déjà en usage"
Bottle se rebind automatiquement sur 8081, 8082, etc.

### Base de données verrouillée
Fermer complètement l'application et relancer.

### Pièces jointes introuvables
Vérifier dossier `justificatifs/` et chemins fichiers en base.

---

## 📞 Support

Pour bugs ou questions, consulter:
- `ARCHITECTURE.md` - Concepts détaillés
- `QUICKREF.md` - Commandes & raccourcis
- Code source dans `app/`

---

## 📄 Historique

- **v2.0** (2026) - Restructuration complète, multi-mandats, UI modernisée
- **v1.0** (2025) - Première version, simple mandat, interface basique

**Dernière mise à jour:** 20 avril 2026
