"""
Composant d'authentification moderne pour Streamlit
Utilise React + Tailwind CSS pour une interface élégante
"""

import os
import streamlit.components.v1 as components
import streamlit as st
from typing import Optional, Dict, Any
from pathlib import Path
import uuid
import time
import mimetypes

# Fix MIME type issues - solution la plus courante pour composants vides
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

# Chemin vers le composant React compilé
_RELEASE = True  # Mettre à False pendant le développement

if not _RELEASE:
    # Mode développement - URL locale
    _component_func = components.declare_component(
        "modern_auth_component",
        url="http://localhost:3001",  # Port du serveur de développement Webpack
    )
else:
    # Mode production - fichiers statiques
    parent_dir = Path(__file__).parent
    build_dir = parent_dir / "modern_auth" / "dist"
    
    # Vérifier que le build directory existe
    if not build_dir.exists():
        raise FileNotFoundError(f"Build directory not found: {build_dir}")
    
    _component_func = components.declare_component(
        "modern_auth_component", 
        path=str(build_dir)
    )


def modern_auth_component(
    loading: bool = False,
    error_message: Optional[str] = None,
    success_message: Optional[str] = None,
    theme: str = "dark",
    language: str = "fr",
    key: Optional[str] = None,
    height: int = 700
) -> Optional[Dict[str, Any]]:
    """
    Affiche le composant d'authentification moderne
    
    Args:
        loading: Afficher l'état de chargement
        error_message: Message d'erreur à afficher
        success_message: Message de succès à afficher  
        theme: Thème du composant ('light' ou 'dark')
        language: Langue du composant ('fr' ou 'en')
        key: Clé unique pour le composant
        height: Hauteur du composant en pixels
    
    Returns:
        Dict contenant les données d'authentification ou None
    """
    
    component_value = _component_func(
        loading=loading,
        error_message=error_message,
        success_message=success_message,
        theme=theme,
        language=language,
        key=key,
        height=height,
        default=None
    )
    
    return component_value


class ModernAuthManager:
    """
    Gestionnaire pour l'authentification moderne
    Intègre le composant React avec la logique d'authentification Python
    """
    
    def __init__(self, auth_backend=None):
        """
        Initialise le gestionnaire
        
        Args:
            auth_backend: Instance de SimpleAuth ou autre backend d'authentification
        """
        self.auth_backend = auth_backend
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialise les variables de session"""
        if "auth_loading" not in st.session_state:
            st.session_state.auth_loading = False
        if "auth_error" not in st.session_state:
            st.session_state.auth_error = None
        if "auth_success" not in st.session_state:
            st.session_state.auth_success = None
    
    def render_login(self, 
                    theme: str = "dark",
                    language: str = "fr",
                    key_suffix: str = "",
                    height: int = 700) -> bool:
        """
        Affiche le formulaire de connexion moderne
        
        Args:
            theme: Thème du composant
            language: Langue du composant
            key_suffix: Suffixe pour rendre la clé unique
            height: Hauteur du composant en pixels
            
        Returns:
            True si l'utilisateur est authentifié
        """
        
        # Vérifier si déjà authentifié
        if st.session_state.get("authenticated", False):
            return True
        
        # Générer une clé vraiment unique
        if not key_suffix:
            key_suffix = f"_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        unique_key = f"modern_auth{key_suffix}"
        
        # Afficher le composant d'authentification
        auth_data = modern_auth_component(
            loading=st.session_state.auth_loading,
            error_message=st.session_state.auth_error,
            success_message=st.session_state.auth_success,
            theme=theme,
            language=language,
            key=unique_key,
            height=height
        )
        
        # Traiter les données d'authentification
        if auth_data is not None:
            return self._handle_auth_data(auth_data)
        
        return False
    
    def _handle_auth_data(self, auth_data: Dict[str, Any]) -> bool:
        """
        Traite les données d'authentification reçues du composant React
        
        Args:
            auth_data: Données d'authentification du composant
            
        Returns:
            True si l'authentification réussit
        """
        action = auth_data.get("action")
        
        if action == "login":
            return self._handle_login(auth_data)
        elif action == "logout":
            return self._handle_logout(auth_data)
        
        return False
    
    def _handle_login(self, auth_data: Dict[str, Any]) -> bool:
        """
        Traite une tentative de connexion
        
        Args:
            auth_data: Données de connexion
            
        Returns:
            True si la connexion réussit
        """
        username = auth_data.get("username", "").strip()
        password = auth_data.get("password", "")
        
        if not username or not password:
            st.session_state.auth_error = "Nom d'utilisateur et mot de passe requis"
            st.session_state.auth_loading = False
            st.rerun()
            return False
        
        # Activer le loading
        st.session_state.auth_loading = True
        st.session_state.auth_error = None
        
        # Authentifier avec le backend
        if self.auth_backend and self.auth_backend.authenticate(username, password):
            # Succès
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.user_role = self.auth_backend.get_user_role(username)
            st.session_state.auth_loading = False
            st.session_state.auth_error = None
            st.session_state.auth_success = f"Bienvenue {username} !"
            
            # Nettoyer les messages après un délai
            st.rerun()
            return True
        else:
            # Échec
            st.session_state.auth_loading = False
            st.session_state.auth_error = "Identifiants incorrects"
            st.rerun()
            return False
    
    def _handle_logout(self, auth_data: Dict[str, Any]) -> bool:
        """
        Traite une déconnexion
        
        Args:
            auth_data: Données de déconnexion
            
        Returns:
            True après déconnexion
        """
        # Nettoyer la session
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.auth_loading = False
        st.session_state.auth_error = None
        st.session_state.auth_success = None
        
        st.rerun()
        return False
    
    def require_authentication(self) -> bool:
        """
        Vérifie que l'utilisateur est authentifié
        Affiche le formulaire de connexion si nécessaire
        
        Returns:
            True si authentifié
        """
        if not st.session_state.get("authenticated", False):
            st.warning("Accès restreint - Veuillez vous connecter")
            return self.render_login()
        return True
    
    def get_user_info(self) -> Optional[Dict[str, str]]:
        """
        Récupère les informations de l'utilisateur connecté
        
        Returns:
            Dict avec username et role ou None
        """
        if st.session_state.get("authenticated", False):
            return {
                "username": st.session_state.get("username"),
                "role": st.session_state.get("user_role", "user")
            }
        return None


# Fonction utilitaire pour faciliter l'usage
def render_modern_login(auth_backend=None, theme="dark", language="fr", key_suffix="", height=700) -> bool:
    """
    Fonction utilitaire pour afficher rapidement le login moderne
    
    Args:
        auth_backend: Backend d'authentification (ex: SimpleAuth)
        theme: Thème du composant
        language: Langue du composant
        key_suffix: Suffixe pour rendre la clé unique
        height: Hauteur du composant en pixels
        
    Returns:
        True si authentifié
    """
    auth_manager = ModernAuthManager(auth_backend)
    return auth_manager.render_login(theme=theme, language=language, key_suffix=key_suffix, height=height)


# Pour les tests en développement
if __name__ == "__main__":
    st.set_page_config(page_title="Modern Auth Test", layout="wide")
    
    st.title("Test du Composant d'Authentification Moderne")
    
    # Simuler un backend simple pour les tests
    class MockAuth:
        def authenticate(self, username, password):
            return username == "test" and password == "test"
        
        def get_user_role(self, username):
            return "admin" if username == "test" else "user"
    
    mock_auth = MockAuth()
    auth_manager = ModernAuthManager(mock_auth)
    
    if auth_manager.render_login():
        user_info = auth_manager.get_user_info()
        st.success(f"Connecté en tant que : {user_info['username']} ({user_info['role']})")
        
        if st.button("Se déconnecter"):
            auth_manager._handle_logout({"action": "logout"})
    else:
        st.info("Utilisez test/test pour vous connecter")