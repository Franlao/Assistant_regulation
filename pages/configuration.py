"""
Page Configuration - Paramètres LLM, RAG, et Mémoire
Regroupe toutes les configurations utilisateur
"""

import streamlit as st
from utils.session_utils import initialize_session_state, update_settings, get_or_create_orchestrator
from components.auth_components import require_authentication, render_change_password_form
from config import save_config, reload_config


def render_llm_configuration():
    """Configuration des modèles LLM"""
    st.subheader("🧠 Configuration des Modèles LLM")
    
    config = st.session_state.get("config")
    current_settings = st.session_state.get("settings", {})
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            # Sélection du provider
            llm_provider = st.selectbox(
                "🏢 Fournisseur LLM",
                options=config.llm.available_providers,
                index=config.llm.available_providers.index(current_settings.get("llm_provider", config.llm.default_provider)),
                help="Choisissez entre Ollama (local) ou Mistral AI (cloud)"
            )
        
        with col2:
            # Sélection du modèle
            model_options = config.get_llm_models(llm_provider)
            current_model = current_settings.get("model_name", "")
            
            try:
                model_index = model_options.index(current_model) if current_model in model_options else 0
            except (ValueError, IndexError):
                model_index = 0
            
            model_name = st.selectbox(
                "🎯 Modèle",
                options=model_options,
                index=model_index,
                help=f"Modèles disponibles pour {llm_provider}"
            )
        
        # Informations sur le provider sélectionné
        if llm_provider == "ollama":
            st.info("🏠 **Ollama (Local)** - Traitement sur votre machine, plus privé mais nécessite des ressources locales")
        else:
            st.info("☁️ **Mistral AI (Cloud)** - Traitement dans le cloud, plus rapide mais nécessite une connexion internet")
        
        # Tester la connexion
        if st.button("🔍 Tester la Connexion", type="secondary"):
            test_llm_connection(llm_provider, model_name)
        
        # Appliquer les changements
        if (llm_provider != current_settings.get("llm_provider") or 
            model_name != current_settings.get("model_name")):
            
            update_settings({
                "llm_provider": llm_provider,
                "model_name": model_name
            })
            st.success("✅ Configuration LLM mise à jour!")


def test_llm_connection(provider: str, model: str):
    """Teste la connexion au modèle LLM"""
    try:
        with st.spinner(f"Test de connexion à {provider}/{model}..."):
            # Créer un orchestrateur de test
            from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
            
            test_orchestrator = ModularOrchestrator(
                llm_provider=provider,
                model_name=model,
                enable_verification=False
            )
            
            # Test simple
            response = test_orchestrator.generation_service.generate_answer(
                "Dis bonjour en une phrase courte",
                context="",
                conversation_context=""
            )
            
            if response and len(response.strip()) > 0:
                st.success(f"✅ Connexion réussie! Réponse: '{response[:100]}...'")
            else:
                st.error("❌ Connexion échouée - Réponse vide")
                
    except Exception as e:
        st.error(f"❌ Erreur de connexion: {str(e)}")


def render_rag_configuration():
    """Configuration des paramètres RAG"""
    st.subheader("🔍 Configuration RAG (Recherche)")
    
    current_settings = st.session_state.get("settings", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 Options de Recherche**")
        
        # Vérification des résultats
        enable_verification = st.toggle(
            "🔎 Vérification LLM des résultats",
            value=current_settings.get("enable_verification", True),
            help="Active la validation des chunks par le LLM (plus précis mais plus lent)"
        )
        
        # Recherche multimodale
        use_images = st.toggle(
            "🖼️ Inclure les images",
            value=current_settings.get("use_images", True),
            help="Recherche dans les diagrammes et figures des documents"
        )
        
        use_tables = st.toggle(
            "📊 Inclure les tableaux",
            value=current_settings.get("use_tables", True),
            help="Recherche dans les tableaux et données structurées"
        )
    
    with col2:
        st.markdown("**⚙️ Paramètres Avancés**")
        
        # Seuil de confiance
        confidence_threshold = st.slider(
            "🎚️ Seuil de confiance",
            min_value=0.0,
            max_value=1.0,
            value=current_settings.get("confidence_threshold", 0.7),
            step=0.1,
            help="Seuil minimum de confiance pour les résultats de recherche"
        )
        
        # Mots-clés forçant RAG
        force_rag_keywords = st.text_input(
            "🔑 Mots-clés forçant RAG",
            value=current_settings.get("force_rag_keywords", ""),
            help="Mots-clés séparés par des virgules qui forcent l'utilisation de RAG"
        )
    
    # Prévisualisation des paramètres
    with st.expander("👁️ Prévisualisation des Paramètres", expanded=False):
        st.json({
            "verification": enable_verification,
            "multimodal": {"images": use_images, "tables": use_tables},
            "confidence_threshold": confidence_threshold,
            "force_rag_keywords": force_rag_keywords.split(",") if force_rag_keywords else []
        })
    
    # Appliquer les changements
    new_settings = {
        "enable_verification": enable_verification,
        "use_images": use_images,
        "use_tables": use_tables,
        "confidence_threshold": confidence_threshold,
        "force_rag_keywords": force_rag_keywords
    }
    
    if any(new_settings[key] != current_settings.get(key) for key in new_settings):
        update_settings(new_settings)
        st.success("✅ Configuration RAG mise à jour!")


def render_memory_configuration():
    """Configuration de la mémoire conversationnelle"""
    st.subheader("🧠 Mémoire Conversationnelle")
    
    current_settings = st.session_state.get("settings", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔧 Paramètres de Mémoire**")
        
        # Activation de la mémoire
        enable_memory = st.toggle(
            "🧠 Activer la mémoire conversationnelle",
            value=current_settings.get("enable_conversation_memory", True),
            help="Permet à l'assistant de se souvenir des échanges précédents"
        )
        
        if enable_memory:
            # Taille de la fenêtre
            window_size = st.slider(
                "📏 Taille de fenêtre mémoire",
                min_value=3,
                max_value=20,
                value=current_settings.get("conversation_window_size", 10),
                help="Nombre d'échanges récents gardés en mémoire active"
            )
        else:
            window_size = current_settings.get("conversation_window_size", 10)
    
    with col2:
        st.markdown("**📊 Statistiques de Mémoire**")
        
        # Afficher les statistiques si l'orchestrateur existe
        orchestrator = st.session_state.get("orchestrator")
        if orchestrator and hasattr(orchestrator, 'get_conversation_stats'):
            try:
                stats = orchestrator.get_conversation_stats()
                if stats and stats.get("conversation_memory") != "disabled":
                    col2a, col2b = st.columns(2)
                    
                    with col2a:
                        st.metric("Tours récents", stats.get('recent_turns', 0))
                        st.metric("Total tours", stats.get('total_turns', 0))
                    
                    with col2b:
                        st.metric("Résumés", stats.get('summaries_count', 0))
                        st.metric("Fenêtre", stats.get('window_size', 0))
                else:
                    st.info("💭 Mémoire inactive")
            except Exception:
                st.warning("⚠️ Impossible de récupérer les statistiques")
        else:
            st.info("🔄 Orchestrateur non initialisé")
        
        # Actions sur la mémoire
        st.markdown("**🎛️ Actions**")
        
        col2a, col2b = st.columns(2)
        with col2a:
            if st.button("🧹 Effacer Mémoire", help="Vider toute la mémoire conversationnelle"):
                if orchestrator:
                    try:
                        orchestrator.clear_conversation_memory()
                        st.success("✅ Mémoire effacée!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur: {e}")
                else:
                    st.warning("⚠️ Orchestrateur non disponible")
        
        with col2b:
            if st.button("📊 Exporter", help="Exporter la conversation actuelle"):
                export_conversation()
    
    # Informations sur la mémoire
    if enable_memory:
        st.info(f"""
        💡 **Comment fonctionne la mémoire :**
        - **Fenêtre active** : {window_size} derniers échanges gardés en mémoire
        - **Résumés automatiques** : Les anciens échanges sont résumés pour économiser la mémoire
        - **Contexte intelligent** : L'assistant comprend vos références aux conversations précédentes
        """)
    else:
        st.warning("⚠️ **Mémoire désactivée** - L'assistant ne se souviendra pas des échanges précédents")
    
    # Appliquer les changements
    if (enable_memory != current_settings.get("enable_conversation_memory") or
        window_size != current_settings.get("conversation_window_size")):
        
        update_settings({
            "enable_conversation_memory": enable_memory,
            "conversation_window_size": window_size
        })
        st.success("✅ Configuration mémoire mise à jour!")


def export_conversation():
    """Exporte la conversation actuelle"""
    try:
        orchestrator = st.session_state.get("orchestrator")
        if orchestrator and hasattr(orchestrator, 'export_conversation'):
            export_data = orchestrator.export_conversation()
            st.json(export_data)
        else:
            # Export simple des messages de session
            messages = st.session_state.get("messages", [])
            if messages:
                st.json({"messages": messages, "exported_at": st.session_state.get("session_id")})
            else:
                st.info("💭 Aucune conversation à exporter")
    except Exception as e:
        st.error(f"❌ Erreur d'export: {e}")


def render_ui_configuration():
    """Configuration de l'interface utilisateur"""
    st.subheader("🎨 Interface Utilisateur")
    
    config = st.session_state.get("config")
    current_language = st.session_state.get("language", "fr")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌐 Langue**")
        
        # Sélecteur de langue
        new_language = st.selectbox(
            "Langue de l'interface",
            options=config.ui.available_languages,
            index=config.ui.available_languages.index(current_language),
            format_func=lambda x: "🇫🇷 Français" if x == "fr" else "🇬🇧 English"
        )
        
        if new_language != current_language:
            st.session_state.language = new_language
            st.success(f"✅ Langue changée pour: {'Français' if new_language == 'fr' else 'English'}")
            st.rerun()
    
    with col2:
        st.markdown("**🛠️ Debug**")
        
        # Mode debug
        show_debug = st.toggle(
            "🔍 Mode Debug",
            value=st.session_state.get("show_debug", False),
            help="Affiche des informations de débogage détaillées"
        )
        
        if show_debug != st.session_state.get("show_debug", False):
            st.session_state.show_debug = show_debug
            st.success(f"✅ Mode debug {'activé' if show_debug else 'désactivé'}")


def render_system_configuration():
    """Configuration système et sauvegarde"""
    st.subheader("⚙️ Configuration Système")
    
    config = st.session_state.get("config")
    settings = st.session_state.get("settings", {})
    
    # Informations sur la configuration actuelle
    with st.expander("📋 Configuration Actuelle", expanded=False):
        st.json({
            "app": {"name": config.app_name, "version": config.version},
            "llm": {
                "provider": settings.get("llm_provider"),
                "model": settings.get("model_name")
            },
            "rag": {
                "verification": settings.get("enable_verification"),
                "multimodal": {
                    "images": settings.get("use_images"),
                    "tables": settings.get("use_tables")
                }
            },
            "memory": {
                "enabled": settings.get("enable_conversation_memory"),
                "window_size": settings.get("conversation_window_size")
            }
        })
    
    # Actions système
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Sauvegarder Config", type="primary"):
            save_current_config()
    
    with col2:
        if st.button("🔄 Recharger Config"):
            reload_current_config()
    
    with col3:
        if st.button("🔧 Réinitialiser Orchestrateur"):
            reset_orchestrator()


def save_current_config():
    """Sauvegarde la configuration actuelle"""
    try:
        config = st.session_state.get("config")
        settings = st.session_state.get("settings", {})
        
        # Mettre à jour la config avec les settings
        config.llm.default_provider = settings.get("llm_provider", config.llm.default_provider)
        
        if settings.get("llm_provider") == "ollama":
            config.llm.default_ollama_model = settings.get("model_name")
        else:
            config.llm.default_mistral_model = settings.get("model_name")
        
        config.rag.enable_verification = settings.get("enable_verification", config.rag.enable_verification)
        config.rag.use_images = settings.get("use_images", config.rag.use_images)
        config.rag.use_tables = settings.get("use_tables", config.rag.use_tables)
        config.memory.enabled = settings.get("enable_conversation_memory", config.memory.enabled)
        config.memory.window_size = settings.get("conversation_window_size", config.memory.window_size)
        config.rag.confidence_threshold = settings.get("confidence_threshold", config.rag.confidence_threshold)
        
        force_rag_keywords = settings.get("force_rag_keywords", "")
        if force_rag_keywords:
            config.rag.force_rag_keywords = [k.strip() for k in force_rag_keywords.split(",")]
        
        # Sauvegarder
        save_config()
        st.success("✅ Configuration sauvegardée avec succès!")
        
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde: {e}")


def reload_current_config():
    """Recharge la configuration depuis le fichier"""
    try:
        reload_config()
        st.success("✅ Configuration rechargée!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur de rechargement: {e}")


def reset_orchestrator():
    """Réinitialise l'orchestrateur"""
    try:
        st.session_state.orchestrator = None
        orchestrator = get_or_create_orchestrator()
        if orchestrator:
            st.success("✅ Orchestrateur réinitialisé!")
        else:
            st.error("❌ Erreur de réinitialisation")
    except Exception as e:
        st.error(f"❌ Erreur: {e}")


def main():
    """Fonction principale de la page configuration"""
    
    # Vérifier l'authentification
    if not require_authentication():
        return
    
    # Initialisation
    initialize_session_state()
    
    # Titre de la page
    st.title("⚙️ Configuration")
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
    
    # Section sécurité
    st.divider()
    st.subheader("🔐 Sécurité")
    render_change_password_form()
    
    # Footer
    st.divider()
    st.caption("💡 Les modifications sont appliquées automatiquement. Utilisez 'Sauvegarder Config' pour les rendre permanentes.")


if __name__ == "__main__":
    main()