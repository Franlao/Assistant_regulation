"""
Exemple d'intégration du composant d'authentification moderne
Remplace l'ancien système auth_components.py
"""

import streamlit as st
from components.modern_auth_component import ModernAuthManager, render_modern_login
from components.auth_components import SimpleAuth


def render_modern_auth_page():
    """
    Page d'authentification moderne - remplace render_login_form()
    """
    st.set_page_config(
        page_title="Authentification",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Style CSS pour masquer les éléments Streamlit par défaut
    st.markdown("""
    <style>
        .stApp > header {visibility: hidden;}
        .stApp > div[data-testid="stDecoration"] {visibility: hidden;}
        .stMainBlockContainer {padding-top: 0rem;}
        .stSidebar {display: none;}
        
        /* Masquer le footer Streamlit */
        footer {visibility: hidden;}
        footer:after {
            content:'Système d\'authentification sécurisé'; 
            visibility: visible;
            display: block;
            position: relative;
            color: #aaa;
            padding: 5px;
            top: 2px;
            text-align: center;
            font-size: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialiser le backend d'authentification
    auth_backend = SimpleAuth()
    
    # Créer le gestionnaire moderne
    auth_manager = ModernAuthManager(auth_backend)
    
    # Afficher le composant d'authentification
    if auth_manager.render_login(theme="dark", language="fr"):
        # Utilisateur authentifié avec succès
        user_info = auth_manager.get_user_info()
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 1rem; color: white; max-width: 400px; margin: 0 auto;">
                <h3>Connexion réussie</h3>
                <p>Redirection en cours...</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Redirection automatique vers la page principale
        st.rerun()


def render_modern_sidebar_user_info():
    """
    Affiche les informations utilisateur dans la sidebar - remplace render_user_info()
    """
    if not st.session_state.get("authenticated", False):
        return
    
    username = st.session_state.get("username", "Inconnu")
    user_role = st.session_state.get("user_role", "user")
    
    # Couleurs selon le rôle
    avatar_color = "#ef4444" if user_role == "admin" else "#3b82f6"
    badge_bg = "#fef2f2" if user_role == "admin" else "#eff6ff" 
    badge_color = "#dc2626" if user_role == "admin" else "#2563eb"
    badge_border = "#fecaca" if user_role == "admin" else "#bfdbfe"
    
    # Approche alternative avec components.html pour forcer le rendu
    import streamlit.components.v1 as components
    html_content = f"""
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    
    <div class="card-body p-3",style="
    border-radius: 15px;
    border: 1px solid #ccc;
    padding: 20px;
    background-color: #f0f2f6;
    overflow: hidden;
    height: 100%;
">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="avatar placeholder">
                    <div class="w-10 h-10 rounded-full" style="background: {avatar_color};">
                        <span class="text-white font-bold text-sm">{username[0].upper()}</span>
                    </div>
                </div>
                <div>
                    <div class="font-semibold text-base-content text-sm">{username}</div>
                    <div class="badge badge-sm" style="background: {badge_bg}; color: {badge_color}; border-color: {badge_border};">
                        {'Administrateur' if user_role == 'admin' else 'Utilisateur'}
                    </div>
                </div>
            </div>
            <button onclick="logout()" 
                    class="btn btn-ghost btn-sm btn-square" 
                    title="Se déconnecter">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
                </svg>
            </button>
        </div>
    </div>
    
    <script>
        function logout() {{
            // Utiliser une approche alternative avec window.name ou localStorage
            window.parent.sessionStorage.setItem('streamlit_logout', 'true');
            // Forcer un refresh de la page
            window.parent.location.reload();
        }}
    </script>
    """


    components.html(html_content, height=70)

    # CSS pour arrondir les bords du composant
    st.markdown("""
    <style>
        /* Arrondir les bords de l'iframe du composant HTML */
        .stStreamlitComponentV1 iframe {
            border-radius: 15px !important;
            overflow: hidden !important;
        }

        /* Alternative avec sélecteur plus spécifique */
        div[data-testid="stStreamlitComponentV1"] iframe {
            border-radius: 15px !important;
            overflow: hidden !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Vérifier le signal de déconnexion via JavaScript au chargement de la page
    logout_js = """
    <script>
        if (sessionStorage.getItem('streamlit_logout') === 'true') {
            sessionStorage.removeItem('streamlit_logout');
            // Déclencher la déconnexion directement
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({logout: true})
            }).then(() => {
                window.location.reload();
            });
        }
    </script>
    """
    st.markdown(logout_js, unsafe_allow_html=True)
    
    # Séparateur subtil
    st.markdown("""
    <div style="
        height: 1px; 
        background: linear-gradient(to right, transparent, #e5e7eb, transparent); 
        margin: 16px 0;
        opacity: 0.3;
    "></div>
    """, unsafe_allow_html=True)
    
    # CSS pour les composants DaisyUI et bouton subtil
    st.markdown("""
    <style>
        /* Style ultra-subtil pour le bouton de déconnexion */
        .stButton[key="sidebar_logout_trigger"] button {
            background-color: transparent !important;
            border: none !important;
            color: #ccc !important;
            font-size: 0.9rem !important;
            padding: 4px 8px !important;
            height: auto !important;
            min-height: auto !important;
            box-shadow: none !important;
            border-radius: 4px !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton[key="sidebar_logout_trigger"] button:hover {
            background-color: rgba(255, 0, 0, 0.05) !important;
            color: #999 !important;
            transform: scale(1.02) !important;
        }
        
        /* Ajustements pour l'intégration DaisyUI */
        .card {
            transition: all 0.2s ease;
            border-radius: 0.75rem;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        /* Animation pour l'avatar */
        .avatar .placeholder > div {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .avatar:hover .placeholder > div {
            transform: scale(1.1);
        }
        
        /* Style pour les stats */
        .stats {
            transition: all 0.2s ease;
            border-radius: 0.5rem;
        }
        
        .card:hover .stats {
            opacity: 1 !important;
            transform: scale(1.02);
        }
        
        /* DaisyUI divider styling */
        .divider {
            margin: 1rem 0;
            height: 1px;
            background: linear-gradient(to right, transparent, #e5e7eb, transparent);
        }
        
        /* Badge animations */
        .badge {
            transition: transform 0.2s ease;
        }
        
        .card:hover .badge {
            transform: scale(1.05);
        }
        
        /* Stats values animation */
        .stat-value {
            transition: color 0.2s ease;
        }
    </style>
    """, unsafe_allow_html=True)


def require_modern_authentication() -> bool:
    """
    Vérifie l'authentification moderne - remplace require_authentication()
    """
    if not st.session_state.get("authenticated", False):
        # Rediriger vers la page Login au lieu d'afficher le composant ici
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin: 2rem auto;
                max-width: 400px;
            ">
                <h3 style="color: #ef4444; margin-bottom: 12px;">Accès restreint</h3>
                <p style="color: #6b7280; margin-bottom: 16px;">Veuillez vous connecter pour accéder à cette page</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton pour aller à la page Login
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Aller à la page Login", type="primary", width='stretch'):
                st.session_state.selected_page = "Login"
                st.rerun()
        
        return False
    
    return True


def require_modern_admin_access() -> bool:
    """
    Vérifie l'accès administrateur moderne - remplace require_admin_access()
    """
    if not st.session_state.get("authenticated", False):
        # Rediriger vers la page Login
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin: 2rem auto;
                max-width: 400px;
            ">
                <h3 style="color: #ef4444; margin-bottom: 12px;">Accès administrateur requis</h3>
                <p style="color: #6b7280; margin-bottom: 16px;">Veuillez vous connecter avec un compte administrateur</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton pour aller à la page Login
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Aller à la page Login", type="primary", width='stretch', key="admin_login_btn"):
                st.session_state.selected_page = "Login"
                st.rerun()
                
        return False
    
    if st.session_state.get("user_role") != "admin":
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin: 2rem auto;
                max-width: 400px;
            ">
                <h3 style="color: #ef4444; margin-bottom: 12px;">Accès interdit</h3>
                <p style="color: #6b7280; margin-bottom: 16px;">Cette page est réservée aux administrateurs</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton pour aller à la page Login avec un compte admin
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Se connecter en Admin", type="primary", width='stretch', key="admin_access_btn"):
                st.session_state.selected_page = "Login"
                st.rerun()
                
        return False
    
    return True


def render_dedicated_login_page():
    """
    Page de connexion dédiée pour l'intégration dans app.py
    Utilise le même style que les autres pages
    """
    # Si déjà connecté, rediriger automatiquement vers Chat
    if st.session_state.get("authenticated", False):
        st.session_state.selected_page = "Chat"
        st.rerun()
        return
    
    # CSS pour optimiser l'affichage du composant
    st.markdown("""
    <style>
        /* Forcer la hauteur de tous les iframes des composants */
        iframe[src*="modern_auth_component"] {
            height: 750px !important;
            min-height: 750px !important;
        }
        
        /* Alternative avec sélecteur plus large */
        .stStreamlitComponentV1 iframe {
            height: 750px !important;
            min-height: 750px !important;
        }
        
        /* Réduire les marges pour donner plus d'espace */
        .stMainBlockContainer {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        
        /* Réduire l'espacement des colonnes */
        .stColumn {
            padding: 0 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    ## Titre centré exactement comme les autres pages
    #st.markdown("""
    #<div style="text-align: center; padding: 1rem 0;">
    #    <h1 style="color: #343a40; font-weight: 400; font-size: 2rem; margin: 0;">Authentification</h1>
    #    <p style="color: #6c757d; font-size: 1rem; margin: 0.5rem 0 0 0;">Connectez-vous pour accéder à l'Assistant Réglementaire</p>
    #</div>
    #""", unsafe_allow_html=True)
    
    # Centrer le composant d'authentification
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Initialiser le backend d'authentification
        auth_backend = SimpleAuth()
        
        # Composant d'authentification moderne avec hauteur explicite
        if render_modern_login(auth_backend, theme="dark", key_suffix="_login_page", height=750):
            # Connexion réussie - rediriger vers Chat
            st.success("Connexion réussie! Redirection en cours...")
            st.session_state.selected_page = "Chat"
            st.rerun()


# Migration utility pour remplacer l'ancien système
def migrate_to_modern_auth():
    """
    Utilitaire pour migrer de l'ancien système vers le nouveau
    """
    migration_guide = """
    # Migration vers l'authentification moderne
    
    ## Remplacements :
    
    ### Dans vos pages :
    ```python
    # Ancien
    from components.auth_components import render_login_form, require_authentication
    
    # Nouveau  
    from components.modern_auth_integration import render_modern_auth_page, require_modern_authentication
    ```
    
    ### Dans votre app.py :
    ```python
    # Ancien
    if not require_authentication():
        return
    
    # Nouveau
    if not require_modern_authentication():
        return
    ```
    
    ### Sidebar :
    ```python
    # Ancien
    render_user_info()
    
    # Nouveau
    render_modern_sidebar_user_info()
    ```
    """
    return migration_guide


if __name__ == "__main__":
    # Page de test
    render_modern_auth_page()