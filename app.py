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
    render_regulation_search, render_regulations_list, render_database_cleanup,
    render_user_management
)
from pages.summary import main as render_summary_page
from pages.about import main as render_about_page
from utils.session_utils import initialize_session_state
from components.modern_auth_integration import require_modern_authentication, require_modern_admin_access, render_modern_sidebar_user_info, render_dedicated_login_page
from translations import get_text, t, _, init_i18n, add_language_selector
from config import get_config
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuration des logs d'optimisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-35s | %(levelname)-5s | %(message)s'
)

# Activer spécifiquement les logs d'optimisation
optimization_loggers = [
    'assistant_regulation.planning.services.retrieval_service',
    'assistant_regulation.planning.services.validation_service',
    'assistant_regulation.planning.sync.query_processor'
]

for logger_name in optimization_loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

print("Logs d'optimisation activés dans la console")

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

# Initialiser le système d'internationalisation moderne
i18n = init_i18n()

# Fonction pour traduire du texte (modernisée)
def t(key: str, *args, **kwargs):
    """Obtenir le texte traduit selon la langue actuelle"""
    # Utiliser le nouveau système moderne
    from translations import t as modern_t
    return modern_t(key, *args, **kwargs)

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

def load_page_specific_css(page_name):
    """Charge le CSS spécifique à une page"""
    css_file = f"pages/{page_name.lower()}_styles.css"
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def apply_page_specific_styles():
    """Applique les styles CSS conditionnels selon la page sélectionnée"""
    current_page = st.session_state.get("selected_page", "Chat")
    
    if current_page == "Summary":
        # CSS spécifique à la page Summary - Design épuré et moderne
        st.markdown("""
        <style>
        /* Background blanc épuré */
        .stApp {
            background: white !important;
        }
        
        /* Container principal avec design card moderne */
        .main .block-container {
            background: white !important;
            border-radius: 12px !important;
            padding: 2rem !important;
            margin: 1rem !important;
            max-width: none !important;
            box-shadow: 
                0.5px 1px 1px hsl(220 14% 56% / 0.07),
                1px 2px 2px hsl(220 14% 56% / 0.07),
                2px 4px 4px hsl(220 14% 56% / 0.07),
                4px 8px 8px hsl(220 14% 56% / 0.07) !important;
            border: 1px solid hsl(220 14% 94%) !important;
        }
        
        /* Titres élégants */
        .main h1 {
            color: #1e293b !important;
            text-align: center !important;
            font-weight: 600 !important;
            font-size: 2rem !important;
            margin-bottom: 2rem !important;
            padding-bottom: 1rem !important;
            border-bottom: 1px solid #e2e8f0 !important;
        }
        
        .main h2, .main h3 {
            color: #334155 !important;
            font-weight: 500 !important;
        }
        
        /* Boutons épurés avec ombres subtiles */
        .stButton > button {
            background: #475569 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.625rem 1rem !important;
            font-weight: 500 !important;
            font-size: 0.875rem !important;
            transition: all 0.15s ease !important;
            box-shadow: 
                0.5px 1px 1px hsl(220 14% 56% / 0.2),
                1px 2px 2px hsl(220 14% 56% / 0.2) !important;
        }
        
        .stButton > button:hover {
            background: #334155 !important;
            transform: translateY(-1px) !important;
            box-shadow: 
                1px 2px 2px hsl(220 14% 56% / 0.333),
                2px 4px 4px hsl(220 14% 56% / 0.333),
                3px 6px 6px hsl(220 14% 56% / 0.333) !important;
        }
        
        /* Selectbox moderne */
        .stSelectbox > div > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }

        .stSelectbox > div > div:focus-within {
            border: none !important;
            box-shadow: none !important;
        }
        
        /* Cards épurées avec ombres modernes */
        .main .element-container {
            background: white !important;
            border-radius: 10px !important;
            padding: 1.5rem !important;
            margin: 1rem 0 !important;
            border: 1px solid #f1f5f9 !important;
            box-shadow: 
                0.5px 1px 1px hsl(220 14% 56% / 0.05),
                1px 2px 2px hsl(220 14% 56% / 0.05) !important;
        }
        
        .main .element-container:hover {
            box-shadow: 
                1px 2px 2px hsl(220 14% 56% / 0.1),
                2px 4px 4px hsl(220 14% 56% / 0.1),
                4px 8px 8px hsl(220 14% 56% / 0.1) !important;
        }
        
        /* Tabs épurés */
        .stTabs [data-baseweb="tab-list"] {
            background: #f8fafc !important;
            border-radius: 10px !important;
            padding: 4px !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px !important;
            color: #64748b !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
            transition: all 0.15s ease !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: white !important;
            color: #1e293b !important;
            box-shadow: 
                0.5px 1px 1px hsl(220 14% 56% / 0.1),
                1px 2px 2px hsl(220 14% 56% / 0.1) !important;
        }
        
        /* Progress bar épuré */
        .stProgress > div > div {
            background: #475569 !important;
            border-radius: 6px !important;
        }
        
        .stProgress > div {
            background: #e2e8f0 !important;
            border-radius: 6px !important;
        }
        
        /* Expanders modernes */
        .stExpander {
            background: white !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
            box-shadow: 
                0.5px 1px 1px hsl(220 14% 56% / 0.05) !important;
        }
        
        .stExpander > div[role="button"] {
            color: #334155 !important;
            font-weight: 500 !important;
            padding: 1rem 1.5rem !important;
            border-bottom: 1px solid #f1f5f9 !important;
        }
        
        .stExpander > div[role="button"]:hover {
            background: #f8fafc !important;
        }
        </style>
        """, unsafe_allow_html=True)
        # Charger le fichier CSS externe si disponible
        load_page_specific_css("summary")
        
    elif current_page == "Configuration":
        # Pour Configuration, on charge uniquement le fichier CSS externe pour éviter les conflits
        load_page_specific_css("configuration")
        
    elif current_page == "Database":
        # Pour Database, on charge uniquement le fichier CSS externe pour éviter les conflits
        load_page_specific_css("database")

# Ajouter le support MathJax pour les formules mathématiques
st.markdown("""
<script type="text/x-mathjax-config">
MathJax.Hub.Config({
  tex2jax: {inlineMath: [['$','$'], ['\\\\(','\\\\)']],
           displayMath: [['$$','$$']],
           processEscapes: true},
  "HTML-CSS": {availableFonts: ["TeX"]},
  displayAlign: "center",
  displayIndent: "0em"
});

// Function to force MathJax to reprocess content
window.rerenderMathJax = function() {
  if (typeof MathJax !== 'undefined') {
    MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
  }
};

// Auto-reprocess MathJax every 2 seconds to catch new content
setInterval(function() {
  if (typeof MathJax !== 'undefined') {
    MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
  }
}, 2000);
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
    if not require_modern_authentication():
        return
    
    # Titre centré exactement comme Summary
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #343a40; font-weight: 400; font-size: 2rem; margin: 0;">{t('settings_title')}</h1>
        <p style="color: #6c757d; font-size: 1rem; margin: 0.5rem 0 0 0;">Configurez tous les paramètres de l'Assistant Réglementaire</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation par onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "LLM",
        "RAG",
        t('memory_configuration'),
        t('ui_configuration'),
        t('system_configuration')
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
    st.caption(t('config_auto_apply'))

def render_database_page(t, config):
    """Rendu de la page database intégrée"""
    # Vérification admin obligatoire
    if not require_modern_admin_access():
        return
    
    # Titre centré exactement comme Summary
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #343a40; font-weight: 400; font-size: 2rem; margin: 0;">{t('database_manager')}</h1>
        <p style="color: #6c757d; font-size: 1rem; margin: 0.5rem 0 0 0;">{t('database_admin_required')}</p>
    </div>
    """, unsafe_allow_html=True)
    # État de la base
    health = render_database_status()
    
    st.divider()
    
    # Navigation par onglets
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        t('ingestion'),
        t('summary'),
        t('search'),
        t('list'),
        t('cleanup'),
        "Utilisateurs"
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

    with tab6:
        render_user_management()
    
    # Footer avec le même style
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.caption(t('database_admin_warning'))

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
# Gestion de l'arrière-plan et styles selon la page
# --------------------------------------------------

if st.session_state.get("selected_page") == "Chat":
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

# Appliquer les styles spécifiques à chaque page
apply_page_specific_styles()

# Contenu principal basé sur la page sélectionnée
if st.session_state.selected_page == "Chat":
    render_main_content(t, config)

elif st.session_state.selected_page == "Summary":
    render_summary_page()

elif st.session_state.selected_page == "About":
    render_about_page()

elif st.session_state.selected_page == "Configuration":
    render_configuration_page(t, config)

elif st.session_state.selected_page == "Database":
    render_database_page(t, config)

elif st.session_state.selected_page == "Login":
    render_dedicated_login_page()

# Barre de statut pour les tâches asynchrones
try:
    from components.task_monitor import render_task_status_bar
    render_task_status_bar()
except ImportError:
    pass  # Composant optionnel