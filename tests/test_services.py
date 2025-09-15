import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestMemoryService:
    
    def test_memory_service_init(self):
        from assistant_regulation.planning.services.memory_service import MemoryService
        service = MemoryService(session_id="test_session")
        assert service is not None
    
    def test_add_turn(self):
        from assistant_regulation.planning.services.memory_service import MemoryService
        service = MemoryService(session_id="test_session")
        service.add_turn("test query", "test response")
        stats = service.stats()
        assert isinstance(stats, dict)

class TestValidationService:
    
    @patch('assistant_regulation.processing.Modul_verif.verif_agent.VerifAgent')
    def test_validation_service_init(self, mock_verif_agent):
        from assistant_regulation.planning.services.validation_service import ValidationService
        service = ValidationService("ollama", "llama3.2")
        assert service.verif_agent is not None
    
    def test_validate_chunks(self):
        from assistant_regulation.planning.services.validation_service import ValidationService
        
        # Créer d'abord le service sans mock
        service = ValidationService("ollama", "llama3.2")
        
        # Puis mocker directement l'instance
        mock_verif_agent = Mock()
        verified_chunk = {"content": "verified chunk", "metadata": {"score": 0.8}}
        mock_verif_agent.verify_chunks.return_value = [verified_chunk]
        service.verif_agent = mock_verif_agent
        
        input_chunk = {"content": "test chunk", "metadata": {"source": "test.pdf"}}
        result = service.validate_chunks("test query", {"text": [input_chunk]})
        
        assert "text" in result
        assert result["text"] == [verified_chunk]
        mock_verif_agent.verify_chunks.assert_called_once_with("test query", [input_chunk], top_k=8)

class TestGenerationService:
    
    def test_generation_service_init(self):
        from assistant_regulation.planning.services.generation_service import GenerationService
        
        with patch.object(GenerationService, '_init_client', return_value={"type": "ollama", "client": Mock()}):
            service = GenerationService("ollama", "llama3.2")
            assert service.llm_provider == "ollama"
            assert service.model_name == "llama3.2"
    
    def test_generate_answer(self):
        from assistant_regulation.planning.services.generation_service import GenerationService
        
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": "Test response"}}
        
        with patch.object(GenerationService, '_init_client', return_value={"type": "ollama", "client": mock_client}):
            service = GenerationService("ollama", "llama3.2")
            # La vraie méthode s'appelle generate_answer, pas generate_response
            response = service.generate_answer("test query", "test context")
            assert response == "Test response"