"""
Utilities for Streamlit application
"""
import streamlit as st
import base64
import pandas as pd
import re
import ast
from datetime import datetime
from typing import Dict, List, Any, Optional


def get_current_time():
    """Renvoie l'horodatage actuel formaté"""
    return datetime.now().strftime("%H:%M:%S")


def add_bg_from_local(image_file):
    """Ajoute un arrière-plan à partir d'un fichier local"""
    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode()
    
    st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(
            to right,
            rgba(34, 34, 34, 0.9),
            rgba(54, 54, 54, 0.8),
            rgba(54, 54, 54, 0.6)
        ), url(data:image/png;base64,{encoded_string});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    /* Barre latérale */
    [data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.8);
        color: #222222;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        font-family: 'Roboto', sans-serif;
    }}

    /* Style du logo */
    .sidebar-logo {{
        border-radius: 50%;
        width: 120px;
        height: 120px;
        object-fit: cover;
        margin: 0 auto;
        display: block;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}

    /* Style des boutons */
    .stButton>button {{
        color: #ffffff;
        background: linear-gradient(90deg, #FF5722, #FF9800);
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 16px;
        border-radius: 10px;
        font-weight: bold;
        transition: background 0.3s ease;
    }}

    .stButton>button:hover {{
        background: linear-gradient(90deg, #FF9800, #FF5722);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }}

    /* Style des messages dans le chat */
    .stChatMessage {{
        background: rgba(255, 255, 255, 0.15) !important;
        border-radius: 15px !important;
        padding: 15px !important;
        font-family: 'Roboto', sans-serif;
        font-size: 15px;
        margin-bottom: 1rem !important;
    }}

    /* Zone de saisie de texte */
    .stChatInput {{
        background: rgba(255, 255, 255, 0.8);
        color: #E0E0E0;
        border: 1px solid linear-gradient(90deg, #FF5722, #FF9800);
        border-radius: 10px;
        padding: 0.75rem;
        width: 100%;
    }}
    .st-emotion-cache-1r7m7vo, 
    .st-emotion-cache-1r7m7vo > div {{
    width: 100% !important;
    max-width: 100% !important;
    }}
    .stChatInputContainer {{
    width: 100% !important;
    }}
    div[data-baseweb="textarea"] {{
    width: 100% !important;
    }}
    .stChatInputContainer {{
    width: 100% !important;
    }}
    /* Expanders pour les sources */
    .streamlit-expanderHeader {{
        background-color: rgba(0, 0, 0, 0.8) !important;
        color: #E0E0E0 !important;
        font-weight: bold !important;
        border-radius: 10px;
    }}

    .streamlit-expanderContent {{
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #FFFFFF !important;
    }}
    
    .stAppHeader{{
        background-color: rgba(225, 225, 225, 0.1) !important;
        color: #E0E0E0 !important;
        font-weight: bold !important;
        border-radius: 10px;
        padding: 0.5rem !important;
    }}
    .st-emotion-cache-128upt6{{
        background-color: rgba(225, 225, 225, 0.1) !important;
    }}
    
    </style>
    """,
    unsafe_allow_html=True
)


def load_css():
    """Charge les styles CSS personnalisés"""
    st.markdown("""
    <style>
        /* Couleurs de base */
        :root {
            --primary: #0a6ebd;
            --secondary: #3498db;
            --accent: #2ecc71;
            --background: #f8f9fa;
            --card: #ffffff;
            --text: #ffffff;
            --light-text: #7f8c8d;
            --border: #e0e0e0;
        }
        
        /* Style général */
        .main {
            background-color: var(--background);
        }
        
        h1, h2, h3 {
            color: var(--text);
        }
        
        /* Personnalisation des messages de chat */
        .user-message {
            background-color: #e6f3ff; 
            border-radius: 15px;
            padding: 10px 15px;
            margin: 10px 0;
            border-left: 5px solid var(--primary);
            line-height: 1.5;
        }
        
        .assistant-message {
            background-color: #f0f7f0;
            border-radius: 15px;
            padding: 10px 15px;
            margin: 10px 0;
            border-left: 5px solid var(--accent);
            line-height: 1.5;
        }
        
        /* Cartes d'information */
        .info-card {
            background-color: var(--card);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border: 1px solid var(--border);
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 5px;
        }
        
        .badge-blue {
            background-color: #cfe2ff;
            color: #0d6efd;
        }
        
        .badge-green {
            background-color: #d1e7dd;
            color: #198754;
        }
        
        .badge-orange {
            background-color: #fff3cd;
            color: #fd7e14;
        }
        
        /* Source citation */
        .source-citation {
            background-color: #f8f9fa;
            border-left: 3px solid #6c757d;
            padding: 8px 12px;
            margin: 5px 0;
            font-size: 0.9em;
        }
        
        /* Image container */
        .image-container {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .image-caption {
            background-color: rgba(0,0,0,0.03);
            padding: 8px;
            font-size: 0.9em;
            border-top: 1px solid var(--border);
        }
        
        /* Boutons d'action */
        .action-button {
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            font-size: 14px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .action-button:hover {
            background-color: var(--secondary);
        }
        /* Mode badges */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 8px;
            margin-right: 5px;
        }

        .badge-blue {
            background-color: #0a6ebd;
            color: white;
        }

        .badge-green {
            background-color: #2ecc71;
            color: white;
        }

        /* Expander pour l'analyse */
        .stExpander {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
        }

        .stExpander > div[role="button"] {
            color: white !important;
        }
        
        /* Loader personnalisé */
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0; }
        100% { opacity: 1; }
        }
        
        .cursor {
            animation: blink 1s linear infinite;
            color: #0a6ebd;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)


def display_message(message, is_user=False, t=None):
    """Affiche un message formaté dans l'historique de conversation"""
    timestamp = message.get("timestamp", get_current_time())
    content = message.get("content", "")
    
    if is_user:
        st.markdown(f"""
        <div class="user-message">
            <div style="display: flex; justify-content: space-between;">
                <strong>{t('user') if t else 'Utilisateur'}</strong>
                <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
            </div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="assistant-message">
            <div style="display: flex; justify-content: space-between;">
                <strong>{t('assistant') if t else 'Assistant'}</strong>
                <span style="color: #888; font-size: 0.8em;">{timestamp}</span>
            </div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)


def extract_table_from_text(text):
    """
    Extrait les tableaux du texte et les convertit en DataFrame pandas.
    Gère à la fois les tableaux représentés comme des listes et les tableaux textuels.
    """
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
        except Exception as e:
            print(f"Erreur lors de l'extraction du tableau (cas 1): {e}")
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
        except Exception as e:
            print(f"Erreur lors de l'extraction du tableau (cas 2): {e}")
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
            except Exception as e:
                print(f"Erreur lors de l'extraction du tableau (cas 3): {e}")
                pass
    
    # Si aucun tableau n'a pu être extrait, retourner None
    return None


def export_conversation_to_pdf(messages):
    """Génère un PDF de la conversation (simulation - téléchargerait normalement un PDF)"""
    conversation_text = "CONVERSATION AVEC L'ASSISTANT RÉGLEMENTAIRE\n\n"
    
    for msg in messages:
        role = "Vous" if msg["role"] == "user" else "Assistant"
        conversation_text += f"[{msg.get('timestamp', '')}] {role}:\n"
        conversation_text += f"{msg['content']}\n\n"
    
    # Encodage pour le téléchargement
    b64 = base64.b64encode(conversation_text.encode()).decode()
    
    # Bouton de téléchargement
    href = f'<a href="data:file/txt;base64,{b64}" download="conversation_reglementaire.txt" class="action-button">Télécharger la conversation</a>'
    st.markdown(href, unsafe_allow_html=True)


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


def generate_unique_key(prefix="key"):
    """Génère une clé unique"""
    import uuid
    return f"{prefix}_{str(uuid.uuid4())[:8]}"


class APIHealthChecker:
    """Vérification de l'état des API"""
    
    @staticmethod
    def check_mistral_api():
        """Vérifie l'état de l'API Mistral"""
        try:
            import httpx
            response = httpx.get("https://api.mistral.ai/", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def check_ollama_api(base_url="http://localhost:11434"):
        """Vérifie l'état de l'API Ollama"""
        try:
            import httpx
            response = httpx.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def get_api_status():
        """Obtient l'état de toutes les API"""
        return {
            "mistral": APIHealthChecker.check_mistral_api(),
            "ollama": APIHealthChecker.check_ollama_api()
        } 