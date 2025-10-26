"""
Composants de la barre latérale pour l'application Streamlit
"""
import streamlit as st
from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
from config import save_config, reload_config
from assistant_regulation.app.streamlit_utils import export_conversation_to_pdf
from components.modern_auth_integration import render_modern_sidebar_user_info
from translations import t


def render_language_selector(config, t, current_language):
    """Affiche le sélecteur de langue ultrathink avec drapeaux emojis uniquement"""
    from translations import get_language, set_language

    # Drapeaux emojis avec 🇺🇸 pour l'anglais
    language_flags = {
        'fr': '🇫🇷',
        'en': '🇺🇸'
    }

    current_lang = get_language()

    # CSS pour style ultrathink footer
    st.markdown("""
    <style>
    .stSelectbox[data-baseweb="select"] {
        margin-top: -10px;
        margin-bottom: -10px;
    }
    .stSelectbox > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        min-height: 2rem !important;
    }
    .stSelectbox > div > div > div {
        background: transparent !important;
        border: none !important;
        font-size: 1.4em !important;
        padding: 0 !important;
        text-align: center !important;
    }
    .stSelectbox [data-baseweb="select"] {
        border: none !important;
        background: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Selectbox ultraminimaliste avec uniquement les drapeaux
    new_language = st.selectbox(
        label="Language",  # Label pour accessibilité
        options=list(language_flags.keys()),
        format_func=lambda x: language_flags[x],  # Afficher uniquement le drapeau
        index=list(language_flags.keys()).index(current_lang),
        key="footer_language_selector",  # Clé fixe pour détecter les changements
        help="Changer la langue / Change language",
        label_visibility="collapsed"  # Cacher le label
    )

    # Si la langue change, mettre à jour silencieusement
    if new_language != current_lang:
        set_language(new_language)
        st.session_state.language = new_language
        st.rerun()

    return get_language()


def render_llm_configuration(config, t, settings):
    """Affiche la configuration LLM"""
    with st.expander(t("llm_config"), expanded=False):

        current_provider = settings["llm_provider"]
        
        
        llm_provider = st.selectbox(
            t("llm_provider"),
            options=config.llm.available_providers,
            index=config.llm.available_providers.index(settings["llm_provider"]),
            key="llm_provider_select"
        )
        
        model_options = config.get_llm_models(llm_provider)
        current_model = settings["model_name"]
        model_index = 0
        if current_model in model_options:
            model_index = model_options.index(current_model)
        
        model_name = st.selectbox(
            t("model"),
            options=model_options,
            index=model_index,
            key="model_name_select"
        )
        
        return llm_provider, model_name


def render_search_options(t, settings):
    """Affiche les options de recherche"""
    with st.expander(t("search_options"), expanded=True):
        use_verification = st.toggle(
            t("verify_results"), 
            value=settings["enable_verification"],
            help="Active la vérification LLM des résultats (plus précis mais plus lent)",
            key="verification_toggle"
        )
        
        use_images = st.toggle(
            t("include_images"), 
            value=settings["use_images"],
            key="images_toggle"
        )
        
        use_tables = st.toggle(
            t("include_tables"), 
            value=settings["use_tables"],
            key="tables_toggle"
        )
        
        return use_verification, use_images, use_tables


def render_conversation_memory(config, settings, orchestrator):
    """Affiche la section mémoire conversationnelle"""
    with st.expander("Mémoire Conversationnelle", expanded=False):
        enable_memory = st.toggle(
            "Activer la mémoire conversationnelle", 
            value=settings["enable_conversation_memory"],
            help="Permet à l'assistant de se souvenir des échanges précédents",
            key="memory_toggle"
        )
        
        window_size = settings["conversation_window_size"]
        
        if enable_memory:
            window_size = st.slider(
                "Taille de la fenêtre mémoire", 
                min_value=3, max_value=15, 
                value=settings["conversation_window_size"],
                help=f"Nombre d'échanges récents à garder en mémoire active (recommandé: {config.memory.window_size})",
                key="memory_window_slider"
            )
            
            # Afficher les statistiques de mémoire si l'orchestrateur existe
            if orchestrator and hasattr(orchestrator, 'get_conversation_stats'):
                stats = orchestrator.get_conversation_stats()
                if stats and stats.get("conversation_memory") != "disabled":
                    st.write("**Statistiques de mémoire:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tours récents", stats.get('recent_turns', 0))
                    with col2:
                        st.metric("Résumés", stats.get('summaries_count', 0))
                    with col3:
                        st.metric("Total", stats.get('total_turns', 0))
                    
                    # Boutons d'action
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(t('clear_memory'), help="Effacer toute la mémoire conversationnelle", key="clear_memory_btn"):
                            if orchestrator:
                                orchestrator.clear_conversation_memory()
                                st.success(t('memory_cleared'))
                                st.rerun()
                    
                    with col2:
                        if st.button(t('export_conversation'), help="Exporter la conversation actuelle", key="export_conversation_btn"):
                            if orchestrator:
                                export_data = orchestrator.export_conversation()
                                st.json(export_data)
        
        return enable_memory, window_size



def render_configuration_management(config, settings):
    """Affiche la section gestion de configuration"""
    with st.expander("Gestion Configuration", expanded=False):
        st.write("**Configuration actuelle:**")
        st.write(f"- App: {config.app_name} v{config.version}")
        st.write(f"- Provider: {settings['llm_provider']}")
        st.write(f"- Modèle: {settings['model_name']}")
        st.write(f"- Mémoire: {'Oui' if settings['enable_conversation_memory'] else 'Non'}")
        
        col1, col2 = st.columns(2)
        
        save_clicked = False
        reload_clicked = False
        
        with col1:
            save_clicked = st.button(t('save_config'), help="Sauvegarder la configuration actuelle", key="save_config_btn")
        
        with col2:
            reload_clicked = st.button(t('reload_config'), help="Recharger depuis le fichier", key="reload_config_btn")
        
        if save_clicked:
            # Mettre à jour la config avec les settings actuels
            config.llm.default_provider = settings["llm_provider"]
            if settings["llm_provider"] == "ollama":
                config.llm.default_ollama_model = settings["model_name"]
            else:
                config.llm.default_mistral_model = settings["model_name"]
            
            config.rag.enable_verification = settings["enable_verification"]
            config.rag.use_images = settings["use_images"]
            config.rag.use_tables = settings["use_tables"]
            config.memory.enabled = settings["enable_conversation_memory"]
            config.memory.window_size = settings["conversation_window_size"]
            config.rag.confidence_threshold = settings["confidence_threshold"]
            config.rag.force_rag_keywords = settings["force_rag_keywords"].split(",")
            
            save_config()
            st.success(t('config_saved'))
        
        if reload_clicked:
            reload_config()
            st.success(t('config_reloaded'))
            st.rerun()


def initialize_or_update_orchestrator(settings, session_state, config):
    """Initialise ou met à jour l'orchestrateur si nécessaire"""
    llm_provider = settings["llm_provider"]
    model_name = settings["model_name"]
    use_verification = settings["enable_verification"]
    
    if (session_state.orchestrator is None or
        session_state.orchestrator.llm_provider != llm_provider or
        session_state.orchestrator.model_name != model_name or
        session_state.orchestrator.enable_verification != use_verification):
        
        with st.spinner("Configuration de l'assistant..."):
            try:
                session_state.orchestrator = ModularOrchestrator(
                    llm_provider=llm_provider,
                    model_name=model_name,
                    enable_verification=use_verification
                )
                
                # Configurer la taille de fenêtre si la mémoire est activée
                if (session_state.orchestrator.conversation_memory and 
                    settings["enable_conversation_memory"]):
                    session_state.orchestrator.conversation_memory.window_size = settings["conversation_window_size"]
                
                st.success(t('assistant_configured_success'))
                return True
            except Exception as e:
                st.error(f"Erreur de configuration: {str(e)}")
                return False
    return True


def render_sidebar(config, t, session_state):
    """Affiche l'ensemble de la barre latérale"""
    
    # Logo
    st.image("assets/IVECO_BUS_Logo_RGB_Web.svg", width=220)

    # ------------------- Profil utilisateur -------------------
    render_modern_sidebar_user_info()

    # ------------------- Navigation -------------------
    st.markdown(f"### {t('navigation')}")

    # Use translated page names for display
    page_translations = {
        "Chat": t('chat'),
        "Summary": t('summary'),
        "About": t('about'),
        "Configuration": t('configuration'),
        "Database": t('database'),
        "Login": t('login')
    }

    available_pages = ["Chat", "Summary", "About", "Configuration", "Database", "Login"]
    translated_page_names = [page_translations[page] for page in available_pages]

    # Initialiser la page sélectionnée
    if 'selected_page' not in session_state:
        session_state.selected_page = "Chat"

    # Find current page index for translated names
    current_page_index = available_pages.index(session_state.selected_page)

    selected_page_display = st.selectbox(
        t('goto_page'),
        translated_page_names,
        index=current_page_index,
        key="page_selector"
    )

    # Convert back to internal page name
    selected_page = available_pages[translated_page_names.index(selected_page_display)]

    if selected_page != session_state.selected_page:
        session_state.selected_page = selected_page
        st.rerun()

    page_descriptions = {
        "Chat": t('chat_description'),
        "Summary": t('summary_description'),
        "About": t('about_description'),
        "Configuration": t('configuration_description'),
        "Database": t('database_description'),
        "Login": t('login_description')
    }

    if selected_page in page_descriptions:
        st.caption(page_descriptions[selected_page])

    if selected_page == "Database":
        st.warning(t('admin_access_required'))

    st.divider()

    # Initialiser ou mettre à jour l'orchestrateur (aucun paramètre visible)
    initialize_or_update_orchestrator(session_state.settings, session_state, config)
    
    st.divider()
    
    # Boutons d'action
    if st.button(t("clear_history"), type="primary", key="clear_history_btn"):
        session_state.messages = []
        # Effacer aussi la mémoire conversationnelle si elle existe
        if session_state.orchestrator and hasattr(session_state.orchestrator, 'clear_conversation_memory'):
            session_state.orchestrator.clear_conversation_memory()
        st.rerun()
    
    # Export conversation
    if session_state.messages:
        export_conversation_to_pdf(session_state.messages)

    # ------------------- Sélecteur de langue (footer) -------------------
    st.markdown("<br>", unsafe_allow_html=True)
    current_language = session_state.get('language', config.ui.default_language)
    new_language = render_language_selector(config, t, current_language)
    if new_language != current_language:
        session_state.language = new_language

    st.caption(t("version"))
    st.caption(t("copyright"))

    return session_state 