"""
Module de gestion de l'extraction et du traitement des données
"""
import streamlit as st
import pandas as pd
import base64
import json
import re
import ast
from datetime import datetime

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


def export_conversation_to_pdf():
    """Génère un PDF de la conversation (simulation - téléchargerait normalement un PDF)"""
    # Ici vous pourriez utiliser une bibliothèque comme reportlab pour générer un vrai PDF
    # Pour l'exemple, nous allons créer un fichier texte simple
    
    conversation_text = "CONVERSATION AVEC L'ASSISTANT RÉGLEMENTAIRE\n\n"
    
    for msg in st.session_state.messages:
        role = "Vous" if msg["role"] == "user" else "Assistant"
        conversation_text += f"[{msg.get('timestamp', '')}] {role}:\n"
        conversation_text += f"{msg['content']}\n\n"
    
    # Encodage pour le téléchargement
    b64 = base64.b64encode(conversation_text.encode()).decode()
    
    # Bouton de téléchargement
    href = f'<a href="data:file/txt;base64,{b64}" download="conversation_reglementaire.txt" class="action-button">Télécharger la conversation</a>'
    st.markdown(href, unsafe_allow_html=True)


def export_conversation_to_json():
    """Exporte la conversation au format JSON"""
    if 'messages' not in st.session_state or not st.session_state.messages:
        return None
    
    export_data = {
        "export_date": datetime.now().isoformat(),
        "session_id": st.session_state.get("session_id", "unknown"),
        "messages": st.session_state.messages,
        "settings": st.session_state.get("settings", {})
    }
    
    return json.dumps(export_data, indent=2, ensure_ascii=False)


def export_conversation_to_text():
    """Exporte la conversation au format texte simple"""
    if 'messages' not in st.session_state or not st.session_state.messages:
        return "Aucune conversation à exporter."
    
    conversation_text = "CONVERSATION AVEC L'ASSISTANT RÉGLEMENTAIRE\n"
    conversation_text += "=" * 60 + "\n"
    conversation_text += f"Date d'export: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    conversation_text += f"Session ID: {st.session_state.get('session_id', 'N/A')}\n"
    conversation_text += "=" * 60 + "\n\n"
    
    for i, msg in enumerate(st.session_state.messages, 1):
        role = "VOUS" if msg["role"] == "user" else "ASSISTANT"
        timestamp = msg.get("timestamp", "")
        content = msg.get("content", "")
        
        conversation_text += f"MESSAGE {i:03d} - [{timestamp}] {role}:\n"
        conversation_text += "-" * 40 + "\n"
        conversation_text += f"{content}\n\n"
    
    return conversation_text


def create_download_link(data, filename, file_type="text"):
    """Crée un lien de téléchargement pour les données"""
    if file_type == "json":
        mime_type = "application/json"
        b64_data = base64.b64encode(data.encode('utf-8')).decode()
    else:  # text
        mime_type = "text/plain"
        b64_data = base64.b64encode(data.encode('utf-8')).decode()
    
    href = f'<a href="data:{mime_type};base64,{b64_data}" download="{filename}" class="action-button">📥 Télécharger {filename}</a>'
    return href


def parse_structured_data(data_string):
    """Parse des données structurées à partir d'une chaîne"""
    try:
        # Essayer JSON en premier
        return json.loads(data_string)
    except json.JSONDecodeError:
        try:
            # Essayer ast.literal_eval pour les structures Python
            return ast.literal_eval(data_string)
        except (ValueError, SyntaxError):
            # Retourner la chaîne telle quelle si aucun parsing ne fonctionne
            return data_string


def extract_urls_from_text(text):
    """Extrait les URLs d'un texte"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return urls


def extract_regulation_references(text):
    """Extrait les références de réglementations d'un texte"""
    # Pattern pour capturer les références comme R107, ECE R46, etc.
    reg_pattern = r'(?:ECE\s+)?R(\d+)(?:\s*-\s*\d+)?(?:\s+series)?'
    references = re.findall(reg_pattern, text, re.IGNORECASE)
    return [f"R{ref}" for ref in references]


def clean_text_content(text):
    """Nettoie le contenu textuel pour l'affichage"""
    if not isinstance(text, str):
        return str(text)
    
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    # Supprimer les caractères de contrôle
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Nettoyer les sauts de ligne multiples
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def validate_image_url(url):
    """Valide qu'une URL d'image est correcte"""
    if not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Vérifier les formats d'URL acceptés
    if url.startswith(('http://', 'https://', 'data:image/')):
        return True
    
    return False


def extract_metadata_from_source(source):
    """Extrait les métadonnées d'une source"""
    metadata = {}
    
    if isinstance(source, dict):
        metadata['regulation'] = source.get('regulation', 'N/A')
        metadata['section'] = source.get('section', 'N/A')
        metadata['pages'] = source.get('pages', 'N/A')
        metadata['score'] = source.get('score', 0.0)
        metadata['text_preview'] = source.get('text', '')[:100] + "..." if source.get('text') else ""
    
    return metadata


def process_search_results(results):
    """Traite et normalise les résultats de recherche"""
    processed = {
        'sources': [],
        'images': [],
        'tables': [],
        'total_count': 0
    }
    
    if not results:
        return processed
    
    # Traiter les sources
    sources = results.get('sources', [])
    for source in sources:
        if isinstance(source, dict):
            processed['sources'].append({
                'regulation': source.get('regulation', 'N/A'),
                'section': source.get('section', 'N/A'),
                'pages': source.get('pages', 'N/A'),
                'text': clean_text_content(source.get('text', '')),
                'score': source.get('score', 0.0)
            })
    
    # Traiter les images
    images = results.get('images', [])
    for img in images:
        if isinstance(img, dict) and validate_image_url(img.get('url', '')):
            processed['images'].append({
                'url': img.get('url'),
                'description': clean_text_content(img.get('description', '')),
                'page': img.get('page', 'N/A')
            })
    
    # Traiter les tableaux
    tables = results.get('tables', [])
    for table in tables:
        if isinstance(table, dict):
            processed['tables'].append({
                'content': table.get('documents', ''),
                'page': table.get('page', 'N/A'),
                'type': table.get('type', 'table')
            })
    
    processed['total_count'] = len(processed['sources']) + len(processed['images']) + len(processed['tables'])
    
    return processed


def create_data_backup():
    """Crée une sauvegarde des données de session"""
    backup_data = {
        'timestamp': datetime.now().isoformat(),
        'session_id': st.session_state.get('session_id', ''),
        'messages': st.session_state.get('messages', []),
        'settings': st.session_state.get('settings', {}),
        'app_version': '2.0.0'
    }
    
    return json.dumps(backup_data, indent=2, ensure_ascii=False)


def restore_data_from_backup(backup_json):
    """Restaure les données à partir d'une sauvegarde"""
    try:
        backup_data = json.loads(backup_json)
        
        # Restaurer les messages
        if 'messages' in backup_data:
            st.session_state.messages = backup_data['messages']
        
        # Restaurer les paramètres (avec précaution)
        if 'settings' in backup_data:
            current_settings = st.session_state.get('settings', {})
            for key, value in backup_data['settings'].items():
                if key in current_settings:  # Ne restaurer que les clés existantes
                    st.session_state.settings[key] = value
        
        return True, "Données restaurées avec succès"
    
    except json.JSONDecodeError:
        return False, "Format de sauvegarde invalide"
    except Exception as e:
        return False, f"Erreur lors de la restauration: {str(e)}"


def get_data_statistics():
    """Retourne des statistiques sur les données disponibles"""
    stats = {
        'messages_count': len(st.session_state.get('messages', [])),
        'session_duration': "N/A",  # Calculé ailleurs
        'settings_count': len(st.session_state.get('settings', {})),
        'memory_usage': "N/A"  # Peut être calculé si nécessaire
    }
    
    # Calculer la durée de session si possible
    messages = st.session_state.get('messages', [])
    if len(messages) >= 2:
        try:
            first_msg = messages[0].get('timestamp', '')
            last_msg = messages[-1].get('timestamp', '')
            if first_msg and last_msg:
                # Ici on pourrait calculer la différence de temps
                stats['session_duration'] = f"Du {first_msg} au {last_msg}"
        except:
            pass
    
    return stats 