import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables"""
    os.environ["TESTING"] = "true"
    os.environ["STREAMLIT_SERVER_TIMEOUT"] = "300"
    yield
    os.environ.pop("TESTING", None)

@pytest.fixture
def mock_config():
    """Mock configuration for tests"""
    from config.config import AppConfig
    config = Mock(spec=AppConfig)
    config.app_name = "Test Assistant"
    config.llm.default_provider = "ollama"
    config.llm.default_ollama_model = "llama3.2"
    config.rag.confidence_threshold = 0.7
    config.ui.default_language = "fr"
    return config

@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for tests"""
    orchestrator = Mock()
    orchestrator.process_query.return_value = {"response": "test response"}
    return orchestrator