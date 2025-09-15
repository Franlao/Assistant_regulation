import pytest
from unittest.mock import patch, mock_open
import json
from config.config import AppConfig, LLMConfig, RAGConfig, get_config

class TestConfig:
    
    def test_llm_config_defaults(self):
        config = LLMConfig()
        assert config.default_provider == "ollama"
        assert "llama3.2" in config.ollama_models
        assert config.temperature == 0.3
    
    def test_rag_config_defaults(self):
        config = RAGConfig()
        assert config.enable_verification is True
        assert config.confidence_threshold == 0.7
        assert "R046" in config.force_rag_keywords
    
    @patch("builtins.open", new_callable=mock_open, read_data='{"llm": {"default_provider": "mistral"}}')
    @patch("os.path.exists", return_value=True)
    def test_load_from_file(self, mock_exists, mock_file):
        config = get_config()
        assert config is not None
    
    def test_get_default_model_ollama(self):
        config = AppConfig()
        model = config.get_default_model("ollama")
        assert model == "llama3.2"
    
    def test_get_default_model_mistral(self):
        config = AppConfig()
        model = config.get_default_model("mistral")
        assert model == "mistral-medium"