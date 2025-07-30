"""
Composants avancés pour l'affichage des sources avec liens cliquables et citations Vancouver
"""
import streamlit as st
import re
from typing import List, Dict, Any, Optional


def display_enhanced_sources(sources: List[Dict], t=None):
    """
    Affiche les sources avec des liens cliquables vers les documents
    
    Args:
        sources: Liste des sources avec métadonnées enrichies
        t: Fonction de traduction
    """
    if not sources:
        return
    
    # Titre de la section sources
    st.markdown("### 📚 Sources citées", unsafe_allow_html=True)
    
    # CSS pour les sources
    st.markdown("""
    <style>
    .source-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        border-left: 4px solid #0a6ebd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .source-card:hover {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .source-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .source-title {
        font-weight: bold;
        color: #0a6ebd;
        text-decoration: none;
        cursor: pointer;
        transition: color 0.3s ease;
    }
    
    .source-title:hover {
        color: #ffffff;
        text-decoration: underline;
    }
    
    .source-badges {
        display: flex;
        gap: 5px;
        flex-wrap: wrap;
    }
    
    .badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        font-weight: bold;
        text-align: center;
    }
    
    .badge-regulation { background-color: #e74c3c; color: white; }
    .badge-page { background-color: #3498db; color: white; }
    .badge-quality { background-color: #2ecc71; color: white; }
    .badge-chunker { background-color: #9b59b6; color: white; }
    .badge-content { background-color: #f39c12; color: white; }
    
    .source-preview {
        margin-top: 10px;
        padding: 10px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 4px;
        font-style: italic;
        font-size: 0.9em;
        color: #cccccc;
    }
    
    .source-metadata {
        margin-top: 10px;
        font-size: 0.8em;
        color: #888;
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .clickable-link {
        color: #0a6ebd;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.3s ease;
        padding: 5px 10px;
        border-radius: 4px;
        background: rgba(10, 110, 189, 0.1);
    }
    
    .clickable-link:hover {
        background: rgba(10, 110, 189, 0.2);
        color: #ffffff;
        text-decoration: underline;
    }
    
    .quality-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 5px;
    }
    
    .quality-high { background-color: #2ecc71; }
    .quality-medium { background-color: #f39c12; }
    .quality-low { background-color: #e74c3c; }
    </style>
    """, unsafe_allow_html=True)
    
    # Affichage des sources
    for i, source in enumerate(sources):
        source_id = source.get('id', f'source_{i+1}')
        
        # Construction des badges
        badges_html = []
        
        # Badge de réglementation
        regulation_code = source.get('regulation_code', 'Code inconnu')
        if regulation_code and regulation_code != 'Code inconnu':
            badges_html.append(f'<span class="badge badge-regulation">{regulation_code}</span>')
        
        # Badge de page(s)
        page_display = source.get('page_display', 'Page inconnue')
        if page_display and page_display != 'Page inconnue':
            pages_count = len(source.get('pages', []))
            page_text = f"Page {page_display}" if pages_count <= 1 else f"Pages {page_display}"
            badges_html.append(f'<span class="badge badge-page">{page_text}</span>')
        
        # Informations Late Chunker
        chunk_info = source.get('chunk_info', {})
        if chunk_info:
            quality_score = chunk_info.get('quality_score', 0)
            if quality_score > 0:
                quality_class = 'quality-high' if quality_score > 0.8 else 'quality-medium' if quality_score > 0.5 else 'quality-low'
                badges_html.append(f'<span class="badge badge-quality"><span class="quality-indicator {quality_class}"></span>{quality_score:.2f}</span>')
            
            # Badge du type de chunker
            badges_html.append(f'<span class="badge badge-chunker">Late Chunker</span>')
            
            # Badges d'analyse de contenu
            content_analysis = chunk_info.get('content_analysis', {})
            content_badges = []
            if content_analysis.get('has_requirement'): content_badges.append('Req')
            if content_analysis.get('has_definition'): content_badges.append('Def')
            if content_analysis.get('has_procedure'): content_badges.append('Proc')
            if content_analysis.get('has_article'): content_badges.append('Art')
            
            if content_badges:
                badges_html.append(f'<span class="badge badge-content">{", ".join(content_badges)}</span>')
        
        badges_str = ' '.join(badges_html)
        
        # Construction du titre cliquable
        document_name = source.get('document_name', 'Document inconnu')
        source_link = source.get('source_link')
        
        if source_link:
            title_html = f'<a href="{source_link}" class="source-title" onclick="window.open(this.href); return false;">{document_name}</a>'
        else:
            title_html = f'<span class="source-title">{document_name}</span>'
        
        # Aperçu du texte
        text_preview = source.get('text_preview', 'Pas d\'aperçu disponible')
        
        # Métadonnées additionnelles
        metadata_items = []
        if chunk_info:
            token_count = chunk_info.get('token_count', 0)
            if token_count > 0:
                metadata_items.append(f"📝 {token_count} tokens")
            
            char_count = chunk_info.get('char_count', 0)
            if char_count > 0:
                metadata_items.append(f"📏 {char_count} caractères")
            
            chunk_position = chunk_info.get('chunk_position', 0)
            if chunk_position > 0:
                metadata_items.append(f"📍 Position: {chunk_position:.1%}")
        
        metadata_html = ' • '.join(metadata_items) if metadata_items else ''
        
        # Construction de la carte source
        st.markdown(f"""
        <div class="source-card" id="{source_id}">
            <div class="source-header">
                {title_html}
                <div class="source-badges">
                    {badges_str}
                </div>
            </div>
            <div class="source-preview">
                "{text_preview}"
            </div>
            {f'<div class="source-metadata">{metadata_html}</div>' if metadata_html else ''}
        </div>
        """, unsafe_allow_html=True)


def generate_vancouver_citations(sources: List[Dict], response_text: str) -> str:
    """
    Génère des citations style Vancouver dans le texte de réponse
    
    Args:
        sources: Liste des sources
        response_text: Texte de la réponse
        
    Returns:
        Texte avec citations Vancouver intégrées
    """
    if not sources:
        return response_text
    
    # Créer un mapping des sources pour les citations
    citation_map = {}
    for i, source in enumerate(sources, 1):
        regulation_code = source.get('regulation_code', '')
        document_name = source.get('document_name', '')
        pages = source.get('pages', [])
        source_link = source.get('source_link', '')
        
        # Format Vancouver simplifié: Auteur. Titre. Page.
        if regulation_code and regulation_code != 'Code inconnu':
            if pages:
                citation_text = f"{regulation_code}. {document_name}. p.{pages[0]}"
            else:
                citation_text = f"{regulation_code}. {document_name}"
        else:
            citation_text = document_name
        
        # Créer le lien hypertexte
        if source_link:
            citation_link = f'<a href="{source_link}" onclick="window.open(this.href); return false;" style="color: #0a6ebd; text-decoration: none;">[{i}]</a>'
        else:
            citation_link = f'[{i}]'
        
        citation_map[i] = {
            'number': i,
            'text': citation_text,
            'link': citation_link,
            'source_link': source_link
        }
    
    # Stratégies pour insérer les citations dans le texte
    modified_text = response_text
    
    # 1. Rechercher des mentions de réglementations spécifiques
    for i, source in enumerate(sources, 1):
        regulation_code = source.get('regulation_code', '')
        if regulation_code and regulation_code != 'Code inconnu':
            # Remplacer les mentions du code de réglementation
            pattern = rf"\\b{re.escape(regulation_code)}\\b"
            replacement = f"{regulation_code} {citation_map[i]['link']}"
            modified_text = re.sub(pattern, replacement, modified_text, count=1)
    
    # 2. Ajouter des citations à la fin des phrases importantes
    # (logique plus complexe pourrait être ajoutée ici)
    
    # 3. Ajouter la liste des références à la fin
    references_html = "\\n\\n**Références:**\\n"
    for i, citation_info in citation_map.items():
        references_html += f"{citation_info['link']} {citation_info['text']}\\n"
    
    modified_text += references_html
    
    return modified_text


def display_source_summary(sources: List[Dict]):
    """
    Affiche un résumé des sources utilisées
    """
    if not sources:
        return
    
    st.markdown("### 📊 Résumé des sources")
    
    # Statistiques générales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total sources", len(sources))
    
    with col2:
        regulations = set(s.get('regulation_code', '') for s in sources if s.get('regulation_code'))
        st.metric("Réglementations", len(regulations))
    
    with col3:
        documents = set(s.get('document_name', '') for s in sources if s.get('document_name'))
        st.metric("Documents", len(documents))
    
    with col4:
        # Qualité moyenne (si disponible)
        quality_scores = [s.get('chunk_info', {}).get('quality_score', 0) for s in sources]
        quality_scores = [q for q in quality_scores if q > 0]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            st.metric("Qualité moy.", f"{avg_quality:.2f}")
        else:
            st.metric("Qualité moy.", "N/A")
    
    # Analyse de contenu
    if sources and any(s.get('chunk_info') for s in sources):
        st.markdown("**Analyse du contenu:**")
        
        content_stats = {
            'requirements': sum(1 for s in sources if s.get('chunk_info', {}).get('content_analysis', {}).get('has_requirement', False)),
            'definitions': sum(1 for s in sources if s.get('chunk_info', {}).get('content_analysis', {}).get('has_definition', False)),
            'procedures': sum(1 for s in sources if s.get('chunk_info', {}).get('content_analysis', {}).get('has_procedure', False)),
            'articles': sum(1 for s in sources if s.get('chunk_info', {}).get('content_analysis', {}).get('has_article', False))
        }
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Exigences", content_stats['requirements'])
        with col2:
            st.metric("Définitions", content_stats['definitions'])
        with col3:
            st.metric("Procédures", content_stats['procedures'])
        with col4:
            st.metric("Articles", content_stats['articles'])


def display_source_quality_analysis(sources: List[Dict]):
    """
    Affiche une analyse de qualité des sources
    """
    if not sources:
        return
    
    # Filtrer les sources avec informations de qualité
    quality_sources = [s for s in sources if s.get('chunk_info', {}).get('quality_score', 0) > 0]
    
    if not quality_sources:
        return
    
    with st.expander("🔍 Analyse qualité des sources", expanded=False):
        for source in quality_sources:
            chunk_info = source.get('chunk_info', {})
            quality_score = chunk_info.get('quality_score', 0)
            
            # Indicateur visuel de qualité
            if quality_score > 0.8:
                quality_color = "#2ecc71"
                quality_label = "Excellente"
            elif quality_score > 0.6:
                quality_color = "#f39c12"
                quality_label = "Bonne"
            else:
                quality_color = "#e74c3c"
                quality_label = "Moyenne"
            
            document_name = source.get('document_name', 'Document inconnu')
            token_count = chunk_info.get('token_count', 0)
            has_global_context = chunk_info.get('has_global_context', False)
            
            st.markdown(f"""
            <div style="padding: 10px; border-left: 4px solid {quality_color}; margin: 5px 0; background: rgba(255,255,255,0.1); border-radius: 4px;">
                <strong>{document_name}</strong><br>
                <span style="color: {quality_color};">●</span> Qualité: {quality_label} ({quality_score:.2f}) 
                • {token_count} tokens 
                • Contexte global: {"Oui" if has_global_context else "Non"}
            </div>
            """, unsafe_allow_html=True)


def display_compact_sources(sources: List[Dict], t=None):
    """
    Affiche les sources de manière compacte avec nom de document et pages cliquables
    Format: R046 - 06 series (p.55), R0107 - 06 series (p.29-30)
    
    Args:
        sources: Liste des sources avec métadonnées
        t: Fonction de traduction
    """
    if not sources:
        return
    
    # Titre de la section sources
    st.markdown("### 📚 Sources citées", unsafe_allow_html=True)
    
    # CSS pour les références compactes
    st.markdown("""
    <style>
    .compact-source {
        display: inline-block;
        margin: 5px 10px 5px 0;
        padding: 8px 12px;
        background: linear-gradient(135deg, rgba(10, 110, 189, 0.1), rgba(10, 110, 189, 0.05));
        border-left: 3px solid #0a6ebd;
        border-radius: 6px;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .compact-source:hover {
        background: linear-gradient(135deg, rgba(10, 110, 189, 0.2), rgba(10, 110, 189, 0.1));
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .compact-source-link {
        color: #0a6ebd;
        text-decoration: none;
        font-weight: bold;
        transition: color 0.3s ease;
    }
    
    .compact-source-link:hover {
        color: #ffffff;
        text-decoration: none;
    }
    
    .page-info {
        color: #888;
        font-size: 0.9em;
        margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Affichage des sources en format compact
    source_html = "<div style='margin: 15px 0;'>"
    
    for i, source in enumerate(sources):
        # Extraire les informations essentielles
        regulation_code = source.get('regulation_code', 'Document')
        document_name = source.get('document_name', 'Document inconnu')
        pages = source.get('pages', [])
        page_display = source.get('page_display', '')
        source_link = source.get('source_link', '')
        
        # Format d'affichage : "R046 - 06 series (p.55)"
        if regulation_code and regulation_code != 'Code inconnu':
            display_name = regulation_code
            if document_name and '- ' in document_name:
                # Extraire la version (ex: "06 series")
                version_part = document_name.split('- ')[-1] if '- ' in document_name else ''
                if version_part:
                    display_name += f" - {version_part}"
        else:
            display_name = document_name
        
        # Affichage des pages
        if page_display:
            page_text = f"(p.{page_display})"
        elif pages:
            if len(pages) == 1:
                page_text = f"(p.{pages[0]})"
            else:
                page_text = f"(p.{pages[0]}-{pages[-1]})"
        else:
            page_text = ""
        
        # Créer le lien cliquable si disponible
        if source_link:
            source_html += f"""
            <div class="compact-source">
                <a href="{source_link}" class="compact-source-link" onclick="window.open(this.href); return false;" target="_blank">
                    {display_name}
                </a>
                <span class="page-info">{page_text}</span>
            </div>
            """
        else:
            source_html += f"""
            <div class="compact-source">
                <span class="compact-source-link">{display_name}</span>
                <span class="page-info">{page_text}</span>
            </div>
            """
    
    source_html += "</div>"
    st.markdown(source_html, unsafe_allow_html=True)


def convert_source_references_to_clickable(response_text: str, sources: List[Dict], images: List[Dict] = None, tables: List[Dict] = None) -> str:
    """
    Convertit les références [Source X], [Image X], [Tableau X] en boutons cliquables pour ouvrir via l'OS
    
    Args:
        response_text: Texte avec références générées par le modèle
        sources: Liste des sources texte
        images: Liste des images
        tables: Liste des tableaux
        
    Returns:
        Texte avec références converties en boutons cliquables
    """
    from .document_opener import create_clickable_reference
    
    modified_text = response_text
    
    # Traiter les références aux sources texte [Source 1], [Source 2], etc.
    if sources:
        for i, source in enumerate(sources, 1):
            clickable_ref = create_clickable_reference(i, source, "Source")
            modified_text = modified_text.replace(f"[Source {i}]", clickable_ref)
    
    # Traiter les références aux images [Image 1], [Image 2], etc.
    if images:
        for i, image in enumerate(images, 1):
            clickable_ref = create_clickable_reference(i, image, "Image")
            modified_text = modified_text.replace(f"[Image {i}]", clickable_ref)
    
    # Traiter les références aux tableaux [Tableau 1], [Tableau 2], etc.  
    if tables:
        for i, table in enumerate(tables, 1):
            clickable_ref = create_clickable_reference(i, table, "Tableau")
            modified_text = modified_text.replace(f"[Tableau {i}]", clickable_ref)
    
    return modified_text


def display_with_document_opener(response_text: str, sources: List[Dict], images: List[Dict] = None, tables: List[Dict] = None):
    """
    Affiche la réponse avec références cliquables et système d'ouverture de documents
    
    Args:
        response_text: Texte de la réponse
        sources: Liste des sources
        images: Liste des images
        tables: Liste des tableaux
    """
    from .document_opener import generate_document_opener_javascript, register_document_opener_callback
    
    # Convertir les références en éléments cliquables
    processed_text = convert_source_references_to_clickable(response_text, sources, images, tables)
    
    # Enregistrer le callback pour l'ouverture des documents
    register_document_opener_callback()
    
    # Créer une interface Streamlit pour gérer les clics
    if sources or images or tables:
        with st.expander("🔗 Ouvrir documents", expanded=False):
            st.markdown("**Cliquez sur les références ci-dessus ou utilisez les boutons ci-dessous :**")
            
            # Boutons directs pour chaque source
            if sources:
                st.markdown("**Sources texte :**")
                cols = st.columns(min(len(sources), 4))
                for i, source in enumerate(sources):
                    col_idx = i % len(cols)
                    with cols[col_idx]:
                        if st.button(f"Source {i+1}", key=f"btn_source_{i+1}"):
                            from .document_opener import get_document_path, open_document_at_page
                            doc_path = get_document_path(source)
                            if doc_path:
                                page_num = None
                                if source.get('page_display'):
                                    try:
                                        page_num = int(source['page_display'].split('-')[0])
                                    except:
                                        pass
                                elif source.get('pages'):
                                    page_num = source['pages'][0]
                                
                                success = open_document_at_page(doc_path, page_num)
                                if success:
                                    st.success(f"Document ouvert : Source {i+1}")
                                else:
                                    st.error("Impossible d'ouvrir le document")
                            else:
                                st.error("Chemin du document non trouvé")
            
            # Boutons pour les images
            if images:
                st.markdown("**Images :**")
                cols = st.columns(min(len(images), 4))
                for i, image in enumerate(images):
                    col_idx = i % len(cols)
                    with cols[col_idx]:
                        if st.button(f"Image {i+1}", key=f"btn_image_{i+1}"):
                            from .document_opener import get_document_path, open_document_at_page
                            doc_path = get_document_path(image)
                            if doc_path:
                                page_num = None
                                if image.get('metadata', {}).get('page'):
                                    try:
                                        page_num = int(image['metadata']['page'])
                                    except:
                                        pass
                                
                                success = open_document_at_page(doc_path, page_num)
                                if success:
                                    st.success(f"Document ouvert : Image {i+1}")
                                else:
                                    st.error("Impossible d'ouvrir le document")
                            else:
                                st.error("Chemin du document non trouvé")
            
            # Boutons pour les tableaux
            if tables:
                st.markdown("**Tableaux :**")
                cols = st.columns(min(len(tables), 4))
                for i, table in enumerate(tables):
                    col_idx = i % len(cols)
                    with cols[col_idx]:
                        if st.button(f"Tableau {i+1}", key=f"btn_table_{i+1}"):
                            from .document_opener import get_document_path, open_document_at_page
                            doc_path = get_document_path(table)
                            if doc_path:
                                page_num = None
                                if table.get('metadata', {}).get('page'):
                                    try:
                                        page_num = int(table['metadata']['page'])
                                    except:
                                        pass
                                
                                success = open_document_at_page(doc_path, page_num)
                                if success:
                                    st.success(f"Document ouvert : Tableau {i+1}")
                                else:
                                    st.error("Impossible d'ouvrir le document")
                            else:
                                st.error("Chemin du document non trouvé")
    
    return processed_text


def inject_vancouver_citations(response_text: str, sources: List[Dict]) -> str:
    """
    Injecte des citations style Vancouver dans le texte de réponse avec liens hypertextes
    Exemple: "selon le règlement R046 [1]" où [1] est cliquable
    
    Args:
        response_text: Texte de la réponse
        sources: Liste des sources
        
    Returns:
        Texte avec citations Vancouver intégrées et liens hypertextes
    """
    if not sources:
        return response_text
    
    # Créer un mapping des sources pour les citations
    citation_map = {}
    for i, source in enumerate(sources, 1):
        regulation_code = source.get('regulation_code', '')
        document_name = source.get('document_name', '')
        pages = source.get('pages', [])
        page_display = source.get('page_display', '')
        source_link = source.get('source_link', '')
        
        # Créer le lien hypertexte pour la citation inline
        if source_link:
            citation_link = f'<a href="{source_link}" onclick="window.open(this.href); return false;" style="color: #0a6ebd; text-decoration: none; font-weight: bold;" target="_blank">[{i}]</a>'
        else:
            citation_link = f'<span style="color: #0a6ebd; font-weight: bold;">[{i}]</span>'
        
        # Format pour la référence complète
        if regulation_code and regulation_code != 'Code inconnu':
            base_citation = regulation_code
            if document_name and '- ' in document_name:
                version_part = document_name.split('- ')[-1]
                if version_part:
                    base_citation += f" - {version_part}"
            
            if page_display:
                citation_text = f"{base_citation} (p.{page_display})"
            elif pages:
                if len(pages) == 1:
                    citation_text = f"{base_citation} (p.{pages[0]})"
                else:
                    citation_text = f"{base_citation} (p.{pages[0]}-{pages[-1]})"
            else:
                citation_text = base_citation
        else:
            citation_text = document_name
        
        citation_map[i] = {
            'number': i,
            'text': citation_text,
            'link': citation_link,
            'source_link': source_link,
            'regulation_code': regulation_code
        }
    
    # Stratégies pour insérer les citations dans le texte
    modified_text = response_text
    citations_used = set()
    
    # 1. Rechercher et remplacer les mentions de codes de réglementation
    for i, citation_info in citation_map.items():
        regulation_code = citation_info.get('regulation_code', '')
        if regulation_code and regulation_code != 'Code inconnu':
            # Patterns de recherche sophistiqués
            patterns = [
                rf"\b{re.escape(regulation_code)}\b(?!\s*\[)",  # Code sans citation existante
                rf"\bRèglement\s+{re.escape(regulation_code)}\b(?!\s*\[)",  # "Règlement R046"
                rf"\b{re.escape(regulation_code.replace('R', 'R\\.'))}\b(?!\s*\[)",  # "R.046"
            ]
            
            for pattern in patterns:
                matches = list(re.finditer(pattern, modified_text, re.IGNORECASE))
                if matches and i not in citations_used:
                    # Remplacer la première occurrence
                    match = matches[0]
                    replacement = f"{match.group()} {citation_info['link']}"
                    modified_text = re.sub(pattern, replacement, modified_text, count=1, flags=re.IGNORECASE)
                    citations_used.add(i)
                    break
    
    # 2. Ajouter des citations contextuelles pour les sources non utilisées
    contextual_patterns = [
        (r"selon (la|le)\s+réglementation", "selon la réglementation"),
        (r"conformément (à|aux)\s+exigences", "conformément aux exigences"), 
        (r"tel que (défini|spécifié|requis)", "tel que défini"),
        (r"(l'|la|le)\s+norme\s+(spécifie|indique|exige)", "la norme spécifie"),
        (r"(doit|doivent)\s+(être|respecter|satisfaire)", "doit être"),
        (r"(est|sont)\s+(défini|spécifié|requis)", "est défini")
    ]
    
    for pattern, context in contextual_patterns:
        matches = list(re.finditer(pattern, modified_text, re.IGNORECASE))
        if matches:
            # Trouver une citation non utilisée
            unused_citations = [i for i in citation_map.keys() if i not in citations_used]
            if unused_citations:
                match = matches[0]
                citation_i = unused_citations[0]
                end_pos = match.end()
                modified_text = modified_text[:end_pos] + f" {citation_map[citation_i]['link']}" + modified_text[end_pos:]
                citations_used.add(citation_i)
                break
    
    # 3. Ajouter la liste des références à la fin
    if citation_map:
        references_html = "\n\n---\n\n**Références :**\n\n"
        for i, citation_info in citation_map.items():
            references_html += f"{citation_info['link']} {citation_info['text']}\n"
        
        modified_text += references_html
    
    return modified_text


def create_citation_mapping(sources: List[Dict]) -> Dict[int, Dict]:
    """
    Crée un mapping des sources pour les citations Vancouver
    
    Args:
        sources: Liste des sources
        
    Returns:
        Dictionnaire avec les informations de citation pour chaque source
    """
    citation_map = {}
    for i, source in enumerate(sources, 1):
        regulation_code = source.get('regulation_code', '')
        document_name = source.get('document_name', '')
        pages = source.get('pages', [])
        page_display = source.get('page_display', '')
        source_link = source.get('source_link', '')
        
        # Format d'affichage compact
        if regulation_code and regulation_code != 'Code inconnu':
            display_name = regulation_code
            if document_name and '- ' in document_name:
                version_part = document_name.split('- ')[-1]
                if version_part:
                    display_name += f" - {version_part}"
        else:
            display_name = document_name
        
        # Informations de page
        if page_display:
            page_info = f"p.{page_display}"
        elif pages:
            if len(pages) == 1:
                page_info = f"p.{pages[0]}"
            else:
                page_info = f"p.{pages[0]}-{pages[-1]}"
        else:
            page_info = ""
        
        citation_map[i] = {
            'number': i,
            'display_name': display_name,
            'page_info': page_info,
            'source_link': source_link,
            'regulation_code': regulation_code
        }
    
    return citation_map


def display_citation_preview(sources: List[Dict]):
    """
    Affiche un aperçu des citations qui seront générées
    
    Args:
        sources: Liste des sources
    """
    if not sources:
        return
    
    citation_map = create_citation_mapping(sources)
    
    with st.expander("🔗 Aperçu des citations", expanded=False):
        st.markdown("**Citations qui seront utilisées :**")
        
        for i, citation_info in citation_map.items():
            display_name = citation_info['display_name']
            page_info = citation_info['page_info']
            source_link = citation_info['source_link']
            
            if source_link:
                link_html = f'<a href="{source_link}" onclick="window.open(this.href); return false;" style="color: #0a6ebd; text-decoration: none; font-weight: bold;" target="_blank">[{i}]</a>'
            else:
                link_html = f'<span style="color: #0a6ebd; font-weight: bold;">[{i}]</span>'
            
            citation_text = f"{display_name}"
            if page_info:
                citation_text += f" ({page_info})"
            
            st.markdown(f"{link_html} {citation_text}", unsafe_allow_html=True)