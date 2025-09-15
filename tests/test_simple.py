"""Tests simples et fiables pour les composants de base"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

@pytest.mark.unit
class TestBasicComponents:
    
    def test_config_imports(self):
        """Test que les imports de config fonctionnent"""
        from config.config import AppConfig, LLMConfig, RAGConfig
        assert AppConfig is not None
        assert LLMConfig is not None
        assert RAGConfig is not None
    
    def test_llm_config_creation(self):
        """Test création basique de LLMConfig"""
        from config.config import LLMConfig
        config = LLMConfig()
        assert config.default_provider == "ollama"
        assert isinstance(config.ollama_models, list)
        assert len(config.ollama_models) > 0
    
    def test_app_config_creation(self):
        """Test création basique d'AppConfig"""
        from config.config import AppConfig
        config = AppConfig()
        assert config.app_name == "Assistant Réglementaire Automobile"
        assert config.llm.default_provider == "ollama"
    
    def test_translation_imports(self):
        """Test que les imports de traduction fonctionnent"""
        from translations import get_text
        assert get_text is not None
    
    def test_basic_translation(self):
        """Test traduction basique"""
        from translations import get_text
        text_fr = get_text("app_title", "fr")
        text_en = get_text("app_title", "en")
        assert isinstance(text_fr, str)
        assert isinstance(text_en, str)
        assert len(text_fr) > 0
        assert len(text_en) > 0
    
    def test_ui_styles_import(self):
        """Test que ui_styles peut être importé"""
        try:
            from assistant_regulation.app.ui_styles import load_all_styles
            assert load_all_styles is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ui_styles: {e}")

@pytest.mark.unit 
class TestConfigValidation:
    
    def test_confidence_threshold_validation(self):
        """Test validation des seuils de confiance"""
        from config.config import AppConfig
        
        # Test valeur valide
        config = AppConfig()
        config.rag.confidence_threshold = 0.8
        # Should not raise
        config._validate_config()
        
        # Test valeur invalide
        config.rag.confidence_threshold = 1.5
        with pytest.raises(ValueError):
            config._validate_config()
    
    def test_memory_window_validation(self):
        """Test validation de la fenêtre mémoire"""
        from config.config import AppConfig
        
        config = AppConfig()
        config.memory.window_size = 0
        with pytest.raises(ValueError):
            config._validate_config()
    
    def test_get_default_models(self):
        """Test récupération des modèles par défaut"""
        from config.config import AppConfig
        config = AppConfig()
        
        ollama_model = config.get_default_model("ollama")
        mistral_model = config.get_default_model("mistral")
        unknown_model = config.get_default_model("unknown")
        
        assert ollama_model == "llama3.2"
        assert mistral_model == "mistral-medium"
        assert unknown_model == "llama3.2"  # fallback