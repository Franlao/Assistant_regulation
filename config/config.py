#!/usr/bin/env python3
"""
Configuration centralisée pour l'Assistant Réglementaire Automobile.
Gère tous les paramètres de l'application de manière centralisée.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

@dataclass
class LLMConfig:
    """Configuration des modèles de langage"""
    # Providers disponibles
    available_providers: List[str] = field(default_factory=lambda: ["ollama", "mistral"])
    default_provider: str = "ollama"
    
    # Modèles par provider
    ollama_models: List[str] = field(default_factory=lambda: [
        "llama3.2", "mistral", "llama3.2:1b", "granite3.1-moe:3b"
    ])
    mistral_models: List[str] = field(default_factory=lambda: [
        "mistral-medium", "mistral-small", "mistral-large-latest", "open-mixtral-8x7b"
    ])
    
    # Modèles par défaut
    default_ollama_model: str = "llama3.2"
    default_mistral_model: str = "mistral-medium"
    
    # Paramètres de génération
    temperature: float = 0.3
    max_tokens: int = 1024
    timeout: int = 300

@dataclass
class ConversationMemoryConfig:
    """Configuration de la mémoire conversationnelle"""
    enabled: bool = True
    window_size: int = 7  # Nombre de tours récents à garder
    max_turns_before_summary: int = 10  # Tours avant résumé automatique
    summary_max_words: int = 70  # Taille max des résumés
    memory_dir: str = ".conversation_memory"  # Répertoire de stockage
    session_timeout_hours: int = 24  # Expiration des sessions

@dataclass
class RAGConfig:
    """Configuration du système RAG"""
    enable_verification: bool = True
    use_images: bool = True
    use_tables: bool = True
    default_top_k: int = 10
    
    # Seuils de confiance
    confidence_threshold: float = 0.7
    force_rag_keywords: List[str] = field(default_factory=lambda: [
        "R046", "R107", "ECE", "réglementation automobile", "norme", "directive"
    ])
    
    # Cache
    use_joblib_cache: bool = True
    cache_dir: str = "./joblib_cache"

@dataclass
class UIConfig:
    """Configuration de l'interface utilisateur"""
    # Langues disponibles
    available_languages: List[str] = field(default_factory=lambda: ["fr", "en"])
    default_language: str = "fr"
    
    # Thèmes
    available_themes: List[str] = field(default_factory=lambda: ["light", "dark"])
    default_theme: str = "light"
    
    # Images
    max_image_height: int = 300
    image_sizes: Dict[str, int] = field(default_factory=lambda: {
        "small": 150,
        "medium": 250,
        "large": 350
    })
    
    # Pagination
    max_sources_display: int = 50
    max_images_per_response: int = 10

@dataclass
class DatabaseConfig:
    """Configuration des bases de données"""
    # Chemins des bases vectorielles
    text_db_path: str = "data/vectorstores/text_chunks"
    image_db_path: str = "data/vectorstores/image_chunks"
    table_db_path: str = "data/vectorstores/table_chunks"
    
    # Paramètres de recherche
    similarity_threshold: float = 0.7
    max_chunk_size: int = 1000
    chunk_overlap: int = 200

@dataclass
class LoggingConfig:
    """Configuration des logs"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "logs/assistant.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_output: bool = True

@dataclass
class SecurityConfig:
    """Configuration de sécurité"""
    max_query_length: int = 1000
    rate_limit_per_minute: int = 60
    allowed_file_types: List[str] = field(default_factory=lambda: [
        ".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg"
    ])
    max_file_size_mb: int = 50

@dataclass
class JinaConfig:
    """Configuration pour l'API Jina"""
    api_key: Optional[str] = None  # Peut être surchargée par la variable d'environnement
    default_model: str = "jina-reranker-m0"
    api_url: str = "https://api.jina.ai/v1/rerank"
    enabled: bool = True
    timeout: int = 15
    disable_on_railway: bool = True

@dataclass
class AppConfig:
    """Configuration principale de l'application"""
    # Informations de l'application
    app_name: str = "Assistant Réglementaire Automobile"
    version: str = "2.0.0"
    description: str = "Assistant IA spécialisé dans les réglementations automobiles UN/ECE"
    
    # Configurations des modules
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: ConversationMemoryConfig = field(default_factory=ConversationMemoryConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    jina: JinaConfig = field(default_factory=JinaConfig)
    
    # Répertoires
    assets_dir: str = "assets"
    data_dir: str = "data"
    temp_dir: str = "temp"
    
    def __post_init__(self):
        """Validation et création des répertoires nécessaires"""
        self._create_directories()
        self._validate_config()
    
    def _create_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        directories = [
            self.memory.memory_dir,
            self.rag.cache_dir,
            self.data_dir,
            self.temp_dir,
            "logs"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self):
        """Valide la configuration"""
        # Validation des seuils
        if not 0 <= self.rag.confidence_threshold <= 1:
            raise ValueError("confidence_threshold doit être entre 0 et 1")
        
        if self.memory.window_size < 1:
            raise ValueError("window_size doit être >= 1")
        
        if self.memory.max_turns_before_summary < self.memory.window_size:
            raise ValueError("max_turns_before_summary doit être >= window_size")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire"""
        def _convert_dataclass(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: _convert_dataclass(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [_convert_dataclass(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: _convert_dataclass(v) for k, v in obj.items()}
            else:
                return obj
        
        return _convert_dataclass(self)
    
    def save_to_file(self, filepath: str = "config/config.json"):
        """Sauvegarde la configuration dans un fichier JSON"""
        # S'assurer que le répertoire existe
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, filepath: str = "config/config.json") -> 'AppConfig':
        """Charge la configuration depuis un fichier JSON"""
        if not os.path.exists(filepath):
            # Créer une configuration par défaut si le fichier n'existe pas
            config = cls()
            config.save_to_file(filepath)
            return config
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruction des objets dataclass
        config = cls()
        config._update_from_dict(data)
        return config
    
    def _update_from_dict(self, data: Dict[str, Any]):
        """Met à jour la configuration depuis un dictionnaire"""
        for key, value in data.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if hasattr(attr, '__dataclass_fields__'):
                    # C'est un dataclass, mise à jour récursive
                    for sub_key, sub_value in value.items():
                        if hasattr(attr, sub_key):
                            setattr(attr, sub_key, sub_value)
                else:
                    setattr(self, key, value)
    
    def get_llm_models(self, provider: str) -> List[str]:
        """Retourne la liste des modèles pour un provider donné"""
        if provider == "ollama":
            return self.llm.ollama_models
        elif provider == "mistral":
            return self.llm.mistral_models
        else:
            return []
    
    def get_default_model(self, provider: str) -> str:
        """Retourne le modèle par défaut pour un provider"""
        if provider == "ollama":
            return self.llm.default_ollama_model
        elif provider == "mistral":
            return self.llm.default_mistral_model
        else:
            return self.llm.default_ollama_model

    def get_jina_api_key(self) -> Optional[str]:
        """Retourne la clé API Jina depuis l'env ou la config."""
        return os.getenv("JINA_API_KEY") or self.jina.api_key

# Instance globale de configuration
_config_instance: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Retourne l'instance globale de configuration (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.load_from_file()
    return _config_instance

def reload_config():
    """Recharge la configuration depuis le fichier"""
    global _config_instance
    _config_instance = AppConfig.load_from_file()

def save_config():
    """Sauvegarde la configuration actuelle"""
    if _config_instance:
        _config_instance.save_to_file()

# Fonctions utilitaires pour accès rapide
def get_llm_config() -> LLMConfig:
    """Accès rapide à la config LLM"""
    return get_config().llm

def get_memory_config() -> ConversationMemoryConfig:
    """Accès rapide à la config mémoire"""
    return get_config().memory

def get_rag_config() -> RAGConfig:
    """Accès rapide à la config RAG"""
    return get_config().rag

def get_ui_config() -> UIConfig:
    """Accès rapide à la config UI"""
    return get_config().ui

# Variables d'environnement avec fallback
def get_env_or_config(env_var: str, config_value: Any) -> Any:
    """Retourne la variable d'environnement ou la valeur de config par défaut"""
    env_value = os.getenv(env_var)
    if env_value is not None:
        # Conversion de type si nécessaire
        if isinstance(config_value, bool):
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(config_value, int):
            return int(env_value)
        elif isinstance(config_value, float):
            return float(env_value)
        else:
            return env_value
    return config_value

if __name__ == "__main__":
    # Test de la configuration
    print("=== Test Configuration ===")
    
    # Créer une configuration par défaut
    config = AppConfig()
    print(f"App: {config.app_name} v{config.version}")
    print(f"LLM Provider: {config.llm.default_provider}")
    print(f"Mémoire activée: {config.memory.enabled}")
    print(f"Fenêtre mémoire: {config.memory.window_size} tours")
    
    # Sauvegarder
    config.save_to_file("config_test.json")
    print("Configuration sauvegardée dans config_test.json")
    
    # Recharger
    config2 = AppConfig.load_from_file("config_test.json")
    print("Configuration rechargée avec succès")
    
    # Test singleton
    config3 = get_config()
    print(f"Singleton: {config3.app_name}") 