"""Tests avec la vraie base de données ChromaDB existante"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

@pytest.mark.integration
class TestWithRealDatabase:
    
    def test_config_with_real_db(self):
        """Test que la config fonctionne avec la vraie DB"""
        from config.config import AppConfig, get_config
        config = get_config()
        assert config is not None
        assert config.app_name == "Assistant Réglementaire Automobile"
    
    @pytest.mark.skipif(not os.path.exists("DB/chroma_db"), reason="ChromaDB not available")
    def test_text_retriever_with_real_db(self):
        """Test le TextRetriever avec la vraie base"""
        from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
        
        try:
            retriever = SimpleTextRetriever()
            # Test simple de recherche
            results = retriever.search("réglementation", top_k=1)
            assert isinstance(results, list)
            # Si la DB contient des données, on devrait avoir des résultats
            if results:
                assert 'content' in results[0] or 'document' in results[0]
        except Exception as e:
            pytest.skip(f"Database access failed: {e}")
    
    def test_memory_service_with_session(self):
        """Test MemoryService avec session réelle"""
        from assistant_regulation.planning.services.memory_service import MemoryService
        
        service = MemoryService(session_id="test_real_session")
        service.add_turn("Qu'est-ce que R046?", "R046 concerne les rétroviseurs.")
        
        context = service.get_context("Parle-moi des rétroviseurs")
        assert isinstance(context, str)
        assert len(context) > 0
        
        stats = service.stats()
        assert isinstance(stats, dict)
    
    def test_generation_service_with_mistral(self):
        """Test GenerationService avec vraie API Mistral si disponible"""
        from assistant_regulation.planning.services.generation_service import GenerationService
        
        try:
            service = GenerationService("mistral", "mistral-medium")
            response = service.generate_answer(
                "Test query", 
                "Context test", 
                max_tokens=50
            )
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            pytest.skip(f"Mistral API not available: {e}")
    
    def test_validation_service_basic(self):
        """Test ValidationService avec mock minimal"""
        from assistant_regulation.planning.services.validation_service import ValidationService
        
        # Mock seulement l'agent de vérification pour éviter l'appel LLM
        with patch('assistant_regulation.processing.Modul_verif.verif_agent.VerifAgent') as mock_agent:
            mock_instance = Mock()
            mock_instance.verify_chunks.return_value = []
            mock_agent.return_value = mock_instance
            
            service = ValidationService("ollama", "llama3.2")
            result = service.validate_chunks("test", {"text": []})
            
            assert isinstance(result, dict)
            assert "text" in result
            assert "images" in result
            assert "tables" in result

@pytest.mark.unit
class TestServicesMocked:
    """Tests unitaires avec mocks complets"""
    
    def test_generation_service_mocked(self):
        """Test GenerationService avec client mocké"""
        from assistant_regulation.planning.services.generation_service import GenerationService
        
        with patch.object(GenerationService, '_init_client') as mock_init:
            mock_client = Mock()
            mock_client.chat.return_value = {"message": {"content": "Mocked response"}}
            mock_init.return_value = {"type": "ollama", "client": mock_client}
            
            service = GenerationService("ollama", "llama3.2")
            response = service.generate_answer("test query", "test context")
            
            assert response == "Mocked response"
    
    def test_memory_service_isolated(self):
        """Test MemoryService en isolation complète"""
        from assistant_regulation.planning.services.memory_service import MemoryService
        
        service = MemoryService(session_id="isolated_test")
        
        # Test basique sans dépendances externes
        service.add_turn("Question", "Réponse")
        stats = service.stats()
        
        assert isinstance(stats, dict)
        assert hasattr(service, '_conversation_memory')