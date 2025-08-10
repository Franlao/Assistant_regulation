"""
Module de gestion des styles CSS et de l'interface utilisateur
"""
import streamlit as st
import base64


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

    /* Masquer la navigation multipage par défaut au-dessus du logo,
       mais conserver l'entête pour garder le bouton de repli/extension */
    [data-testid="stSidebarNav"] {{ display: none !important; }}
    
    /* Réduire l'espace en haut de la sidebar */
    [data-testid="stSidebarHeader"] {{
        height: auto !important;
        min-height: 0 !important;
        padding: 0 !important;
    }}
    
    /* Ajuster le contenu de la sidebar pour qu'il soit plus haut */
    [data-testid="stSidebarContent"] {{
        padding-top: 1rem !important;
    }}
    
    /* Positionner le bouton de repli/extension */
    [data-testid="stSidebarCollapsedControl"] {{
        top: 0.5rem !important;
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


def load_main_css():
    """Charge les styles CSS principaux de l'application"""
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
        
        .badge-purple {
            background-color: #9b59b6;
            color: white;
        }
        
        .badge-gray {
            background-color: #6c757d;
            color: white;
        }
        
        .badge-orange {
            background-color: #fff3cd;
            color: #fd7e14;
        }
        
        /* Source citation moderne */
        .source-citation {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(248, 249, 250, 0.95));
            border: 1px solid rgba(230, 230, 230, 0.8);
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .source-citation:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            transform: translateY(-1px);
        }
        
        /* Badges de confiance pour sources */
        .confidence-badge {
            position: absolute;
            top: 12px;
            right: 12px;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: white;
        }
        
        .confidence-high { background: #2ecc71; }
        .confidence-medium { background: #f39c12; }
        .confidence-low { background: #e74c3c; }
        
        /* En-tête de source */
        .source-header {
            color: #2c3e50;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .source-index {
            background: linear-gradient(90deg, #3498db, #2980b9);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
        }
        
        /* Métadonnées de source */
        .source-meta {
            color: #7f8c8d;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        
        /* Contenu de source */
        .source-content {
            color: #2c3e50;
            font-size: 13px;
            line-height: 1.5;
            border-left: 3px solid #3498db;
            padding: 10px 12px;
            margin: 8px 0;
            background: rgba(52, 152, 219, 0.04);
            border-radius: 0 6px 6px 0;
            font-style: italic;
        }
        
        /* Ligne décorative */
        .source-decoration {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #3498db, transparent);
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


def load_table_css():
    """Charge les styles CSS spécifiques aux tableaux"""
    st.markdown("""
    <style>
    [data-testid="stExpander"] {
        background-color: white !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def apply_custom_theme(theme_name="default"):
    """Applique un thème personnalisé"""
    themes = {
        "default": {
            "primary": "#0a6ebd",
            "secondary": "#3498db",
            "accent": "#2ecc71"
        },
        "dark": {
            "primary": "#2c3e50",
            "secondary": "#34495e", 
            "accent": "#e74c3c"
        },
        "light": {
            "primary": "#3498db",
            "secondary": "#2980b9",
            "accent": "#27ae60"
        }
    }
    
    if theme_name not in themes:
        theme_name = "default"
    
    theme = themes[theme_name]
    
    st.markdown(f"""
    <style>
        :root {{
            --primary: {theme["primary"]};
            --secondary: {theme["secondary"]};
            --accent: {theme["accent"]};
        }}
    </style>
    """, unsafe_allow_html=True)


def create_status_badge(status, text):
    """Crée un badge de statut coloré"""
    colors = {
        "online": "#2ecc71",
        "offline": "#e74c3c", 
        "warning": "#f39c12",
        "info": "#3498db"
    }
    
    color = colors.get(status, "#95a5a6")
    
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 5px;
    ">{text}</span>
    """


def create_gradient_text(text, color1="#FF5722", color2="#FF9800"):
    """Crée un texte avec gradient"""
    return f"""
    <span style="
        background: linear-gradient(90deg, {color1}, {color2});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: bold;
    ">{text}</span>
    """


def load_all_styles():
    """Charge tous les styles de l'application"""
    load_main_css()
    load_table_css() 