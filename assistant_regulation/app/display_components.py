"""
Composants d'affichage pour l'application Streamlit
"""
import streamlit as st
import pandas as pd
import time
import base64
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from .streamlit_utils import get_current_time, extract_table_from_text, generate_unique_key


def display_fullscreen_pdf(file_path, page_number, document_name, source_id):
    """Affiche le PDF en fullscreen avec modal Streamlit"""
    # S'assurer que page_number est un entier
    try:
        if isinstance(page_number, str):
            page_number = int(page_number)
        elif page_number is None:
            page_number = 1
        page_number = int(page_number)  # Force conversion
    except (ValueError, TypeError):
        page_number = 1
    
    try:
        import fitz  # PyMuPDF
    except ImportError:
        st.error("PyMuPDF n'est pas installé. Exécutez: pip install PyMuPDF")
        return
    
    # Créer un modal fullscreen avec st.dialog (Streamlit >= 1.31)
    @st.dialog(f"{document_name} - Page {page_number}", width="large")
    def show_pdf():
        if not os.path.exists(file_path):
            st.error("Document non accessible")
            return
            
        doc = fitz.open(file_path)
        if page_number > len(doc):
            st.error(f"Page {page_number} non trouvée")
            doc.close()
            return
            
        page = doc[page_number - 1]
        
        # Convertir avec haute résolution pour le fullscreen
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))  # Zoom 3x pour fullscreen
        img_data = pix.tobytes("png")
        img_b64 = base64.b64encode(img_data).decode()
        
        # Affichage fullscreen optimisé
        st.markdown(f"""
        <div style="text-align: center; width: 100%; height: 80vh; overflow: auto;">
            <img src="data:image/png;base64,{img_b64}" 
                 style="max-width: 100%; height: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
        </div>
        """, unsafe_allow_html=True)
        
        # Informations en bas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Page", f"{page_number}/{len(doc)}")
        with col2:
            st.metric("Résolution", f"{pix.width}x{pix.height}")
        with col3:
            with open(file_path, "rb") as pdf_file:
                st.download_button(
                    "⬇️ Télécharger PDF",
                    data=pdf_file.read(),
                    file_name=os.path.basename(file_path),
                    mime="application/pdf"
                )
        
        doc.close()
    
    show_pdf()


def display_inline_pdf_excerpt(file_path, page_number, source_id):
    """Affiche un extrait du PDF directement dans l'interface"""
    # S'assurer que page_number est un entier
    try:
        if isinstance(page_number, str):
            page_number = int(page_number)
        elif page_number is None:
            page_number = 1
        page_number = int(page_number)  # Force conversion
    except (ValueError, TypeError):
        page_number = 1
    
    try:
        # Importer PyMuPDF (fitz) avec gestion d'erreur
        try:
            import fitz  # PyMuPDF
        except ImportError:
            st.error("PyMuPDF n'est pas installé. Exécutez: pip install PyMuPDF")
            return
        
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            st.error(f"Fichier non trouvé : {file_path}")
            return
            
        # Ouvrir le PDF et extraire la page spécifique
        doc = fitz.open(file_path)
        
        if page_number > len(doc):
            st.error(f"Page {page_number} non trouvée (PDF a {len(doc)} pages)")
            doc.close()
            return
            
        page = doc[page_number - 1]  # Les pages sont indexées à partir de 0
        
        # Convertir la page en image avec une résolution plus élevée
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # Zoom 2x pour meilleure qualité
        img_data = pix.tobytes("png")
        
        # Encoder en base64
        img_b64 = base64.b64encode(img_data).decode()
        
        # Afficher avec un expander
        with st.expander(f"Aperçu - {os.path.basename(file_path)} - Page {page_number}", expanded=True):
            # Afficher l'image de la page
            st.markdown(f'''
            <div style="text-align: center; margin: 10px 0;">
                <img src="data:image/png;base64,{img_b64}" 
                     style="width: 100%; max-width: 700px; border: 2px solid #e0e0e0; border-radius: 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            </div>
            ''', unsafe_allow_html=True)
            
            # Informations sur le document
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Page:** {page_number}/{len(doc)}")
            with col2:
                st.info(f"**Taille:** {pix.width}x{pix.height} px")
            with col3:
                # Bouton pour télécharger le PDF complet
                with open(file_path, "rb") as pdf_file:
                    st.download_button(
                        "Télécharger PDF",
                        data=pdf_file.read(),
                        file_name=os.path.basename(file_path),
                        mime="application/pdf",
                        key=f"download_pdf_{source_id}",
                        help="Télécharger le document PDF complet"
                    )
        
        doc.close()
        
    except Exception as e:
        st.error(f"Impossible d'afficher l'aperçu PDF : {e}")
        # Afficher les détails de l'erreur en mode développement
        with st.expander("Détails de l'erreur", expanded=False):
            st.exception(e)


def display_sources(sources, t, compact=False):
    """Affiche les sources avec un design moderne et subtil"""
    if not sources:
        st.warning("Aucune source disponible")
        return
    
    # Affichage silencieux (pas de debug dans l'UI)
    
    # Statistiques des sources
    total_sources = len(sources)
    unique_regs = len(set(source.get('regulation', 'Unknown') for source in sources))
    
    # En-tête avec statistiques
    header_text = f"📚 {total_sources} source{'s' if total_sources > 1 else ''}"
    if unique_regs > 1:
        header_text += f" • {unique_regs} réglementations"
    
    with st.expander(header_text, expanded=False):
        # Mode compact pour affichage dans l'historique
        if compact and total_sources > 3:
            st.info(f"Affichage des 3 premières sources sur {total_sources} total(es)")
            display_sources = sources[:3]
        else:
            display_sources = sources
        
        # Organisation par réglementation
        sources_by_reg = {}
        for source in display_sources:
            reg = source.get('regulation', 'Réglementation inconnue')
            if reg not in sources_by_reg:
                sources_by_reg[reg] = []
            sources_by_reg[reg].append(source)
        
        # Affichage groupé par réglementation
        for reg_name, reg_sources in sources_by_reg.items():
            if len(sources_by_reg) > 1:
                st.markdown(f"**📋 {reg_name}**")
            
            # Colonnes pour affichage en grille
            if len(reg_sources) > 1:
                cols = st.columns(min(2, len(reg_sources)))
                for idx, source in enumerate(reg_sources):
                    with cols[idx % 2]:
                        _render_source_card_minimal(source, idx + 1)
            else:
                _render_source_card_minimal(reg_sources[0], 1)
            
            if len(sources_by_reg) > 1:
                st.divider()
        
        # Lien pour voir toutes les sources si mode compact
        if compact and total_sources > 3:
            st.caption("💡 Sources complètes disponibles dans la réponse générée")


def _render_source_card(source, index):
    """Rend une carte de source individuelle avec design moderne"""
    import html
    
    regulation = source.get('regulation', 'Réglementation')
    section = source.get('section', 'Section inconnue') 
    pages_raw = source.get('pages', 'Page inconnue')
    document_name = source.get('document_name', source.get('document', 'Document inconnu'))
    source_link = source.get('source_link', '')
    confidence = source.get('confidence', 0)
    
    # Formatage sécurisé des pages
    if isinstance(pages_raw, list):
        if len(pages_raw) == 1:
            pages_str = str(pages_raw[0])
        elif len(pages_raw) > 1:
            pages_str = f"{pages_raw[0]}-{pages_raw[-1]}"
        else:
            pages_str = 'Page inconnue'
    elif pages_raw is not None:
        pages_str = str(pages_raw)
    else:
        pages_str = 'Page inconnue'
    
    # Nettoyer et échapper le texte pour éviter les problèmes HTML
    regulation = html.escape(str(regulation))
    section = html.escape(str(section))
    pages = html.escape(pages_str)
    document_name = html.escape(str(document_name))
    
    # Couleur du badge de confiance
    if confidence >= 0.8:
        confidence_color = "#2ecc71"  # Vert
        confidence_label = "Haute"
    elif confidence >= 0.6:
        confidence_color = "#f39c12"  # Orange
        confidence_label = "Moyenne"
    else:
        confidence_color = "#e74c3c"  # Rouge
        confidence_label = "Faible"
    
    # Utiliser une approche plus simple avec les composants Streamlit natifs
    with st.container():
        # En-tête avec badge de confiance
        col_header, col_badge = st.columns([4, 1])
        
        with col_header:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 249, 250, 0.95));
                border: 1px solid rgba(230, 230, 230, 0.8);
                border-radius: 12px 12px 0 0;
                padding: 12px 16px;
                margin-bottom: 0;
            ">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="
                        background: linear-gradient(90deg, #3498db, #2980b9);
                        color: white;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 700;
                    ">#{index}</span>
                    <strong style="color: #2c3e50; font-size: 14px;">{regulation}</strong>
                </div>
                <div style="color: #7f8c8d; font-size: 12px;">
                    📄 {section} • 📍 {pages}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_badge:
            st.markdown(f"""
            <div style="text-align: right; padding: 12px 0;">
                <span style="
                    background: {confidence_color};
                    color: white;
                    padding: 4px 8px;
                    border-radius: 20px;
                    font-size: 10px;
                    font-weight: 600;
                    text-transform: uppercase;
                ">{confidence_label}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Lien vers le document avec bouton d'ouverture
        if source_link:
            # Extraire le chemin du fichier depuis le source_link
            file_path = source_link.replace('file:///', '').split('#')[0]
            file_path = file_path.replace('%20', ' ')  # Décoder les espaces
            import urllib.parse
            file_path = urllib.parse.unquote(file_path)
            
            # Créer des colonnes pour les boutons
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div style="
                    background: rgba(52, 152, 219, 0.04);
                    border: 1px solid rgba(230, 230, 230, 0.8);
                    border-radius: 8px;
                    padding: 12px;
                    margin-top: 0;
                    border-left: 4px solid #3498db;
                ">
                    <div style="
                        color: #2c3e50;
                        font-size: 13px;
                        line-height: 1.6;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    ">
                        <span style="
                            background: linear-gradient(90deg, #27ae60, #2ecc71);
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 10px;
                            font-weight: 600;
                            text-transform: uppercase;
                        ">📄</span>
                        <span style="font-weight: 500;">{document_name}</span>
                        <span style="color: #7f8c8d; font-size: 11px;">• Page {pages}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Debug UI supprimé
                
                # Bouton pour aperçu PDF
                if st.button(f"Aperçu", key=f"preview_pdf_{index}", help=f"Aperçu de {document_name}"):
                    st.write("Bouton Aperçu cliqué!")
                    try:
                        if os.path.exists(file_path):
                            # Formatage sécurisé du numéro de page
                            page_raw = source.get('page', source.get('pages', 1))
                            
                            try:
                                if isinstance(page_raw, list):
                                    page_num = int(page_raw[0]) if page_raw else 1
                                else:
                                    page_num = int(page_raw) if page_raw is not None else 1
                            except (ValueError, TypeError):
                                page_num = 1
                            
                            display_inline_pdf_excerpt(file_path, page_num, index)
                        else:
                            st.error(f"Fichier non trouvé : {file_path}")
                    except Exception as e:
                        st.error(f"Erreur d'aperçu : {str(e)}")
                
                # Bouton secondaire pour ouvrir le fichier (fallback)
                if st.button(f"Ouvrir", key=f"open_file_{index}", help=f"Ouvrir {document_name} dans l'application par défaut"):
                    try:
                        import subprocess
                        import platform
                        
                        # Vérifier que le fichier existe
                        if os.path.exists(file_path):
                            # Ouvrir selon le système d'exploitation
                            if platform.system() == "Windows":
                                subprocess.run(["start", file_path], shell=True, check=True)
                            elif platform.system() == "Darwin":  # macOS
                                subprocess.run(["open", file_path], check=True)
                            else:  # Linux
                                subprocess.run(["xdg-open", file_path], check=True)
                            
                            st.success(f"Ouverture de {document_name}")
                        else:
                            st.error(f"Fichier non trouvé : {file_path}")
                                
                    except Exception as e:
                        st.error(f"Erreur d'ouverture : {str(e)}")
                        # Bouton de fallback pour copier le lien
                        if st.button(f"Copier le lien", key=f"copy_link_error_{index}"):
                            st.code(source_link)
                            st.info("Copiez ce lien dans votre navigateur")
        else:
            # Fallback si pas de lien disponible
            st.markdown(f"""
            <div style="
                background: rgba(243, 156, 18, 0.04);
                border: 1px solid rgba(230, 230, 230, 0.8);
                border-top: none;
                border-radius: 0 0 12px 12px;
                padding: 16px;
                margin-top: 0;
                border-left: 4px solid #f39c12;
            ">
                <div style="
                    color: #2c3e50;
                    font-size: 13px;
                    line-height: 1.6;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="
                        background: #f39c12;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 20px;
                        font-size: 11px;
                        font-weight: 600;
                        text-transform: uppercase;
                    ">⚠️ Document</span>
                    <span style="
                        color: #7f8c8d;
                        font-style: italic;
                        flex: 1;
                        padding: 8px 12px;
                        background: rgba(243, 156, 18, 0.1);
                        border-radius: 8px;
                        border: 1px solid rgba(243, 156, 18, 0.2);
                    ">
                        📄 {document_name} (lien non disponible)
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Espacement
        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)


def _render_source_card_minimal(source, index):
    """Carte de source minimaliste et efficace - Version moderne 2024"""
    import html
    
    document_name = source.get('document_name', source.get('document', 'Document'))
    pages_raw = source.get('pages', source.get('page', '?'))
    source_link = source.get('source_link', '')
    text_preview = source.get('text_preview', source.get('full_text', ''))
    
    # Formatage sécurisé des pages
    if isinstance(pages_raw, list):
        if len(pages_raw) == 1:
            pages = str(pages_raw[0])
        elif len(pages_raw) > 1:
            pages = f"{pages_raw[0]}-{pages_raw[-1]}"
        else:
            pages = '?'
    elif pages_raw is not None:
        pages = str(pages_raw)
    else:
        pages = '?'
    
    if not text_preview or not isinstance(text_preview, str):
        text_preview = "Aperçu du contenu non disponible"
    elif len(text_preview.strip()) > 80:
        text_preview = text_preview.strip()[:80] + "..."
    else:
        text_preview = text_preview.strip()
    
    # Extraire le chemin du fichier
    file_path = None
    if source_link:
        file_path = source_link.replace('file:///', '').split('#')[0]
        file_path = file_path.replace('%20', ' ')
        import urllib.parse
        file_path = urllib.parse.unquote(file_path)
        
        # Si le fichier n'existe pas, essayer de le trouver dans le dossier Data/
        if not os.path.exists(file_path):
            # Extraire juste le nom du fichier  
            filename = os.path.basename(file_path)
            # Chercher dans le dossier Data/
            data_path = os.path.join(os.getcwd(), 'Data', filename)
            if os.path.exists(data_path):
                file_path = data_path
    
    # Design minimaliste clean inspiré des standards 2024
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Design propre avec composants Streamlit natifs
            with st.container():
                # Titre du document (en gras)
                st.markdown(f"**{document_name}**")
                
                # Page (plus petit, gris)
                st.caption(f"Page {pages}")
                
                # Aperçu du contenu (italique)
                if text_preview:
                    st.markdown(f"*{text_preview}*")
                else:
                    st.markdown("*Contenu disponible*")
                
                # Ligne de séparation subtile
                st.markdown("---")
        
        with col2:
            # Bouton unique et efficace
            if file_path and st.button("👁 Voir", key=f"view_{index}", help="Voir le document"):
                if os.path.exists(file_path):
                    # Formatage sécurisé du numéro de page
                    page_raw = source.get('page', source.get('pages', 1))
                    
                    try:
                        if isinstance(page_raw, list):
                            page_num = int(page_raw[0]) if page_raw else 1
                        else:
                            page_num = int(page_raw) if page_raw is not None else 1
                    except (ValueError, TypeError):
                        page_num = 1
                    
                    display_fullscreen_pdf(file_path, page_num, document_name, index)
                else:
                    st.error("Document inaccessible")


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
    
    # Statistiques des tableaux
    total_tables = len(tables)
    
    # Encapsuler dans un expander global comme les sources
    with st.expander(f"📊 {total_tables} tableau{'x' if total_tables > 1 else ''}", expanded=False):
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
                    from assistant_regulation.app.streamlit_utils import get_intelligent_routing_badge
                    # Pour les chunks "text", chunk_content est une string, pas un dict
                    # Les données de routage sont dans analysis_data
                    routing_decision = analysis_data.get("routing_decision", {}) if isinstance(analysis_data, dict) else {}
                    mode_badge = get_intelligent_routing_badge(analysis_data, routing_decision)
                    
                    # Préparer le contenu avec traitement amélioré des formules et markdown
                    import re
                    processed_text = response_text
                    
                    # Convertir d'abord le markdown en HTML
                    processed_text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', processed_text)  # Gras
                    processed_text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', processed_text)  # Italique
                    
                    # Convertir les formules LaTeX en format MathJax
                    processed_text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'$$\\frac{\1}{\2}$$', processed_text)
                    processed_text = re.sub(r'\\\(([^)]+)\\\)', r'$\1$', processed_text)
                    # Traiter les fractions simples avec des chiffres et des variables
                    processed_text = re.sub(r'\b(\d+)\s*/\s*([a-zA-Z]+)\b', r'$$\\frac{\1}{\2}$$', processed_text)
                    processed_text = re.sub(r'\b(\d+)\s*/\s*(\d+)\b', r'$$\\frac{\1}{\2}$$', processed_text)
                    # Traiter les expressions mathématiques entre [ ]
                    processed_text = re.sub(r'\[\s*([^[\]]*(?:frac|=|\+|\-|\*|/)[^[\]]*)\s*\]', r'$$\1$$', processed_text)
                    
                    # Afficher le message complet avec HTML et markdown
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">{t('assistant')}</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{processed_text}<span class="cursor">▋</span></div>
                    </div>
                    """, unsafe_allow_html=True)
            
            elif chunk_type == "error":
                st.error(f"{t('error_occurred')} {chunk_content}")
                return None
            
            elif chunk_type == "done":
                # Finaliser l'affichage sans le curseur  
                with response_container.container():
                    from assistant_regulation.app.streamlit_utils import get_intelligent_routing_badge
                    routing_decision = chunk_content.get("routing_decision", {})
                    mode_badge = get_intelligent_routing_badge(analysis_data, routing_decision)
                    
                    # Traitement final du texte avec markdown et formules LaTeX
                    import re
                    final_text = response_text
                    
                    # Convertir d'abord le markdown en HTML
                    final_text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', final_text)  # Gras
                    final_text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', final_text)  # Italique
                    
                    # Convertir les formules LaTeX en format MathJax
                    final_text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'$$\\frac{\1}{\2}$$', final_text)
                    final_text = re.sub(r'\\\(([^)]+)\\\)', r'$\1$', final_text)
                    # Traiter les fractions simples avec des chiffres et des variables
                    final_text = re.sub(r'\b(\d+)\s*/\s*([a-zA-Z]+)\b', r'$$\\frac{\1}{\2}$$', final_text)
                    final_text = re.sub(r'\b(\d+)\s*/\s*(\d+)\b', r'$$\\frac{\1}{\2}$$', final_text)
                    # Traiter les expressions mathématiques entre [ ]
                    final_text = re.sub(r'\[\s*([^[\]]*(?:frac|=|\+|\-|\*|/)[^[\]]*)\s*\]', r'$$\1$$', final_text)
                    
                    st.markdown(f"""
                    <div class="assistant-message">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #333;">{t('assistant')}</strong>
                                {mode_badge}
                            </div>
                            <span style="color: #888; font-size: 0.8em;">{get_current_time()}</span>
                        </div>
                        <div style="color: #333; margin-top: 10px;">{final_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Nettoyer l'indicateur d'analyse
        analysis_placeholder.empty()
        
        # Retourner les données finales
        routing_decision = None
        if analysis_data:
            routing_decision = analysis_data.get("routing_decision", {})
        
        return {
            "response": response_text,
            "analysis": analysis_data,
            "routing_decision": routing_decision,
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
    
    # Afficher un badge intelligent indiquant le mode de réponse
    from assistant_regulation.app.streamlit_utils import get_intelligent_routing_badge
    routing_decision = response_data.get("routing_decision", {})
    mode_badge = get_intelligent_routing_badge(analysis, routing_decision)
    
    # Garder les explications pour compatibilité
    if needs_rag:
        mode_explanation = t("explanation_rag")
    else:
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