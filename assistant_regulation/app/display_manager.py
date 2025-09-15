"""
Module de gestion de l'affichage des éléments (sources, images, tableaux, métriques)
"""
import streamlit as st
import pandas as pd
import uuid


def display_sources(sources):
    """Affiche les sources de façon formatée"""
    if not sources:
        return
        
    with st.expander("Sources utilisées", expanded=False):
        for i, source in enumerate(sources):
            try:
                # Formatage sécurisé des pages
                pages_value = source.get('pages', 'N/A')
                if isinstance(pages_value, list):
                    pages_str = ', '.join(map(str, pages_value))
                elif pages_value is not None:
                    pages_str = str(pages_value)
                else:
                    pages_str = 'N/A'
                
                regulation = source.get('regulation', 'N/A')
                section = source.get('section', 'N/A')
                text = source.get('text', source.get('content', ''))
                
                st.markdown(f"""
                <div class="source-citation">
                    <strong>Source {i+1}:</strong> {regulation}, Section {section} (Pages {pages_str})
                    <div style="margin-top: 5px; font-style: italic;">{text}</div>
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Erreur lors de l'affichage de la source {i+1}: {str(e)}")
                st.code(str(source))


def display_images(images, max_height=300, section_key=None):
    """
    Affiche les images de façon élégante avec taille contrôlée
    
    Args:
        images: Liste des images à afficher
        max_height: Hauteur maximale des images en pixels
        section_key: Clé unique pour identifier cette section d'images
    """
    # Générer une clé unique si elle n'est pas fournie
    if section_key is None:
        section_key = f"img_section_{str(uuid.uuid4())[:8]}"
        
    if not images:
        st.info("Aucune image disponible")
        return
        
    # Affichage minimal du nombre d'images
    with st.expander(f"Images disponibles ({len(images)})", expanded=False):
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
            st.warning("Aucune image disponible")
            return
        
        # Permettre à l'utilisateur d'ajuster la taille des images
        col1, col2 = st.columns([1, 3])
        with col1:
            size_options = ["Petite", "Moyenne", "Grande"]
            size_values = {"Petite": 200, "Moyenne": 400, "Grande": 600}
            
            selected_size = st.radio(
                "Taille des images",
                options=size_options,
                index=0,  # Default to small
                key=f"img_size_{section_key}"
            )
            max_height = size_values[selected_size]
        
        # Configuration responsive - plus d'images par ligne sur petits écrans
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
                                caption=None,
                                width='stretch'
                            )
                        
                        # Description tronquée courte
                        short_desc = description[:20] + ("..." if len(description) > 20 else "")
                        st.caption(f"<p style='color: white; font-size: 0.8em;'> {short_desc} </p>", unsafe_allow_html=True)
                        
                        # Bouton de détail plus discret
                        if st.button(f"📝", key=f"detail_btn_{section_key}_{i}", help="Voir détail"):
                            st.session_state[f"selected_image_{section_key}"] = {
                                "url": image_url,
                                "description": description
                            }
                    except Exception as e:
                        st.error(f"Erreur: {str(e)}")
        
        # Afficher l'image détaillée si sélectionnée
        if st.session_state[f"selected_image_{section_key}"]:
            with st.container():
                st.divider()
                sel_img = st.session_state[f"selected_image_{section_key}"]
                
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.subheader("Détail de l'image")
                with col2:
                    if st.button("❌", key=f"close_detail_{section_key}", help="Fermer"):
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
                        st.image(sel_img["url"], width='stretch')
                    
                    # Description complète dans un container discret
                    with st.container():
                        st.markdown(f"**Description:** {sel_img['description']}")
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")


def extract_table_from_text(text):
    """
    Extrait les tableaux du texte et les convertit en DataFrame pandas.
    Gère à la fois les tableaux représentés comme des listes et les tableaux textuels.
    """
    import re
    import ast
    
    def ensure_valid_column_names(columns):
        """S'assure que les noms de colonnes sont valides pour pandas"""
        if columns is None:
            return [f"Col_{i}" for i in range(20)]  # Valeur par défaut
            
        cols = list(columns)  # Convertir en liste
        
        # Remplacer les None et chaînes vides
        for i in range(len(cols)):
            if cols[i] is None or cols[i] == "":
                cols[i] = f"Col_{i}"
        
        # Assurer l'unicité
        seen = {}
        for i in range(len(cols)):
            if cols[i] in seen:
                seen[cols[i]] += 1
                cols[i] = f"{cols[i]}_{seen[cols[i]]}"
            else:
                seen[cols[i]] = 0
                
        return cols
    
    # Cas 1: Tableau représenté comme une liste Python dans le texte
    table_pattern = r'\[\[(.*?)\]\]'
    matches = re.findall(table_pattern, text, re.DOTALL)
    
    if matches:
        try:
            # Essayer de reconstruire la structure de liste
            table_str = "[[" + matches[0] + "]]"
            # Évaluer de façon sécurisée la chaîne en structure Python
            table_data = ast.literal_eval(table_str)
            
            # Convertir en DataFrame
            if isinstance(table_data, list) and all(isinstance(row, list) for row in table_data):
                if len(table_data) > 1:  # S'assurer qu'il y a au moins un en-tête et une ligne
                    columns = ensure_valid_column_names(table_data[0] if table_data[0] else None)
                    return pd.DataFrame(table_data[1:], columns=columns)
        except Exception:
            # Erreur silencieuse (cas 1)
            pass
    
    # Cas 2: Tableau avec format plus complexe (plusieurs blocs)
    table_blocks = re.findall(r'\[\[(.*?)\]\]', text, re.DOTALL)
    if len(table_blocks) > 1:
        try:
            all_rows = []
            for block in table_blocks:
                block_str = "[[" + block + "]]"
                block_data = ast.literal_eval(block_str)
                if isinstance(block_data, list) and all(isinstance(row, list) for row in block_data):
                    all_rows.extend(block_data)
            
            if all_rows and len(all_rows) > 1:  # S'assurer qu'il y a au moins un en-tête et une ligne
                columns = ensure_valid_column_names(all_rows[0] if all_rows[0] else None)
                return pd.DataFrame(all_rows[1:], columns=columns)
        except Exception:
            # Erreur silencieuse (cas 2)
            pass
    
    # Cas 3: Tableau formaté en texte avec espaces ou pipes
    lines = text.strip().split('\n')
    if len(lines) > 1:
        # Détecter si c'est un tableau formaté avec des | ou des espaces
        if '|' in lines[0]:
            # Tableau formaté avec des pipes (markdown ou similaire)
            try:
                rows = []
                for line in lines:
                    if '|' in line and not line.strip().startswith('-'):
                        cells = [cell.strip() for cell in line.split('|')]
                        # Éliminer les cellules vides aux extrémités (causées par | au début/fin)
                        if cells and cells[0] == '':
                            cells = cells[1:]
                        if cells and cells[-1] == '':
                            cells = cells[:-1]
                        if cells:
                            rows.append(cells)
                
                if len(rows) > 1:  # Au moins une ligne d'en-tête et une ligne de données
                    # Normaliser la taille des lignes
                    max_cols = max(len(row) for row in rows)
                    for row in rows:
                        while len(row) < max_cols:
                            row.append("")  # Ajouter des cellules vides si nécessaire
                    
                    columns = ensure_valid_column_names(rows[0])
                    return pd.DataFrame(rows[1:], columns=columns)
            except Exception:
                # Erreur silencieuse (cas 3)
                pass
    
    # Si aucun tableau n'a pu être extrait, retourner None
    return None


def display_tables(tables):
    """Affiche les tableaux de façon formatée avec détection améliorée"""
    if not tables:
        return
        
    st.markdown("<h4 style='color: white;'>Tableaux</h4>", unsafe_allow_html=True)
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
        with st.expander(f"Tableau {i+1}", expanded=False):
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
                    st.dataframe(df, width='stretch')
                    continue
            
            # Étape 2: Traiter différents formats de données structurées
            try:
                if isinstance(content, list) and all(isinstance(row, list) for row in content):
                    # Cas d'une matrice (liste de listes)
                    if content and len(content) > 0:
                        # Corriger les noms de colonnes
                        column_names = fix_column_names(content[0] if len(content) > 0 else None)
                        df = pd.DataFrame(content[1:], columns=column_names)
                        st.dataframe(df, width='stretch')
                    else:
                        st.write("Tableau vide")
                elif isinstance(content, list) and all(isinstance(row, dict) for row in content):
                    # Cas d'une liste de dictionnaires
                    df = pd.DataFrame(content)
                    st.dataframe(df, width='stretch')
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
                                    st.dataframe(df, width='stretch')
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


def display_regulation_metrics():
    """Affiche des métriques sur les réglementations disponibles"""
    # Données d'exemple - dans une implémentation réelle, ces données viendraient de votre base
    regulations = [
        {"code": "R046", "title": "Dispositifs de vision indirecte", "version": "06 series"},
        {"code": "R107", "title": "Véhicules des catégories M2 et M3", "version": "07 series"},
        {"code": "R048", "title": "Installation des dispositifs d'éclairage", "version": "05 series"},
    ]
    
    st.markdown("<h3 style='color: white;'>Réglementations disponibles</h3>", unsafe_allow_html=True)
    
    cols = st.columns(len(regulations))
    for i, reg in enumerate(regulations):
        with cols[i]:
            st.markdown(f"""
            <div class="info-card" style="text-align: center;">
                <div style="font-size: 1.5em; font-weight: bold; color: var(--primary);">{reg['code']}</div>
                <div style="margin: 5px 0; font-size: 0.9em;">{reg['title']}</div>
                <div><span class="badge badge-blue">{reg['version']}</span></div>
            </div>
            """, unsafe_allow_html=True)


def create_info_card(title, content, badge_text=None, badge_color="blue"):
    """Crée une carte d'information stylisée"""
    badge_html = ""
    if badge_text:
        badge_colors = {
            "blue": "#0a6ebd",
            "green": "#2ecc71", 
            "orange": "#f39c12",
            "red": "#e74c3c"
        }
        color = badge_colors.get(badge_color, "#0a6ebd")
        badge_html = f'<span class="badge" style="background-color: {color}; color: white;">{badge_text}</span>'
    
    return f"""
    <div class="info-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; color: var(--primary);">{title}</h4>
            {badge_html}
        </div>
        <div>{content}</div>
    </div>
    """


def display_loading_indicator(text="Chargement..."):
    """Affiche un indicateur de chargement"""
    return f"""
    <div style="display: flex; align-items: center; justify-content: center; padding: 20px;">
        <div class="loader"></div>
        <span style="margin-left: 15px; color: var(--text);">{text}</span>
    </div>
    """


def create_expandable_section(title, content, expanded=False, key=None):
    """Crée une section expandable avec style personnalisé"""
    with st.expander(title, expanded=expanded):
        if isinstance(content, str):
            st.markdown(content, unsafe_allow_html=True)
        else:
            content()  # Appel de fonction si c'est un callable


def display_data_summary(data_stats):
    """Affiche un résumé des données disponibles"""
    st.markdown("### 📊 Résumé des données")
    
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("Documents", data_stats.get("documents", 0))
    
    with cols[1]:
        st.metric("Images", data_stats.get("images", 0))
    
    with cols[2]:
        st.metric("Tableaux", data_stats.get("tables", 0))
    
    with cols[3]:
        st.metric("Sources", data_stats.get("sources", 0))


def generate_unique_key(prefix="key"):
    """Génère une clé unique pour les composants Streamlit"""
    return f"{prefix}_{str(uuid.uuid4())[:8]}" 