"""
Composants d'affichage pour l'application Streamlit
"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from .streamlit_utils import get_current_time, extract_table_from_text, generate_unique_key


def display_sources(sources, t):
    """Affiche les sources de façon formatée - version basique"""
    if not sources:
        return
    
    # Version basique simple
    with st.expander("Sources utilisées", expanded=False):
        for i, source in enumerate(sources):
            st.markdown(f"""
            <div class="source-citation">
                <strong>Source {i+1}:</strong> {source.get('regulation', 'Réglementation')}, Section {source.get('section', 'Section inconnue')} (Pages {source.get('pages', 'Page inconnue')})
                <div style="margin-top: 5px; font-style: italic;">{source.get('text', '')}</div>
            </div>
            """, unsafe_allow_html=True)


def display_images(images, max_height=300, section_key=None, t=None, config=None):
    """
    Affiche les images de façon élégante avec taille contrôlée
    
    Args:
        images: Liste des images à afficher
        max_height: Hauteur maximale des images en pixels
        section_key: Clé unique pour identifier cette section d'images
        t: Fonction de traduction
        config: Configuration de l'application
    """
    # Générer une clé unique si elle n'est pas fournie
    if section_key is None:
        section_key = generate_unique_key("img_section")
        
    if not images:
        st.info(t("no_images_available") if t else "Aucune image disponible")
        return
        
    # Affichage minimal du nombre d'images
    with st.expander(t("images_available", len(images)) if t else f"Images disponibles ({len(images)})", expanded=False):
        # Filtrer les images invalides sans afficher les détails de débogage
        valid_images = []
        
        for i, img in enumerate(images):
            try:
                # Get image URL - try different possible formats
                image_url = img.get("url", "")
                
                if not image_url:
                    continue
                    
                if not isinstance(image_url, str):
                    continue
                    
                # Vérifier si l'URL est valide (au moins formellement)
                if not (image_url.startswith('http') or image_url.startswith('https') or image_url.startswith('data:')):
                    continue
                    
                valid_images.append(img)
            except Exception:
                pass
        
        # Si aucune image valide, afficher un message et sortir
        if not valid_images:
            st.warning(t("no_images_available") if t else "Aucune image disponible")
            return
        
        # Permettre à l'utilisateur d'ajuster la taille des images dans un expander compact
        col1, col2 = st.columns([1, 3])
        with col1:
            # Utiliser les tailles de configuration si disponibles
            if config and hasattr(config.ui, 'image_sizes'):
                size_options = list(config.ui.image_sizes.keys())
                size_labels = [t(f"image_size_{size}") if t else size for size in size_options]
            else:
                size_options = ["small", "medium", "large"]
                size_labels = ["Petit", "Moyen", "Grand"]
            
            selected_size = st.radio(
                t("image_size") if t else "Taille image",
                options=size_labels,
                index=0,  # Default to small
                key=f"img_size_{section_key}"
            )
        
        # Convertir le choix en pixels
        if config and hasattr(config.ui, 'image_sizes'):
            selected_size_key = size_options[size_labels.index(selected_size)]
            max_height = config.ui.image_sizes[selected_size_key]
        else:
            size_map = {"Petit": 200, "Moyen": 400, "Grand": 600}
            max_height = size_map.get(selected_size, 300)
        
        # Configuration responsive - plus d'images par ligne sur petits écrans
        # Maximum 3 colonnes, mais n'utilise pas plus de colonnes que d'images
        display_cols = min(3, len(valid_images))
        cols = st.columns(display_cols)
        
        # Variable pour stocker l'image sélectionnée pour affichage détaillé
        if f"selected_image_{section_key}" not in st.session_state:
            st.session_state[f"selected_image_{section_key}"] = None
        
        # Afficher les images en grille
        for i, img in enumerate(valid_images):
            with cols[i % display_cols]:
                # Conteneur pour l'image et les commandes
                with st.container():
                    # Image
                    image_url = img.get("url", "").strip()
                    description = img.get("description", "Aucune description")
                    
                    # Vérifier et afficher l'image
                    try:
                        # Vérifier si c'est une data URL
                        if image_url.startswith('data:image'):
                            # Pour les images data:URL, utiliser HTML pour garantir l'affichage
                            st.markdown(f"""
                            <div style="border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; margin-bottom: 10px;">
                                <div style="width: 100%; height: {max_height}px; 
                                        display: flex; align-items: center; justify-content: center; 
                                        background-color: #f8f9fa;">
                                    <img src="{image_url}" style="max-width: 100%; max-height: {max_height}px; 
                                                                object-fit: contain;" />
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # Pour les images avec URL normale, utiliser st.image
                            st.image(
                                image_url,
                                caption=None,  # Pas de légende ici, on l'ajoute plus bas
                                width=None,
                                use_container_width=True
                            )
                        
                        # Description tronquée courte
                        short_desc = description[:20] + ("..." if len(description) > 20 else "")
                        st.caption(f"<p style='color: white; font-size: 0.8em;'> {short_desc} </p>", unsafe_allow_html=True)
                        
                        # Bouton de détail plus discret
                        if st.button(f"📝", key=f"detail_btn_{section_key}_{i}", help=t("view_detail") if t else "Voir le détail"):
                            st.session_state[f"selected_image_{section_key}"] = {
                                "url": image_url,
                                "description": description
                            }
                    except Exception as e:
                        st.error(f"Erreur d'affichage: {str(e)}")
        
        # Afficher l'image détaillée si sélectionnée dans un modal-like container
        if st.session_state[f"selected_image_{section_key}"]:
            with st.container():
                st.divider()
                sel_img = st.session_state[f"selected_image_{section_key}"]
                
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.subheader(t("image_detail") if t else "Détail de l'image")
                with col2:
                    if st.button("❌", key=f"close_detail_{section_key}", help=t("close") if t else "Fermer"):
                        st.session_state[f"selected_image_{section_key}"] = None
                        st.rerun()
                
                try:
                    # Utiliser les composants natifs pour l'affichage détaillé aussi
                    if sel_img["url"].startswith('data:image'):
                        # Pour les images data:URL, utiliser HTML
                        st.markdown(f"""
                        <div style="width: 100%; display: flex; justify-content: center; margin: 20px 0;">
                            <img src="{sel_img['url']}" style="max-width: 100%; max-height: 500px; object-fit: contain;" />
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Pour les URL normales, utiliser st.image
                        st.image(sel_img["url"], use_container_width=True)
                    
                    # Description complète dans un container discret
                    with st.container():
                        st.markdown(f"**{t('image_description') if t else 'Description'}:** {sel_img['description']}")
                except Exception as e:
                    st.error(f"Erreur d'affichage: {str(e)}")


def display_tables(tables, t=None):
    """Affiche les tableaux de façon formatée avec détection améliorée"""
    if not tables:
        return
        
    st.markdown(f"<h4 style='color: white;'>{t('tables_title') if t else 'Tableaux'}</h4>", unsafe_allow_html=True)
    st.markdown("""
    <style>
    [data-testid="stExpander"] {
        background-color: white !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    for i, table in enumerate(tables):
        with st.expander(f"{t('table_label', i+1) if t else f'Tableau {i+1}'}", expanded=False):
            # Récupérer le contenu du tableau
            content = table.get('documents', "")
            
            # Fonction pour corriger les noms de colonnes dupliqués ou invalides
            def fix_column_names(columns):
                if columns is None:
                    return [f"Col_{i}" for i in range(20)]  # Noms génériques
                
                # Assurer que nous avons une liste
                cols = list(columns)
                
                # Remplacer les None par des noms génériques
                for i in range(len(cols)):
                    if cols[i] is None or cols[i] == "":
                        cols[i] = f"Col_{i}"
                
                # Gérer les doublons en ajoutant _1, _2, etc.
                seen = {}
                for i in range(len(cols)):
                    if cols[i] in seen:
                        seen[cols[i]] += 1
                        cols[i] = f"{cols[i]}_{seen[cols[i]]}"
                    else:
                        seen[cols[i]] = 0
                
                return cols
            
            # Étape 1: Essayer d'extraire un tableau du texte
            if isinstance(content, str):
                df = extract_table_from_text(content)
                if df is not None:
                    # Corriger les noms de colonnes
                    df.columns = fix_column_names(df.columns)
                    st.dataframe(df, use_container_width=True)
                    continue
            
            # Étape 2: Traiter différents formats de données structurées
            try:
                if isinstance(content, list) and all(isinstance(row, list) for row in content):
                    # Cas d'une matrice (liste de listes)
                    if content and len(content) > 0:
                        # Corriger les noms de colonnes
                        column_names = fix_column_names(content[0] if len(content) > 0 else None)
                        df = pd.DataFrame(content[1:], columns=column_names)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.write("Tableau vide")
                elif isinstance(content, list) and all(isinstance(row, dict) for row in content):
                    # Cas d'une liste de dictionnaires
                    df = pd.DataFrame(content)
                    st.dataframe(df, use_container_width=True)
                else:
                    # Si le contenu est une chaîne, essayer de l'analyser comme un tableau
                    if isinstance(content, str):
                        # Rechercher des patterns qui ressemblent à des tableaux
                        if '|' in content or '\t' in content:
                            # Tentative de splitting et nettoyage
                            lines = [line.strip() for line in content.split('\n') if line.strip()]
                            if lines:
                                rows = []
                                for line in lines:
                                    if '|' in line:
                                        cells = [cell.strip() for cell in line.split('|')]
                                    else:
                                        cells = [cell.strip() for cell in line.split('\t')]
                                    rows.append(cells)
                                
                                if rows and len(rows) > 0:
                                    # Corriger les noms de colonnes
                                    column_names = fix_column_names(rows[0] if len(rows) > 0 else None)
                                    df = pd.DataFrame(rows[1:], columns=column_names)
                                    st.dataframe(df, use_container_width=True)
                                    continue
                        
                        # Si toutes les tentatives échouent, afficher tel quel mais avec un format amélioré
                        st.markdown(f"```\n{content}\n```")
                    else:
                        # Dernier recours: afficher tel quel
                        st.write(content)
            except Exception as e:
                # En cas d'erreur, afficher le contenu brut et l'erreur
                st.error(f"Erreur de tableau: {str(e)}")
                st.code(str(content))
                # Afficher plus de détails sur l'erreur pour le débogage
                with st.expander("Détails de l'erreur", expanded=False):
                    st.exception(e)


def stream_assistant_response(orchestrator, query, settings, t):
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
                # Afficher l'analyse
                analysis_data = chunk_content
                needs_rag = chunk_content.get("needs_rag", False)
                mode_text = t("mode_rag") if needs_rag else t("mode_direct")
                analysis_placeholder.markdown(f"""
                <div style="padding: 10px; border-radius: 5px; background-color: #e8f4f8;">
                    <strong>{t('mode_used')}:</strong> {mode_text} | 
                    <strong>{t('confidence')}:</strong> {chunk_content.get('confidence', 0):.2f}
                </div>
                """, unsafe_allow_html=True)
            
            elif chunk_type == "search_complete":
                # Récupérer les résultats de recherche
                sources = chunk_content.get("sources", [])
                
                # Filtrer les images valides (avec URLs non vides)
                raw_images = chunk_content.get("images", [])
                
                images = []
                for img in raw_images:
                    # Vérifier que l'URL existe et n'est pas vide - check both possible URL formats
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
                        mode_badge = f'<span class="badge badge-blue">{t("mode_rag")}</span>'
                    else:
                        mode_badge = f'<span class="badge badge-green">{t("mode_direct")}</span>'
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">{t('assistant')}</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{response_text}<span class="cursor">▋</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif chunk_type == "error":
                st.error(f"{t('error_occurred')} {chunk_content}")
                return None
            
            elif chunk_type == "done":
                # Finaliser l'affichage sans le curseur
                with response_container.container():
                    if analysis_data and analysis_data.get("needs_rag", False):
                        mode_badge = f'<span class="badge badge-blue">{t("mode_rag")}</span>'
                    else:
                        mode_badge = f'<span class="badge badge-green">{t("mode_direct")}</span>'
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">{t('assistant')}</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{response_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Nettoyer l'indicateur d'analyse
        analysis_placeholder.empty()
        
        # Retourner les données finales
        return {
            "response": response_text,
            "analysis": analysis_data,
            "images": images,
            "tables": tables,
            "sources": sources
        }
        
    except Exception as e:
        st.error(f"{t('error_occurred')} {str(e)}")
        st.exception(e)  # Display the full exception traceback
        return None


def display_assistant_response(response_data, query, t):
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
        mode_badge = f'<span class="badge badge-blue">{t("mode_rag")}</span>'
        mode_explanation = t("explanation_rag")
    else:
        mode_badge = f'<span class="badge badge-green">{t("mode_direct")}</span>'
        mode_explanation = t("explanation_direct")
    
    # Afficher le message avec le badge de mode
    st.markdown(f"""
    <div class="assistant-message">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: #333;">{t('assistant')}</strong>
                {mode_badge}
            </div>
            <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
        </div>
        <div style="color: #333; margin-top: 10px;">{content}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Afficher l'explication du mode utilisé dans un expander
    with st.expander(t("response_mode"), expanded=False):
        st.markdown(f"""
        <div style="color: white;">
            <strong>{t('mode_used')}:</strong> {mode_badge}
            
            <br><br>
            <strong>{t('analysis')}:</strong>
            <ul style="color: white;">
                <li>{t('query_type')}: {query_type}</li>
                <li>{t('uses_rag')}: {"Oui" if needs_rag else "Non"}</li>
                <li>{t('confidence')}: {confidence:.2f}</li>
                <li>{t('explanation')}: {mode_explanation}</li>
                <li>{t('context')}: {context_hint}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True) 