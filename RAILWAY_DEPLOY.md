# Guide de Déploiement Railway

Ce guide détaille le processus de déploiement de l'Assistant Réglementaire sur Railway.

## 🚀 Déploiement Rapide

### 1. Préparation du Projet

```bash
# Cloner le projet (si nécessaire)
git clone <votre-repo>
cd Assistant_regulation

# Vérifier que tous les fichiers de déploiement sont présents
ls -la Dockerfile railway.json .env.example start.sh
```

### 2. Configuration des Variables d'Environnement

Dans Railway Dashboard, configurez ces variables essentielles :

**Variables obligatoires :**
```
MISTRAL_API_KEY=votre_clé_mistral
SECRET_KEY=votre_clé_secrète_session
ADMIN_USERS=votre_email@example.com
```

**Variables recommandées :**
```
RAG_CONFIDENCE_THRESHOLD=0.7
CONVERSATION_MEMORY_ENABLED=true
LOG_LEVEL=INFO
ENABLE_CACHE=true
```

### 3. Déploiement

1. **Connecter le Repository :**
   - Allez sur railway.app
   - Créez un nouveau projet
   - Connectez votre repository GitHub

2. **Configuration Automatique :**
   - Railway détecte automatiquement le `railway.json`
   - Le build utilise le `Dockerfile`
   - Les volumes sont configurés automatiquement

3. **Variables d'Environnement :**
   - Ajoutez vos variables dans l'onglet "Variables"
   - Railway injecte automatiquement `$PORT`

4. **Déployment :**
   - Railway build et déploie automatiquement
   - L'application sera disponible sur votre domaine Railway

## ⚙️ Configuration Avancée

### Volumes Persistants

Les volumes sont configurés dans `railway.json` :

- `/app/Data` - Documents PDF
- `/app/logs` - Logs applicatifs  
- `/app/joblib_cache` - Cache de performance
- `/app/.conversation_memory` - Mémoire conversationnelle

### Variables d'Environnement Complètes

Copiez `.env.example` vers `.env` localement et configurez :

```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

Pour Railway, configurez dans le dashboard :

**LLM Configuration :**
- `MISTRAL_API_KEY` - Clé API Mistral (obligatoire)
- `MISTRAL_MODEL` - Modèle à utiliser (défaut: mistral-large-latest)

**Sécurité :**
- `SECRET_KEY` - Clé secrète pour sessions (générez une clé forte)
- `ADMIN_USERS` - Emails admin séparés par virgules

**RAG Configuration :**
- `RAG_CONFIDENCE_THRESHOLD` - Seuil de confiance (0.0-1.0)
- `RAG_USE_RERANKER` - Utiliser le reranker (true/false)
- `JINA_API_KEY` - Clé API Jina pour reranking (optionnel)

### Optimisation des Performances

**Cache Configuration :**
```
ENABLE_CACHE=true
CACHE_TTL=3600
JOBLIB_CACHE_DIR=./joblib_cache
```

**Mémoire Conversationnelle :**
```
CONVERSATION_MEMORY_ENABLED=true
CONVERSATION_WINDOW_SIZE=10
MEMORY_STORAGE_PATH=./.conversation_memory
```

## 🔧 Dépannage

### Problèmes Courants

**1. Build Failed - Dépendances manquantes :**
```bash
# Vérifier requirements.txt
pip install -r requirements.txt
```

**2. Port Binding Error :**
```bash
# Railway injecte automatiquement $PORT
# Assurez-vous que l'app écoute sur 0.0.0.0:$PORT
```

**3. Import Errors :**
```bash
# Vérifier la structure du projet
python -c "from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator"
```

**4. Volumes Non Persistants :**
- Les volumes sont configurés dans `railway.json`
- Railway les monte automatiquement
- Vérifiez les permissions dans le Dockerfile

### Logs et Monitoring

**Accès aux logs :**
```bash
# Dans Railway Dashboard
# Onglet "Deployments" > Sélectionner deployment > "View Logs"
```

**Health Check :**
```bash
# Railway ping automatiquement /_stcore/health
curl https://votre-app.railway.app/_stcore/health
```

### Performance

**Métriques importantes :**
- Temps de démarrage : ~2-3 minutes
- Mémoire RAM : ~1-2 GB
- CPU : Variable selon utilisation

**Optimisations :**
- Cache activé par défaut
- Lazy loading des modèles
- Compression des réponses Streamlit

## 💰 Coûts Estimés

**Railway Pro Plan (~$20/mois) :**
- 8 GB RAM, 8 vCPU
- 100 GB stockage
- Domaine custom inclus
- Support SSL automatique

**Variables selon usage :**
- API Mistral : ~$0.002-0.02 per 1K tokens
- Stockage additionnel : $0.10/GB/mois
- Trafic : Illimité sur Railway

## 🔄 CI/CD

### Auto-Deploy

Railway déploie automatiquement à chaque push sur `main` :

```yaml
# .github/workflows/railway-deploy.yml (optionnel)
name: Railway Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        uses: railway/railway@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
```

### Rollback

```bash
# Dans Railway Dashboard
# Onglet "Deployments" > Sélectionner version précédente > "Redeploy"
```

## 📞 Support

**Problèmes Railway :**
- Documentation : railway.app/docs
- Discord : railway.app/discord
- Support : railway.app/support

**Problèmes Application :**
- Vérifiez les logs Railway
- Testez localement avec Docker
- Vérifiez les variables d'environnement

---

🎯 **Checklist Pré-Déploiement :**

- [ ] Variables d'environnement configurées
- [ ] Clé API Mistral valide
- [ ] Repository connecté à Railway
- [ ] Tests locaux passés
- [ ] Dockerfile et railway.json présents
- [ ] Volumes configurés
- [ ] Domaine configuré (optionnel)