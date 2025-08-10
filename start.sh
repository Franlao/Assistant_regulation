#!/bin/bash
# Script de démarrage pour Railway

echo "🚀 Démarrage de l'Assistant Réglementaire sur Railway..."

# Créer les dossiers nécessaires
mkdir -p logs Data joblib_cache .conversation_memory assets translations temp_uploads

# Vérifier les variables d'environnement essentielles
if [ -z "$PORT" ]; then
    export PORT=8501
    echo "⚠️  PORT non défini, utilisation du port par défaut: 8501"
fi

# Configuration Streamlit pour Railway
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

echo "📍 Configuration:"
echo "   - Port: $PORT"
echo "   - Mode: Production"
echo "   - Headless: true"

# Vérifier la santé de l'application
echo "🔍 Vérification de la configuration..."

# Test de l'import Python
python -c "
try:
    from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
    from config import get_config
    print('✅ Modules principaux importés avec succès')
except ImportError as e:
    print(f'❌ Erreur d\'import: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Échec de la vérification des imports"
    exit 1
fi

# Initialiser la configuration
echo "⚙️  Initialisation de la configuration..."
python -c "
from config import get_config
config = get_config()
print(f'✅ Configuration chargée: {config.app_name}')
"

# Démarrage de Streamlit
echo "🎯 Lancement de Streamlit sur 0.0.0.0:$PORT..."

exec streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --server.maxUploadSize=200 \
    --browser.gatherUsageStats=false \
    --global.developmentMode=false