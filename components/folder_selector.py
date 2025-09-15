"""
Composant de sélection de dossiers pour Streamlit
Alternative à st.file_uploader pour les dossiers
"""

import streamlit as st
import os
from pathlib import Path
from typing import Optional


def st_folder_picker(
    label: str = "Sélectionner un dossier",
    initial_path: Optional[str] = None,
    key: Optional[str] = None,
    help: Optional[str] = None
) -> Optional[str]:
    """
    Composant de sélection de dossier interactif
    
    Args:
        label: Texte du label
        initial_path: Chemin initial (par défaut: dossier courant)
        key: Clé unique pour le composant
        help: Texte d'aide
    
    Returns:
        Chemin du dossier sélectionné ou None
    """
    
    # Initialiser le chemin
    if initial_path is None:
        initial_path = os.getcwd()
    
    # Clé unique pour éviter les conflits
    if key is None:
        key = f"folder_picker_{hash(label)}"
    
    # État du composant
    state_key = f"{key}_state"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            'current_path': str(Path(initial_path).resolve()),
            'selected_path': None,
            'show_browser': False
        }
    
    state = st.session_state[state_key]
    
    st.markdown(f"**{label}**")
    if help:
        st.caption(help)
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # Afficher le chemin sélectionné ou demander une saisie manuelle
        display_path = state.get('selected_path', state['current_path'])
        manual_path = st.text_input(
            "Chemin du dossier",
            value=display_path,
            key=f"{key}_manual_input",
            label_visibility="collapsed"
        )
        
        # Mettre à jour si l'utilisateur modifie manuellement
        if manual_path != display_path:
            if os.path.isdir(manual_path):
                state['selected_path'] = os.path.abspath(manual_path)
                state['current_path'] = os.path.abspath(manual_path)
            else:
                st.error("Dossier inexistant")
    
    with col2:
        if st.button("Parcourir", key=f"{key}_browse_btn", help="Ouvrir le navigateur de dossiers"):
            state['show_browser'] = not state['show_browser']
    
    with col3:
        if st.button("Actuel", key=f"{key}_current_btn", help="Utiliser le dossier courant"):
            state['selected_path'] = os.getcwd()
            state['current_path'] = os.getcwd()
            state['show_browser'] = False
    
    # Navigateur de dossiers interactif
    if state['show_browser']:
        st.markdown("---")
        _render_folder_browser(state, key)
    
    # Validation du dossier sélectionné
    selected_path = state.get('selected_path')
    if selected_path and os.path.isdir(selected_path):
        # Afficher les informations du dossier
        try:
            pdf_files = [f for f in os.listdir(selected_path) if f.lower().endswith('.pdf')]
            st.success(f"Dossier valide: {len(pdf_files)} fichiers PDF trouvés")
            
            if pdf_files:
                with st.expander(f"Aperçu des fichiers ({min(len(pdf_files), 5)} premiers)", expanded=False):
                    for pdf_file in pdf_files[:5]:
                        st.write(f"• {pdf_file}")
                    if len(pdf_files) > 5:
                        st.write(f"... et {len(pdf_files) - 5} autres")
            
            return selected_path
            
        except PermissionError:
            st.error("Accès refusé à ce dossier")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du dossier: {e}")
    
    return None


def _render_folder_browser(state: dict, key: str):
    """Rendu du navigateur de dossiers interactif"""
    
    current_path = Path(state['current_path'])
    
    # Navigation vers le parent
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if current_path.parent != current_path:  # Pas à la racine
            if st.button("Parent", key=f"{key}_parent_btn"):
                state['current_path'] = str(current_path.parent)
                st.rerun()
    
    with col2:
        st.write(f"**Dossier actuel**: `{current_path}`")
    
    # Liste des dossiers
    try:
        # Récupérer les dossiers
        folders = []
        if current_path.exists() and current_path.is_dir():
            for item in sorted(current_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    folders.append(item)
        
        if folders:
            st.markdown("**Dossiers disponibles:**")
            
            # Organiser en colonnes pour un affichage compact
            cols_per_row = 2
            for i in range(0, len(folders), cols_per_row):
                cols = st.columns(cols_per_row)
                
                for j, folder in enumerate(folders[i:i + cols_per_row]):
                    with cols[j]:
                        folder_name = folder.name
                        if len(folder_name) > 25:
                            folder_name = folder_name[:22] + "..."
                        
                        # Bouton pour naviguer dans le dossier
                        if st.button(
                            f"{folder_name}",
                            key=f"{key}_folder_{i+j}_{folder.name}",
                            help=f"Naviguer vers: {folder}"
                        ):
                            state['current_path'] = str(folder)
                            st.rerun()
        else:
            st.info("Aucun sous-dossier trouvé")
        
        # Bouton pour sélectionner le dossier actuel
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button(
                f"Sélectionner ce dossier",
                key=f"{key}_select_current",
                type="primary",
                help=f"Utiliser: {current_path}"
            ):
                state['selected_path'] = str(current_path)
                state['show_browser'] = False
                st.rerun()
    
    except PermissionError:
        st.error("Accès refusé à ce dossier")
    except Exception as e:
        st.error(f"Erreur: {e}")


def st_folder_picker_simple(
    label: str = "Chemin du dossier",
    default_path: str = "./Data",
    key: Optional[str] = None
) -> str:
    """
    Version simplifiée du sélecteur de dossier avec suggestion intelligente
    
    Args:
        label: Label du champ
        default_path: Chemin par défaut
        key: Clé unique
    
    Returns:
        Chemin du dossier sélectionné
    """
    
    if key is None:
        key = f"simple_folder_picker_{hash(label)}"
    
    # Suggestions de dossiers courants
    common_folders = []
    
    # Ajouter des suggestions basées sur l'environnement
    suggestions = ["./Data", "./Documents", "./Downloads", os.getcwd()]
    
    for folder in suggestions:
        if os.path.isdir(folder):
            common_folders.append(os.path.abspath(folder))
    
    # Interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        folder_path = st.text_input(
            label,
            value=default_path,
            key=f"{key}_input",
            help="Chemin absolu ou relatif vers le dossier"
        )
    
    with col2:
        # Menu déroulant avec suggestions
        if common_folders:
            st.markdown("**Suggestions:**")
            suggestion = st.selectbox(
                "Dossiers suggérés",
                options=[""] + common_folders,
                format_func=lambda x: "Choisir..." if x == "" else os.path.basename(x) or x,
                key=f"{key}_suggestions",
                label_visibility="collapsed"
            )
            
            if suggestion and suggestion != folder_path:
                st.session_state[f"{key}_input"] = suggestion
                st.rerun()
    
    # Validation en temps réel
    if folder_path:
        if os.path.isdir(folder_path):
            try:
                pdf_count = len([f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')])
                st.success(f"Dossier valide - {pdf_count} fichiers PDF")
            except Exception:
                st.warning("Dossier valide mais inaccessible")
        else:
            st.error("Dossier inexistant")
    
    return folder_path


# Exemple d'utilisation
if __name__ == "__main__":
    st.title("Test Folder Picker")
    
    st.subheader("Version complète avec navigateur")
    selected = st_folder_picker(
        label="Sélectionner le dossier de données",
        initial_path="./Data",
        help="Choisissez le dossier contenant vos fichiers PDF"
    )
    
    if selected:
        st.write(f"**Dossier sélectionné**: {selected}")
    
    st.divider()
    
    st.subheader("Version simplifiée")
    simple_path = st_folder_picker_simple(
        label="Dossier de travail",
        default_path="./Data"
    )
    
    st.write(f"**Chemin**: {simple_path}")