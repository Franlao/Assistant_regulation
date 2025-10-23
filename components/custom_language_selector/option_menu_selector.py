"""
Sélecteur de langue utilisant streamlit-option-menu avec icônes Icons8
Solution recommandée - Utilise le composant streamlit-option-menu
"""
import streamlit as st

# Vérifier si streamlit-option-menu est installé
try:
    from streamlit_option_menu import option_menu
    OPTION_MENU_AVAILABLE = True
except ImportError:
    OPTION_MENU_AVAILABLE = False
    st.error("Le composant streamlit-option-menu n'est pas installé. Exécutez: pip install streamlit-option-menu")


def render_option_menu_language_selector(current_language="fr", key="option_menu_lang_selector"):
    """
    Sélecteur de langue avec streamlit-option-menu et icônes Bootstrap/Unicode

    Args:
        current_language (str): Langue actuelle ('fr' ou 'en')
        key (str): Clé unique pour le composant

    Returns:
        str: La langue sélectionnée ('fr' ou 'en')
    """
    if not OPTION_MENU_AVAILABLE:
        # Fallback vers un selectbox simple
        return st.selectbox(
            "Language",
            options=['fr', 'en'],
            format_func=lambda x: x.upper(),
            index=['fr', 'en'].index(current_language),
            key=key,
            label_visibility="collapsed"
        )

    # Configuration des langues avec des emojis drapeaux
    languages = {
        'fr': {
            'label': 'FR',
            'icon': '🇫🇷',  # Emoji drapeau France
            'flag_url': 'https://img.icons8.com/?size=20&id=3muzEmi4dpD5&format=png'
        },
        'en': {
            'label': 'EN',
            'icon': '🇺🇸',  # Emoji drapeau USA
            'flag_url': 'https://img.icons8.com/?size=20&id=ShNNs7i8tXQF&format=png&color=000000'
        }
    }

    # Index de la langue actuelle
    current_index = list(languages.keys()).index(current_language)

    # CSS personnalisé pour un style ultraminimaliste
    custom_styles = {
        "container": {
            "padding": "0px",
            "background-color": "transparent",
            "border": "none",
            "box-shadow": "none"
        },
        "icon": {
            "color": "inherit",
            "font-size": "1.2em"
        },
        "nav-link": {
            "font-size": "0.9em",
            "text-align": "center",
            "margin": "0px",
            "padding": "4px 8px",
            "background-color": "transparent",
            "border": "none",
            "border-radius": "4px"
        },
        "nav-link-selected": {
            "background-color": "rgba(255,255,255,0.1)",
            "border": "none"
        }
    }

    # Sélecteur horizontal avec icônes
    selected_lang = option_menu(
        menu_title=None,  # Pas de titre
        options=list(languages.keys()),
        icons=[languages[lang]['icon'] for lang in languages.keys()],
        default_index=current_index,
        orientation="horizontal",
        styles=custom_styles,
        key=key
    )

    return selected_lang


def render_inline_flag_selector(current_language="fr", key="inline_flag_selector"):
    """
    Version ultra-simple avec HTML inline et icônes Icons8
    """
    # URLs des icônes Icons8
    france_icon = "https://img.icons8.com/?size=18&id=3muzEmi4dpD5&format=png"
    gb_icon = "https://img.icons8.com/?size=18&id=ShNNs7i8tXQF&format=png&color=000000"

    # HTML avec icônes cliquables
    st.markdown(f"""
    <div style="display: flex; gap: 8px; align-items: center; justify-content: center; margin: -10px 0;">
        <div onclick="selectLanguage('fr', '{key}')"
             style="cursor: pointer; padding: 4px; border-radius: 4px;
                    {'background: rgba(255,255,255,0.2);' if current_language == 'fr' else ''}
                    transition: all 0.15s ease;"
             onmouseover="this.style.opacity='0.7'"
             onmouseout="this.style.opacity='1'">
            <img src="{france_icon}" style="width: 18px; height: 18px;" alt="FR">
        </div>
        <div onclick="selectLanguage('en', '{key}')"
             style="cursor: pointer; padding: 4px; border-radius: 4px;
                    {'background: rgba(255,255,255,0.2);' if current_language == 'en' else ''}
                    transition: all 0.15s ease;"
             onmouseover="this.style.opacity='0.7'"
             onmouseout="this.style.opacity='1'">
            <img src="{gb_icon}" style="width: 18px; height: 18px;" alt="EN">
        </div>
    </div>

    <script>
    function selectLanguage(lang, key) {{
        // Stocker la sélection
        sessionStorage.setItem('selected_language_' + key, lang);

        // Déclencher un événement personnalisé
        const event = new CustomEvent('languageSelected', {{
            detail: {{ language: lang, key: key }}
        }});
        window.dispatchEvent(event);

        // Recharger la page pour appliquer le changement
        // Note: Dans une vraie app, on utiliserait st.rerun() côté Python
        console.log('Language selected:', lang);
    }}

    // Restaurer la sélection depuis sessionStorage
    const savedLang = sessionStorage.getItem('selected_language_{key}');
    if (savedLang) {{
        console.log('Restored language:', savedLang);
    }}
    </script>
    """, unsafe_allow_html=True)

    # Selectbox caché pour la logique Streamlit
    selected_language = st.selectbox(
        "Hidden Language",
        options=['fr', 'en'],
        index=['fr', 'en'].index(current_language),
        key=f"hidden_{key}",
        label_visibility="collapsed"
    )

    # CSS pour cacher le selectbox
    st.markdown("""
    <style>
    div[data-testid="stSelectbox"]:has(select[aria-label*="Hidden Language"]) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    return selected_language


def install_option_menu():
    """
    Instructions pour installer streamlit-option-menu
    """
    st.info("""
    Pour utiliser le sélecteur de langue avec icônes, installez le composant :

    ```bash
    pip install streamlit-option-menu
    ```

    Puis redémarrez votre application Streamlit.
    """)