"""
Utilitaires de gestion de session pour l'application multi-pages
"""

import streamlit as st
import uuid
from typing import Optional, Dict, Any

def initialize_session_state():
    """Initialise l'état de session global avec les valeurs par défaut"""
    
    # Configuration par défaut si pas encore chargée
    if 'config' not in st.session_state:
        try:
            from config import get_config
            st.session_state.config = get_config()
        except Exception as e:
            st.error(f"Erreur de chargement de la configuration: {e}")
            st.stop()
    
    config = st.session_state.config
    
    # États par défaut
    defaults = {
        # Authentification et utilisateur
        "authenticated": False,
        "user_role": None,  # 'admin', 'user', ou None
        "username": None,
        
        # Orchestrateur et services
        "orchestrator": None,
        "orchestrator_version": "modular_1.0",
        
        # Chat et conversation
        "messages": [],
        "session_id": str(uuid.uuid4())[:8],
        "current_conversation_id": None,
        
        # Configuration utilisateur
        "settings": {
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
        },
        
        # UI et langue
        "language": config.ui.default_language,
        "show_debug": False,
        
        # État des pages
        "current_page": "chat",
        "page_data": {}
    }
    
    # Initialiser les valeurs manquantes
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def get_or_create_orchestrator():
    """Obtient ou crée l'orchestrateur de manière thread-safe"""
    try:
        settings = st.session_state.settings
        current_version = st.session_state.get("orchestrator_version", "")
        expected_version = "modular_1.0"
        
        # Vérifier si l'orchestrateur doit être recréé
        needs_recreate = (
            st.session_state.orchestrator is None or
            current_version != expected_version or
            getattr(st.session_state.orchestrator, 'llm_provider', None) != settings["llm_provider"] or
            getattr(st.session_state.orchestrator, 'model_name', None) != settings["model_name"] or
            getattr(st.session_state.orchestrator, 'enable_verification', None) != settings["enable_verification"]
        )
        
        if needs_recreate:
            from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
            
            st.session_state.orchestrator = ModularOrchestrator(
                llm_provider=settings["llm_provider"],
                model_name=settings["model_name"],
                enable_verification=settings["enable_verification"]
            )
            
            # Marquer la version
            st.session_state.orchestrator._version = expected_version
            st.session_state.orchestrator_version = expected_version
            
            # Configurer la mémoire conversationnelle
            if (st.session_state.orchestrator.conversation_memory and 
                settings["enable_conversation_memory"]):
                st.session_state.orchestrator.conversation_memory.window_size = settings["conversation_window_size"]
        
        return st.session_state.orchestrator
        
    except Exception as e:
        st.error(f"Erreur lors de la création de l'orchestrateur: {e}")
        return None


def update_settings(new_settings: Dict[str, Any]):
    """Met à jour les paramètres de session"""
    if "settings" not in st.session_state:
        st.session_state.settings = {}
    
    st.session_state.settings.update(new_settings)
    
    # Marquer l'orchestrateur pour recréation si nécessaire
    orchestrator_settings = ["llm_provider", "model_name", "enable_verification"]
    if any(key in new_settings for key in orchestrator_settings):
        st.session_state.orchestrator = None


def get_user_role() -> Optional[str]:
    """Retourne le rôle de l'utilisateur actuel"""
    return st.session_state.get("user_role")


def is_authenticated() -> bool:
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get("authenticated", False)


def is_admin() -> bool:
    """Vérifie si l'utilisateur a des droits admin"""
    return st.session_state.get("user_role") == "admin"


def logout():
    """Déconnexion - nettoie l'état d'authentification"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None


def clear_chat_history():
    """Vide l'historique de chat et la mémoire"""
    st.session_state.messages = []
    
    # Effacer aussi la mémoire conversationnelle si elle existe
    if (st.session_state.orchestrator and 
        hasattr(st.session_state.orchestrator, 'clear_conversation_memory')):
        st.session_state.orchestrator.clear_conversation_memory()


def get_conversation_stats() -> Dict[str, Any]:
    """Retourne les statistiques de conversation"""
    stats = {
        "total_messages": len(st.session_state.messages),
        "conversation_memory": "disabled"
    }
    
    if (st.session_state.orchestrator and 
        hasattr(st.session_state.orchestrator, 'get_conversation_stats')):
        try:
            memory_stats = st.session_state.orchestrator.get_conversation_stats()
            if memory_stats:
                stats.update(memory_stats)
        except Exception:
            pass
    
    return stats


def get_page_data(page_name: str, key: str, default=None):
    """Récupère des données spécifiques à une page"""
    if "page_data" not in st.session_state:
        st.session_state.page_data = {}
    
    if page_name not in st.session_state.page_data:
        st.session_state.page_data[page_name] = {}
    
    return st.session_state.page_data[page_name].get(key, default)


def set_page_data(page_name: str, key: str, value):
    """Stocke des données spécifiques à une page"""
    if "page_data" not in st.session_state:
        st.session_state.page_data = {}
    
    if page_name not in st.session_state.page_data:
        st.session_state.page_data[page_name] = {}
    
    st.session_state.page_data[page_name][key] = value


def get_current_time():
    """Retourne l'horodatage actuel formaté"""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def reset_session_state():
    """Réinitialise complètement l'état de session"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    initialize_session_state()