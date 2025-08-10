"""
Module de gestion de la génération de chat et du streaming des réponses
"""
import streamlit as st
from datetime import datetime
from assistant_regulation.app.display_manager import display_sources


def get_current_time():
    """Renvoie l'horodatage actuel formaté"""
    return datetime.now().strftime("%H:%M:%S")


def stream_assistant_response(orchestrator, query, settings):
    """Gère l'affichage d'une réponse en streaming"""
    
    # Créer un placeholder pour l'indicateur d'analyse
    analysis_placeholder = st.empty()
    
    # Créer un placeholder pour la réponse
    response_container = st.empty()
    response_text = ""
    
    # Variables pour stocker les métadonnées
    analysis_data = None
    images = []
    tables = []
    sources = []
    
    try:
        # Démarrer le streaming avec contexte conversationnel
        for chunk in orchestrator.process_query_stream(
            query,
            use_images=settings["use_images"],
            use_tables=settings["use_tables"],
            top_k=10
        ):
            chunk_type = chunk.get("type", "unknown")
            chunk_content = chunk.get("content", "")
            
            if chunk_type == "analysis":
                # Afficher l'analyse avec le nouveau badge intelligent
                from assistant_regulation.app.streamlit_utils import get_intelligent_routing_badge
                analysis_data = chunk_content
                routing_decision = chunk_content.get("routing_decision", {})
                mode_badge = get_intelligent_routing_badge(analysis_data, routing_decision)
                confidence = chunk_content.get('confidence', 0)
                
                analysis_placeholder.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; background-color: #e8f4f8;">
                    <strong>Mode utilisé:</strong> {mode_badge} | 
                    <strong>Confiance:</strong> {confidence:.2f}
                </div>
                """, unsafe_allow_html=True)
            
            elif chunk_type == "search_complete":
                # Récupérer les résultats de recherche
                sources = chunk_content.get("sources", [])
                
                # Filtrer les images valides (avec URLs non vides)
                raw_images = chunk_content.get("images", [])
                
                images = []
                for img in raw_images:
                    # Vérifier que l'URL existe et n'est pas vide
                    image_url = img.get("url", "")
                    
                    # If no direct url field, try to get it from metadata
                    if not image_url and isinstance(img.get("metadata"), dict):
                        image_url = img.get("metadata", {}).get("image_url", "")
                    
                    if isinstance(image_url, str) and image_url.strip():
                        # Assurer que l'URL est proprement formatée
                        url = image_url.strip()
                        
                        # Ajouter l'image avec l'URL validée
                        images.append({
                            "url": url,
                            "description": img.get("description", img.get("documents", "")),
                            "page": img.get("page", img.get("metadata", {}).get("page", "N/A"))
                        })
                
                tables = chunk_content.get("tables", [])
            
            elif chunk_type == "text":
                # Ajouter le texte au cumul et l'afficher
                response_text += chunk_content
                
                # Afficher la réponse dans le container avec un style
                with response_container.container():
                    if analysis_data and analysis_data.get("needs_rag", False):
                        mode_badge = '<span class="badge badge-blue">Mode RAG</span>'
                    else:
                        mode_badge = '<span class="badge badge-green">Mode Direct</span>'
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">Assistant</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{response_text}<span class="cursor">▋</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif chunk_type == "error":
                st.error(f"Erreur: {chunk_content}")
                return None
            
            elif chunk_type == "done":
                # Finaliser l'affichage sans le curseur
                with response_container.container():
                    if analysis_data and analysis_data.get("needs_rag", False):
                        mode_badge = '<span class="badge badge-blue">Mode RAG</span>'
                    else:
                        mode_badge = '<span class="badge badge-green">Mode Direct</span>'
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">Assistant</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{response_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Nettoyer l'indicateur d'analyse
        analysis_placeholder.empty()
        
        # Finaliser l'affichage sans le curseur
        with response_container.container():
            if analysis_data and analysis_data.get("needs_rag", False):
                mode_badge = '<span class="badge badge-blue">Mode RAG</span>'
            else:
                mode_badge = '<span class="badge badge-green">Mode Direct</span>'
            
            st.markdown(f"""
            <div class="assistant-message">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #333;">Assistant</strong>
                        {mode_badge}
                    </div>
                    <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                </div>
                <div style="color: #333; margin-top: 10px;">{response_text}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Retourner les données finales
        return {
            "response": response_text,
            "analysis": analysis_data,
            "images": images,
            "tables": tables,
            "sources": sources
        }
        
    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        st.exception(e)
        return None


def display_assistant_response(response_data, query):
    """Affiche une réponse de l'assistant avec son mode de réponse"""
    
    # Récupérer l'analyse de la requête
    analysis = response_data.get("analysis", {})
    query_type = analysis.get("query_type", "unknown")
    needs_rag = analysis.get("needs_rag", False)
    confidence = analysis.get("confidence", 0)
    context_hint = analysis.get("context_hint", "")
    timestamp = response_data.get("timestamp", get_current_time())
    content = response_data.get("content", "")
    
    # Afficher un badge indiquant le mode de réponse
    if needs_rag:
        mode_badge = '<span class="badge badge-blue">Mode RAG</span>'
        mode_explanation = "Réponse basée sur la recherche dans les documents"
    else:
        mode_badge = '<span class="badge badge-green">Mode Direct</span>'
        mode_explanation = "Réponse basée sur les connaissances générales"
    
    # Afficher le message avec le badge de mode
    st.markdown(f"""
    <div class="assistant-message">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: #333;">Assistant</strong>
                {mode_badge}
            </div>
            <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
        </div>
        <div style="color: #333; margin-top: 10px;">{content}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Afficher l'explication du mode utilisé dans un expander
    with st.expander("Mode de réponse", expanded=False):
        st.markdown(f"""
        <div style="color: white;">
            <strong>Mode utilisé:</strong> {mode_badge}
            
            <br><br>
            <strong>Analyse:</strong>
            <ul style="color: white;">
                <li>Type de requête: {query_type}</li>
                <li>Utilise RAG: {"Oui" if needs_rag else "Non"}</li>
                <li>Confiance: {confidence:.2f}</li>
                <li>Explication: {mode_explanation}</li>
                <li>Contexte: {context_hint}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


def display_message(message, is_user=False):
    """Affiche un message formaté dans l'historique de conversation"""
    timestamp = message.get("timestamp", get_current_time())
    content = message.get("content", "")
    
    if is_user:
        st.markdown(f"""
        <div class="user-message">
            <div style="display: flex; justify-content: space-between;">
                <strong>Vous</strong>
                <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
            </div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            <div style="display: flex; justify-content: space-between;">
                <strong>Assistant</strong>
                <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
            </div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)


def create_response_badge(analysis_data):
    """Crée un badge pour le mode de réponse"""
    if analysis_data and analysis_data.get("needs_rag", False):
        return '<span class="badge badge-blue">Mode RAG</span>'
    else:
        return '<span class="badge badge-green">Mode Direct</span>'


def format_chat_message(content, role="assistant", timestamp=None, analysis_data=None):
    """Formate un message de chat avec style et badges"""
    if timestamp is None:
        timestamp = get_current_time()
    
    role_display = "Assistant" if role == "assistant" else "Vous"
    message_class = "assistant-message" if role == "assistant" else "user-message"
    
    # Ajouter badge pour l'assistant
    badge_html = ""
    if role == "assistant" and analysis_data:
        badge_html = create_response_badge(analysis_data)
    
    return f"""
    <div class="{message_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: #333;">{role_display}</strong>
                {badge_html}
            </div>
            <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
        </div>
        <div style="color: #333; margin-top: 10px;">{content}</div>
    </div>
    """


def create_typing_indicator():
    """Crée un indicateur de frappe animé"""
    return """
    <div style="display: flex; align-items: center; padding: 10px; background-color: #f0f7f0; border-radius: 15px; margin: 10px 0;">
        <strong style="color: #333; margin-right: 10px;">Assistant</strong>
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    </div>
    <style>
    .typing-indicator {
        display: flex;
        gap: 4px;
    }
    .typing-indicator span {
        width: 8px;
        height: 8px;
        background-color: #0a6ebd;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
    </style>
    """


def add_message_to_history(message, role="user", analysis_data=None):
    """Ajoute un message à l'historique de la session"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    message_data = {
        "role": role,
        "content": message,
        "timestamp": get_current_time()
    }
    
    if analysis_data:
        message_data["analysis"] = analysis_data
    
    st.session_state.messages.append(message_data)
    return message_data


def clear_chat_history():
    """Vide l'historique de chat"""
    if 'messages' in st.session_state:
        st.session_state.messages = []
    st.success("Historique de conversation vidé !")


def export_chat_history():
    """Exporte l'historique de chat au format texte"""
    if 'messages' not in st.session_state or not st.session_state.messages:
        return "Aucun historique à exporter."
    
    export_text = "HISTORIQUE DE CONVERSATION\n"
    export_text += "=" * 50 + "\n\n"
    
    for msg in st.session_state.messages:
        role = "VOUS" if msg["role"] == "user" else "ASSISTANT"
        timestamp = msg.get("timestamp", "")
        content = msg.get("content", "")
        
        export_text += f"[{timestamp}] {role}:\n"
        export_text += f"{content}\n\n"
        export_text += "-" * 30 + "\n\n"
    
    return export_text 