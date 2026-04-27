# 🚀 Guide de Déploiement - Budget BDE sur Render.com

## Prérequis
- Compte GitHub avec le repo pushé
- Compte [Render.com](https://render.com)
- Compte [Supabase](https://supabase.com) (PostgreSQL gratuit)

---

## Étape 1 : Configurer PostgreSQL sur Supabase

1. Créer un nouveau projet Supabase (free tier)
2. Dans **Settings → Database**, copier l'URL:
   ```
   postgresql://user:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

---

## Étape 2 : Configurer le Service Web sur Render.com

1. **Aller sur Render.com** → Dashboard → **New** → **Web Service**

2. **Connecter GitHub Repository**
   - Sélectionner votre repo `Budget-BDE`
   - Autoriser Render d'accéder à GitHub

3. **Paramètres du Service**
   - **Name**: `budget-bde` (ou votre nom)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`

4. **Environment Variables** (cliquer "Add Environment Variable")
   
   | Key | Value | Notes |
   |-----|-------|-------|
   | `DATABASE_URL` | `postgresql://user:pass@db...` | Depuis Supabase |
   | `SECRET_KEY` | `your-long-random-key-here` | Générer une clé aléatoire |
   | `PORT` | `5000` | Défaut (optionnel) |
   | `HOST` | `0.0.0.0` | Défaut (optionnel) |

5. **Instance Type**: Free ($0/mois) ou Paid ($7+/mois)

6. **Cliquer "Create Web Service"** → Render va builder et déployer automatiquement

---

## Étape 3 : Vérifier le Déploiement

- Après ~5 min, vous aurez une URL: `https://budget-bde.onrender.com`
- Consulter les **Logs** dans Render.com pour debug
- La base PostgreSQL sera initialisée automatiquement au premier lancement

---

## Étape 4 : Accéder à l'Application

- URL: `https://budget-bde.onrender.com`
- Partager avec vos collègues du BDE
- Aucune installation requise (accès direct via navigateur)

---

## Développement Local

### Avec SQLite (pas d'env var)
```bash
# Pas besoin de DATABASE_URL → utilise .db local
python main.py
```

### Avec PostgreSQL Local
```bash
# Définir DATABASE_URL
export DATABASE_URL="postgresql://user:pass@localhost:5432/budget_bde"
python main.py
```

---

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'psycopg2'"
- Render lance `pip install -r requirements.txt` automatiquement
- Attendre la fin du build (voir les logs)

### ❌ "psycopg2.OperationalError: could not connect to server"
- Vérifier que `DATABASE_URL` est correcte dans Render env vars
- Tester la connexion PostgreSQL depuis local: `psql $DATABASE_URL`

### ❌ "No such table: mandats"
- Les tables sont créées automatiquement au démarrage
- Attendre ~10-30 sec que l'app démarre complètement
- Rafraîchir la page

### ❌ "502 Bad Gateway"
- Consulter les **Logs** Render.com
- Vérifier les env vars ne contiennent pas d'erreur typo

---

## Maintenance

### Backup PostgreSQL Supabase
Aller dans **Supabase Dashboard → Backups** (auto-backups quotidiens en gratuit)

### Logs en Temps Réel
```bash
# Si vous avez SSH sur Render
render logs --follow budget-bde
```

### Redéployer après un commit
Render redéploie automatiquement avec chaque push sur la branche définie

---

## Coûts
- **Render Web Service**: Free ($0) ou Paid ($7+/mois)
- **Supabase PostgreSQL**: Free (5GB storage, shared instance)
- **Total**: $0 pour commencer, $7/mois pour une instance dédiée

---

**Besoin d'aide?**
- Docs Render: https://render.com/docs
- Docs Supabase: https://supabase.com/docs
- Issues GitHub: Créer une issue dans votre repo
