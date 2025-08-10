"""
Composants d'authentification pour l'application multi-pages
"""

import streamlit as st
import hashlib
import sqlite3
import os
from typing import Optional, Tuple
from pathlib import Path


class SimpleAuth:
    """Gestionnaire d'authentification simple basé sur SQLite"""
    
    def __init__(self):
        # Créer le dossier .streamlit s'il n'existe pas
        self.auth_dir = Path(".streamlit")
        self.auth_dir.mkdir(exist_ok=True)
        
        self.db_path = self.auth_dir / "users.db"
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données des utilisateurs"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Créer la table des utilisateurs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Créer les utilisateurs par défaut
            self._create_default_users(cursor)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Erreur d'initialisation de la base d'authentification: {e}")
    
    def _create_default_users(self, cursor):
        """Crée les utilisateurs par défaut"""
        default_users = [
            ("admin", "admin123", "admin"),
            ("user", "user123", "user")
        ]
        
        for username, password, role in default_users:
            password_hash = self._hash_password(password)
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
    
    def _hash_password(self, password: str) -> str:
        """Hash le mot de passe avec SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authentifie un utilisateur"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            password_hash = self._hash_password(password)
            cursor.execute(
                "SELECT username FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            st.error(f"Erreur d'authentification: {e}")
            return False
    
    def get_user_role(self, username: str) -> Optional[str]:
        """Récupère le rôle d'un utilisateur"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            st.error(f"Erreur de récupération du rôle: {e}")
            return None
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change le mot de passe d'un utilisateur"""
        try:
            # Vérifier l'ancien mot de passe
            if not self.authenticate(username, old_password):
                return False
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            new_password_hash = self._hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (new_password_hash, username)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Erreur de changement de mot de passe: {e}")
            return False


def render_login_form() -> bool:
    """Affiche le formulaire de connexion"""
    
    # Style CSS pour le formulaire de connexion
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    .login-title {
        text-align: center;
        color: white;
        margin-bottom: 1.5rem;
    }
    .login-info {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="login-title">🔐 Authentification</h2>', unsafe_allow_html=True)
    
    # Informations sur les comptes de test
    with st.expander("ℹ️ Comptes de test disponibles", expanded=True):
        st.markdown("""
        **Administrateur:**
        - Utilisateur: `admin`
        - Mot de passe: `admin123`
        - Accès: Toutes les pages
        
        **Utilisateur standard:**
        - Utilisateur: `user`
        - Mot de passe: `user123`
        - Accès: Chat + Configuration
        """)
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("👤 Nom d'utilisateur", placeholder="admin ou user")
        password = st.text_input("🔒 Mot de passe", type="password", placeholder="Votre mot de passe")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_submitted = st.form_submit_button("🚀 Se connecter", use_container_width=True, type="primary")
        
        if login_submitted:
            if not username or not password:
                st.error("Veuillez saisir nom d'utilisateur et mot de passe")
                st.markdown('</div>', unsafe_allow_html=True)
                return False
            
            auth = SimpleAuth()
            if auth.authenticate(username, password):
                # Authentification réussie
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_role = auth.get_user_role(username)
                
                st.success(f"✅ Connexion réussie ! Bienvenue {username}")
                st.balloons()
                
                # Petite pause pour l'UX puis rerun
                import time
                time.sleep(1)
                st.rerun()
                return True
            else:
                st.error("❌ Identifiants incorrects")
    
    st.markdown('</div>', unsafe_allow_html=True)
    return False


def render_user_info():
    """Affiche les informations de l'utilisateur connecté dans la sidebar"""
    if not st.session_state.get("authenticated", False):
        return
    
    username = st.session_state.get("username", "Inconnu")
    user_role = st.session_state.get("user_role", "user")
    
    # Badge utilisateur
    role_color = "#28a745" if user_role == "admin" else "#007bff"
    role_icon = "👑" if user_role == "admin" else "👤"
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {role_color}22, {role_color}11);
        border: 1px solid {role_color}44;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 15px;
        text-align: center;
    ">
        <div style="color: {role_color}; font-size: 1.2em; font-weight: bold;">
            {role_icon} {username}
        </div>
        <div style="color: {role_color}; font-size: 0.8em; opacity: 0.8;">
            {user_role.capitalize()}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Bouton de déconnexion
    if st.button("🚪 Déconnexion", use_container_width=True, key="logout_btn"):
        logout()
        st.rerun()


def render_change_password_form():
    """Affiche le formulaire de changement de mot de passe"""
    if not st.session_state.get("authenticated", False):
        return
    
    with st.expander("🔑 Changer le mot de passe", expanded=False):
        with st.form("change_password_form"):
            old_password = st.text_input("Ancien mot de passe", type="password")
            new_password = st.text_input("Nouveau mot de passe", type="password")
            confirm_password = st.text_input("Confirmer nouveau mot de passe", type="password")
            
            if st.form_submit_button("🔄 Changer mot de passe"):
                if not old_password or not new_password or not confirm_password:
                    st.error("Veuillez remplir tous les champs")
                    return
                
                if new_password != confirm_password:
                    st.error("Les nouveaux mots de passe ne correspondent pas")
                    return
                
                if len(new_password) < 6:
                    st.error("Le nouveau mot de passe doit contenir au moins 6 caractères")
                    return
                
                auth = SimpleAuth()
                username = st.session_state.get("username")
                
                if auth.change_password(username, old_password, new_password):
                    st.success("✅ Mot de passe changé avec succès!")
                else:
                    st.error("❌ Ancien mot de passe incorrect")


def require_authentication() -> bool:
    """Vérifie l'authentification requise - à utiliser dans les pages"""
    if not st.session_state.get("authenticated", False):
        st.warning("🔒 **Accès restreint** - Veuillez vous connecter pour accéder à cette page.")
        render_login_form()
        return False
    return True


def require_admin_access() -> bool:
    """Vérifie l'accès administrateur - à utiliser dans les pages admin"""
    if not require_authentication():
        return False
    
    if st.session_state.get("user_role") != "admin":
        st.error("🚫 **Accès interdit** - Cette page est réservée aux administrateurs.")
        st.info("Connectez-vous avec un compte administrateur pour accéder à cette fonctionnalité.")
        return False
    
    return True


def logout():
    """Fonction de déconnexion"""
    # Nettoyer les données d'authentification
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.username = None
    
    # Optionnel: nettoyer d'autres données sensibles
    # st.session_state.messages = []


def get_available_pages():
    """Retourne les pages disponibles selon le rôle utilisateur"""
    from utils.session_utils import is_authenticated, is_admin
    
    pages = []
    
    # Page Chat accessible à tous (même non authentifiés)
    pages.append(st.Page("pages/chat.py", title="💬 Chat", icon="💬", default=True))
    
    # Pages authentifiées
    if is_authenticated():
        pages.append(st.Page("pages/configuration.py", title="⚙️ Configuration", icon="⚙️"))
        
        # Page admin uniquement
        if is_admin():
            pages.append(st.Page("pages/database.py", title="🗃️ Database", icon="🗃️"))
    
    return pages