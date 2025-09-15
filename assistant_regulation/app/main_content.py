"""
Contenu principal de l'application Streamlit
"""
import streamlit as st
import time
from assistant_regulation.app.streamlit_utils import get_current_time, display_regulation_metrics, generate_unique_key, get_intelligent_routing_badge
from .display_components import display_sources, display_images, display_tables, stream_assistant_response
from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator


def render_welcome_section(t):
    """Affiche la section de bienvenue avec les métriques des réglementations"""
    display_regulation_metrics()
    
    st.markdown(f"""
    <div class="info-card">
        <h3 align="center">{t('welcome_title')}</h3>
        <p>{t('welcome_subtitle')}</p>
        <p>{t('example_questions')}</p>
        <ul>
            <li>{t('example1')}</li>
            <li>{t('example2')}</li>
            <li>{t('example3')}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # (Bloc d'information Mémoire Conversationnelle supprimé)


def render_header(t, config):
    """Affiche l'en-tête principal avec indicateur de mémoire"""
    header_content = f"<h1 style='color: white; text-align: center;'>{t('app_title')}</h1>"

    # Ajouter un indicateur de mémoire conversationnelle
    if (st.session_state.settings.get("enable_conversation_memory", False) and 
        st.session_state.orchestrator and 
        hasattr(st.session_state.orchestrator, 'get_conversation_stats')):
        
        stats = st.session_state.orchestrator.get_conversation_stats()
        if stats and stats.get("conversation_memory") != "disabled" and stats.get("total_turns", 0) > 0:
            memory_badge = f"""
            <div style="display: inline-block; background: linear-gradient(90deg, #2ecc71, #27ae60); 
                        color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px; 
                        margin-left: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                🧠 Mémoire: {stats.get('recent_turns', 0)} récents | {stats.get('summaries_count', 0)} résumés
            </div>
            """
            header_content += memory_badge

    st.markdown(header_content, unsafe_allow_html=True)


def render_message_history(t, config):
    """Affiche l'historique des messages"""
    for message in st.session_state.messages:
        if message["role"] == "user":
            from assistant_regulation.app.streamlit_utils import display_message
            display_message(message, is_user=True, t=t)
        else:  # assistant message
            # Afficher la réponse avec le nouveau badge intelligent
            analysis = message.get("analysis", {})
            routing_decision = message.get("routing_decision", {})
            mode_badge = get_intelligent_routing_badge(analysis, routing_decision)
            
            st.markdown(f"""
            <div class="assistant-message">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #333;">Assistant Réglementaire</strong>
                        {mode_badge}
                    </div>
                    <span style="color: #888; font-size: 0.8em;">{message.get('timestamp', '')}</span>
                </div>
                <div style="color: #333; margin-top: 10px;">{message['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Afficher les médias et sources
            if "images" in message and message["images"]:
                # Générer une clé unique pour cette section d'images
                display_images(message["images"], section_key=generate_unique_key("img_section"), t=t, config=config)
                
            if "tables" in message and message["tables"]:
                display_tables(message["tables"], t=t)
                
            if "sources" in message and message["sources"]:
                display_sources(message["sources"], t=t, compact=True)


def process_user_query(query, t, config):
    """Traite une requête utilisateur et affiche la réponse"""
    # Ajouter le message de l'utilisateur à l'historique
    user_message = {
        "role": "user",
        "content": query,
        "timestamp": get_current_time()
    }
    st.session_state.messages.append(user_message)
    
    # Afficher le message de l'utilisateur
    from assistant_regulation.app.streamlit_utils import display_message
    display_message(user_message, is_user=True, t=t)
    
    # Afficher l'indicateur de chargement
    progress_placeholder = st.empty()
    try:
        
        # Vérifier que l'orchestrateur est initialisé ou doit être recréé
        orchestrator_version = "modular_1.0"
        needs_recreate = (
            st.session_state.orchestrator is None or
            not hasattr(st.session_state.orchestrator, '_version') or
            getattr(st.session_state.orchestrator, '_version', None) != orchestrator_version
        )
        
        if needs_recreate:
            print(f"[ORCHESTRATOR] Creating new ModularOrchestrator with optimizations...")
            st.session_state.orchestrator = ModularOrchestrator(
                llm_provider=st.session_state.settings["llm_provider"],
                model_name=st.session_state.settings["model_name"],
                enable_verification=st.session_state.settings["enable_verification"]
            )
            print(f"[ORCHESTRATOR] Cache enabled: {st.session_state.orchestrator.retrieval_service.config.enable_caching}")
            print(f"[ORCHESTRATOR] Created successfully")
            # Marquer la version pour éviter les recréations inutiles
            st.session_state.orchestrator._version = orchestrator_version
        
        # Phase 1: Analyse de la requête
        progress_placeholder.markdown("<p style='color: white;'>Analyse de la requête...</p>", unsafe_allow_html=True)
        time.sleep(0.5)
        
        # Phase 2: Streaming de la réponse
        progress_placeholder.markdown("<p style='color: white;'>Génération de la réponse...</p>", unsafe_allow_html=True)
        
        # Streamer la réponse avec contexte conversationnel
        result = stream_assistant_response(
            st.session_state.orchestrator,
            query,
            st.session_state.settings,
            t
        )
        
        # Nettoyer l'indicateur de progression
        progress_placeholder.empty()
        
        if result:
            # Créer le message de réponse
            assistant_message = {
                "role": "assistant",
                "content": result["response"],
                "images": result["images"],
                "tables": result["tables"],
                "sources": result["sources"],
                "analysis": result["analysis"],
                "routing_decision": result.get("routing_decision"),
                "timestamp": get_current_time()
            }
            
            # Ajouter la réponse à l'historique
            st.session_state.messages.append(assistant_message)
            
            # Enregistrer la conversation en mémoire
            if (st.session_state.orchestrator and 
                hasattr(st.session_state.orchestrator, 'conversation_memory') and 
                st.session_state.orchestrator.conversation_memory):
                # Sécurisation de l'accès à analysis
                analysis = result.get("analysis") or {}
                metadata = {
                    "sources_count": len(result.get("sources", [])),
                    "images_count": len(result.get("images", [])),
                    "tables_count": len(result.get("tables", [])),
                    "query_type": analysis.get("query_type", "unknown"),
                    "mode": "RAG" if analysis.get("needs_rag", False) else "Direct"
                }
                st.session_state.orchestrator.conversation_memory.add_turn(
                    user_query=query,
                    assistant_response=result["response"],
                    metadata=metadata
                )
            
            # Afficher les médias et sources
            if result["images"]:
                # Générer une clé unique pour cette section d'images
                display_images(result["images"], section_key=generate_unique_key("img_section"), t=t, config=config)
                
            if result["tables"]:
                display_tables(result["tables"], t=t)
                
            display_sources(result["sources"], t=t, compact=False)
    
    except Exception as e:
        st.error(f"Une erreur s'est produite: {str(e)}")
        
        # Ajouter un message d'erreur à l'historique
        error_message = {
            "role": "assistant",
            "content": f"Je suis désolé, une erreur s'est produite lors du traitement de votre demande: {str(e)}",
            "timestamp": get_current_time()
        }
        st.session_state.messages.append(error_message)


def render_main_content(t, config):
    """Affiche le contenu principal de l'application"""
    # En-tête
    render_header(t, config)
    
    # Section de bienvenue si pas de messages
    if not st.session_state.messages:
        render_welcome_section(t)
    
    # Historique des messages
    render_message_history(t, config)
    
    # Zone de saisie pour la question
    query = st.chat_input("Posez votre question sur les réglementations automobiles...")
    
    # Traitement de la question
    if query:
        process_user_query(query, t, config)
    
    # Afficher un pied de page
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.caption("<p style='color: white;'> Cet assistant utilise les bases de données officielles des réglementations UN/ECE. Les réponses sont générées à titre informatif uniquement.</p>", unsafe_allow_html=True) 