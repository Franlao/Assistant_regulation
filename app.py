import streamlit as st
import os
from assistant_regulation.app.ui_styles import load_all_styles, add_bg_from_local
from assistant_regulation.app.sidebar_components import render_sidebar
from assistant_regulation.app.main_content import render_main_content

# Import des fonctions de configuration et database
from pages.configuration import (
    render_llm_configuration, render_rag_configuration, render_memory_configuration,
    render_ui_configuration, render_system_configuration
)
from pages.database import (
    render_database_status, render_pdf_ingestion, render_database_summary,
    render_regulation_search, render_regulations_list, render_database_cleanup
)
from pages.summary import main as render_summary_page
from utils.session_utils import initialize_session_state
from components.auth_components import require_authentication, require_admin_access
from translations import get_text
from config import get_config
from dotenv import load_dotenv

load_dotenv()
# Ajouter après l'import de streamlit
os.environ['STREAMLIT_SERVER_TIMEOUT'] = '300'

# Charger la configuration
config = get_config()

# Configuration de la page
st.set_page_config(
    page_title=config.app_name,
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des états de session pour la langue
if 'language' not in st.session_state:
    st.session_state.language = config.ui.default_language

# Fonction pour traduire du texte
def t(key: str, *args):
    """Obtenir le texte traduit selon la langue actuelle"""
    return get_text(key, st.session_state.language, *args)

# Le fond d'écran est appliqué uniquement pour la page Chat (voir plus bas)

# Initialisation des états de session
if 'messages' not in st.session_state:
    st.session_state.messages = []
    
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None

if 'session_id' not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())[:8]
    
if 'settings' not in st.session_state:
    st.session_state.settings = {
        "llm_provider": config.llm.default_provider,
        "model_name": config.get_default_model(config.llm.default_provider),
        "enable_verification": config.rag.enable_verification,
        "use_images": config.rag.use_images,
        "use_tables": config.rag.use_tables,
        "theme": config.ui.default_theme,
        "enable_conversation_memory": config.memory.enabled,
        "conversation_window_size": config.memory.window_size,
        "confidence_threshold": config.rag.confidence_threshold,
        "force_rag_keywords": ",".join(config.rag.force_rag_keywords)
    }

# Charger les styles CSS
load_all_styles()

# Ajouter le support MathJax pour les formules mathématiques
st.markdown("""
<script type="text/x-mathjax-config">
MathJax.Hub.Config({
  tex2jax: {inlineMath: [['$','$'], ['\\\\(','\\\\)']]}
});
</script>
<script type="text/javascript"
  src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML">
</script>
""", unsafe_allow_html=True)

# Initialiser les états de session supplémentaires
initialize_session_state()

def render_configuration_page(t, config):
    """Rendu de la page configuration intégrée"""
    # Vérifier l'authentification pour la configuration
    if not require_authentication():
        st.warning("🔐 Veuillez vous authentifier pour accéder à la configuration")
        return
    
    # En-tête avec le même style que l'app principale
    st.markdown("<h1 style='color: white;'>⚙️ Configuration</h1>", unsafe_allow_html=True)
    st.markdown("Configurez tous les paramètres de l'Assistant Réglementaire")
    
    # Navigation par onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🧠 LLM", 
        "🔍 RAG", 
        "🧠 Mémoire", 
        "🎨 Interface", 
        "⚙️ Système"
    ])
    
    with tab1:
        render_llm_configuration()
    
    with tab2:
        render_rag_configuration()
    
    with tab3:
        render_memory_configuration()
    
    with tab4:
        render_ui_configuration()
    
    with tab5:
        render_system_configuration()
    
    # Footer avec le même style
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.caption("<p style='color: white;'>💡 Les modifications sont appliquées automatiquement. Utilisez 'Sauvegarder Config' pour les rendre permanentes.</p>", unsafe_allow_html=True)

def render_database_page(t, config):
    """Rendu de la page database intégrée"""
    # Vérification admin obligatoire
    if not require_admin_access():
        st.warning("🔐 Accès administrateur requis pour gérer la base de données")
        return
    
    # En-tête avec le même style que l'app principale
    st.markdown("<h1 style='color: white;'>🗃️ Gestionnaire de Base de Données</h1>", unsafe_allow_html=True)
    st.markdown("**Interface d'administration ChromaDB** - Accès administrateur requis")
    
    # État de la base
    health = render_database_status()
    
    st.divider()
    
    # Navigation par onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📥 Ingestion",
        "📊 Résumé", 
        "🔍 Recherche",
        "📋 Liste",
        "🗑️ Nettoyage"
    ])
    
    with tab1:
        render_pdf_ingestion()
    
    with tab2:
        render_database_summary()
    
    with tab3:
        render_regulation_search()
    
    with tab4:
        render_regulations_list()
    
    with tab5:
        render_database_cleanup()
    
    # Footer avec le même style
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.caption("<p style='color: white;'>🔧 Interface d'administration - Utilisez avec précaution</p>", unsafe_allow_html=True)

# Barre latérale pour la configuration
with st.sidebar:
    st.session_state = render_sidebar(config, t, st.session_state)
    
    # Notifications des tâches asynchrones (optionnel)
    try:
        from components.task_monitor import render_task_notifications
        render_task_notifications()
    except ImportError:
        pass  # Composant optionnel

# --------------------------------------------------
# Gestion de l'arrière-plan selon la page
# --------------------------------------------------

if st.session_state.get("selected_page") == "💬 Chat":
    add_bg_from_local("assets/Image1.jpg")
else:
    # Arrière-plan blanc pour Configuration et Database
    st.markdown(
        """
        <style>
        .stApp {background: white !important;}
        [data-testid='stSidebarNav'] {display:none !important;}
        h1, h2, h3 {color:#000000 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Contenu principal basé sur la page sélectionnée
if st.session_state.selected_page == "💬 Chat":
    render_main_content(t, config)
    
elif st.session_state.selected_page == "📝 Summary":
    render_summary_page()
    
elif st.session_state.selected_page == "⚙️ Configuration":
    render_configuration_page(t, config)
    
elif st.session_state.selected_page == "🗃️ Database":
    render_database_page(t, config)

# Barre de statut pour les tâches asynchrones
try:
    from components.task_monitor import render_task_status_bar
    render_task_status_bar()
except ImportError:
    pass  # Composant optionnel