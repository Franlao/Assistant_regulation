"""
Application multi-pages Assistant Réglementaire
Architecture moderne avec st.navigation() et authentification
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Chargements initiaux
load_dotenv()
os.environ['STREAMLIT_SERVER_TIMEOUT'] = '300'

# Imports des utilitaires et composants
from utils.session_utils import initialize_session_state, is_authenticated, is_admin
from components.auth_components import render_user_info, get_available_pages
from assistant_regulation.app.ui_styles import add_bg_from_local


def setup_page_config():
    """Configuration de base de l'application"""
    st.set_page_config(
        page_title="Assistant Réglementaire Automotive",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def render_sidebar():
    """Rendu de la barre latérale avec informations utilisateur et système"""
    
    with st.sidebar:
        # Logo
        if os.path.exists("assets/IVECO_BUS_Logo_RGB_Web.svg"):
            st.image("assets/IVECO_BUS_Logo_RGB_Web.svg", width=220)
        
        st.title("🚗 Assistant Réglementaire")
        
        # Informations utilisateur
        render_user_info()
        
        st.divider()
        
        # Informations système
        st.markdown("### 📊 État Système")
        
        # État de l'orchestrateur
        if st.session_state.get("orchestrator"):
            st.success("🟢 Orchestrateur actif")
            
            # Statistiques de conversation si disponibles
            try:
                if hasattr(st.session_state.orchestrator, 'get_conversation_stats'):
                    stats = st.session_state.orchestrator.get_conversation_stats()
                    if stats and stats.get("conversation_memory") != "disabled":
                        st.info(f"🧠 Mémoire: {stats.get('recent_turns', 0)} récents")
            except Exception:
                pass
        else:
            st.warning("🟡 Orchestrateur inactif")
        
        # État de l'authentification
        if is_authenticated():
            role_icon = "👑" if is_admin() else "👤"
            st.success(f"🔐 {role_icon} Authentifié")
        else:
            st.info("🔓 Accès public")
        
        # Statistiques de session
        messages_count = len(st.session_state.get("messages", []))
        if messages_count > 0:
            st.metric("Messages", messages_count)
        
        st.divider()
        
        # Informations sur les pages
        st.markdown("### 📱 Navigation")
        
        # Guide d'accès aux pages
        if not is_authenticated():
            st.info("💡 **Connectez-vous** pour accéder aux configurations")
        elif not is_admin():
            st.info("💡 **Accès administrateur** requis pour la gestion DB")
        else:
            st.success("✅ **Accès complet** - Toutes les fonctionnalités disponibles")
        
        # Footer
        st.divider()
        st.caption("🔧 Assistant Réglementaire v2.0")
        st.caption("💻 Architecture Multi-Pages")


def main():
    """Fonction principale de l'application"""
    
    # Configuration de la page
    setup_page_config()
    
    # Initialisation de l'état de session
    initialize_session_state()
    
    # Application du thème visuel
    try:
        if os.path.exists("assets/Image1.jpg"):
            add_bg_from_local("assets/Image1.jpg")
    except Exception as e:
        st.warning(f"Impossible de charger l'arrière-plan: {e}")
    
    # Rendu de la barre latérale
    render_sidebar()
    
    # Configuration de la navigation dynamique
    pages = get_available_pages()
    
    # Navigation principale avec st.navigation()
    pg = st.navigation(pages, position="hidden")  # Hidden car on gère via sidebar
    
    # Affichage du sélecteur de page dans la sidebar
    with st.sidebar:
        st.divider()
        st.markdown("### 🧭 Pages Disponibles")
        
        page_options = []
        page_mapping = {}
        
        for page in pages:
            display_name = f"{page.icon} {page.title}"
            page_options.append(display_name)
            page_mapping[display_name] = page
        
        # Sélecteur de page
        if "selected_page_index" not in st.session_state:
            st.session_state.selected_page_index = 0
        
        selected_page_name = st.selectbox(
            "Aller à la page:",
            page_options,
            index=st.session_state.selected_page_index,
            key="page_selector"
        )
        
        # Mise à jour de l'index sélectionné
        st.session_state.selected_page_index = page_options.index(selected_page_name)
        
        # Navigation vers la page sélectionnée
        selected_page = page_mapping[selected_page_name]
        
        # Informations sur la page actuelle
        st.markdown(f"**Page active:** {selected_page.title}")
        
        # Description des pages
        page_descriptions = {
            "💬 Chat": "Interface conversationnelle RAG",
            "⚙️ Configuration": "Paramètres LLM et RAG", 
            "🗃️ Database": "Gestion ChromaDB (Admin)"
        }
        
        if selected_page.title in page_descriptions:
            st.caption(page_descriptions[selected_page.title])
    
    # Exécution de la page sélectionnée
    try:
        # Navigation manuelle vers la page sélectionnée
        if selected_page.url_path == "pages/chat.py":
            from pages.chat import main as chat_main
            chat_main()
        elif selected_page.url_path == "pages/configuration.py":
            from pages.configuration import main as config_main
            config_main()
        elif selected_page.url_path == "pages/database.py":
            from pages.database import main as db_main
            db_main()
        else:
            st.error(f"Page inconnue: {selected_page.url_path}")
            
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()