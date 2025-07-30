"""
Package de configuration centralisée pour l'Assistant Réglementaire Automobile.

Ce package contient tous les modules et fichiers de configuration de l'application.
"""

from .config import (
    # Classes de configuration
    AppConfig,
    LLMConfig,
    ConversationMemoryConfig,
    RAGConfig,
    UIConfig,
    DatabaseConfig,
    LoggingConfig,
    SecurityConfig,
    
    # Fonctions principales
    get_config,
    reload_config,
    save_config,
    
    # Fonctions d'accès rapide
    get_llm_config,
    get_memory_config,
    get_rag_config,
    get_ui_config,
    
    # Utilitaires
    get_env_or_config
)

__version__ = "1.0.0"
__author__ = "Assistant Réglementaire Automobile Team"

# Exports pour faciliter l'import
__all__ = [
    # Classes
    "AppConfig",
    "LLMConfig", 
    "ConversationMemoryConfig",
    "RAGConfig",
    "UIConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "SecurityConfig",
    
    # Fonctions principales
    "get_config",
    "reload_config", 
    "save_config",
    
    # Accès rapide
    "get_llm_config",
    "get_memory_config",
    "get_rag_config", 
    "get_ui_config",
    
    # Utilitaires
    "get_env_or_config"
] 