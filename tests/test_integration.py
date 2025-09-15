import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

@pytest.mark.integration
class TestIntegration:
    
    @patch('config.config.Path')
    def test_config_loading(self, mock_path):
        """Test que la configuration se charge correctement"""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        from config import get_config
        config = get_config()
        assert config is not None
        assert config.app_name == "Assistant Réglementaire Automobile"
    
    def test_full_query_processing(self):
        """Test du workflow complet de traitement de requête"""
        from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
        
        # Mock tous les services nécessaires
        with patch('assistant_regulation.planning.services.generation_service.GenerationService'), \
             patch('assistant_regulation.planning.services.retrieval_service.RetrievalService'), \
             patch('assistant_regulation.planning.services.memory_service.MemoryService'), \
             patch('assistant_regulation.planning.sync.query_processor.QueryProcessor') as mock_processor:
                
            mock_processor_instance = Mock()
            mock_processor_instance.process_query.return_value = {
                "response": "Réponse de test",
                "sources": [],
                "images": []
            }
            mock_processor.return_value = mock_processor_instance
            
            orchestrator = ModularOrchestrator(llm_provider="ollama")
            # process_query prend seulement query en param
            result = orchestrator.process_query("test query")
            
            assert "response" in result