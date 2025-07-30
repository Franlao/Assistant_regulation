import streamlit as st
import os
import time
import pandas as pd
import json
import base64
import asyncio
from datetime import datetime
from assistant_regulation.planning.sync.orchestrator_2 import  SimpleOrchestrator
from assistant_regulation.app.ui_styles import load_all_styles, add_bg_from_local
from assistant_regulation.app.chat_generation import stream_assistant_response, display_message, get_current_time
from assistant_regulation.app.display_manager import display_sources, display_images, display_tables, display_regulation_metrics
from assistant_regulation.app.data_extraction import export_conversation_to_pdf, extract_table_from_text
from assistant_regulation.app.sidebar_components import render_sidebar
from assistant_regulation.app.main_content import render_main_content
from translations import get_text, AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE
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

# Appelez cette fonction au début de votre app (juste après set_page_config)
add_bg_from_local("assets/Image1.jpg")

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

# Barre latérale pour la configuration
with st.sidebar:
    st.session_state = render_sidebar(config, t, st.session_state)

# Contenu principal
render_main_content(t, config)