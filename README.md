# BDE Trésorerie - Pilotage par Mandat

Application de gestion de trésorerie pour BDE (Bureau Des Étudiants) avec support multi-mandats et 3 vues principales.

**Version:** 2.0 | **Statut:** Production | **Dernière mise à jour:** Avril 2026

---

## 🚀 Démarrage Rapide (30 secondes)

### Windows
`.powershell
.\run.bat
`

### Linux / macOS
`.bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
`

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
`
Budget BDE/
├── app/
│   ├── backend/
│   │   ├── api.py              # Routes Bottle (endpoints HTTP)
│   │   ├── database.py         # Schéma SQLite, migrations
│   │   ├── models.py           # Objets métier
│   │   ├── services.py         # Logique métier
│   │   ├── justificatifs.py    # Gestion fichiers
│   │   └── paths.py            # Utilitaires chemins
│   └── frontend/
│       ├── static/
│       │   ├── css/style.css   # Styles (thème dark)
│       │   └── js/app.js       # Application client
│       └── templates/ (4 vues HTML)
├── main.py                      # Point d'entrée
├── requirements.txt             # Dépendances
├── run.bat / run.ps1           # Lanceurs
└── build.bat                    # PyInstaller script
`

### Stack Technologique
- **Backend:** Python 3.12 + Bottle (WSGI)
- **Frontend:** HTML5 + CSS3 + JavaScript Vanilla
- **DB:** PostgreSQL (Render/Supabase) avec fallback SQLite en local
- **Serveur prod:** Gunicorn (Render)

### Base de Données
- **data/mandats.db** - Métadonnées mandats
- **data/mandats/*.db** - Une DB indépendante par mandat
- **Build EXE/mandats/*.db** - Copies packagées

---

## 💻 Utilisation

### Gestion des Mandats
1. Un **mandat** = une période (ex: 2025-2026)
2. Structure de catégories et transactions propres à chaque mandat
3. Sélectionner le mandat actif dans l'en-tête

### Enregistrer une Transaction
1. Vue Transactions → **+ Nouvelle Transaction**
2. Remplir: libellé, montant, type, date, catégorie
3. Ajouter pièce jointe (optionnel)
4. Enregistrer

### Analyser les Écarts
1. Vue Pilotage → Sélectionner année
2. Observer les indicateurs:
   - **Vert** = Sous-budget
   - **Orange** = Neutre
   - **Rouge** = Dépassement

---

## 🔌 API REST (points clés)

`
GET  /api/mandats
POST /api/mandat
GET  /api/structure/<mandat_id>
POST /api/transaction
GET  /api/transactions/<mandat_id>
GET  /api/dashboard/<mandat_id>
`

Voir code pp/backend/api.py pour documentation complète.

---

## 📦 Dépendances

`
bottle==0.12.25         # Micro-framework web
gunicorn==23.0.0        # Serveur WSGI production
psycopg2-binary==2.9.9  # Driver PostgreSQL
`

SQLite inclus nativement.

---

## 🛠️ Build & Distribution

### Créer l'EXE (Windows)
`.powershell
.\build.bat
`

Génère: Build EXE/BDE Tresorerie.exe + bases + justificatifs

### Distribuer
Copier le dossier Build EXE/ entier sur machines cibles.

---

## 🔑 Points Clés

- **Mandats indépendants** - Chaque mandat a sa propre DB complète
- **Soft delete** - Suppression logique via deleted_at
- **Hiérarchie infinie** - Catégories imbriquables à volonté
- **SQLite DELETE mode** - Un seul fichier .db par base

---

**Dernière mise à jour:** 20 avril 2026
