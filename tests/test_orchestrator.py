import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

@pytest.mark.integration
class TestModularOrchestrator:
    
    def test_orchestrator_init(self):
        from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
        
        # Mock tous les services pour éviter les dépendances externes
        with patch('assistant_regulation.planning.services.generation_service.GenerationService'), \
             patch('assistant_regulation.planning.services.retrieval_service.RetrievalService'), \
             patch('assistant_regulation.planning.services.memory_service.MemoryService'):
            
            orchestrator = ModularOrchestrator(llm_provider="ollama", model_name="llama3.2")
            assert orchestrator is not None
    
    def test_process_query(self):
        from assistant_regulation.planning.Orchestrator.modular_orchestrator import ModularOrchestrator
        
        with patch('assistant_regulation.planning.services.generation_service.GenerationService'), \
             patch('assistant_regulation.planning.services.retrieval_service.RetrievalService'), \
             patch('assistant_regulation.planning.services.memory_service.MemoryService'), \
             patch('assistant_regulation.planning.sync.query_processor.QueryProcessor') as mock_processor:
                
            mock_processor_instance = Mock()
            mock_processor_instance.process_query.return_value = {
                "response": "test response",
                "sources": [],
                "images": []
            }
            mock_processor.return_value = mock_processor_instance
            
            orchestrator = ModularOrchestrator(llm_provider="ollama")
            # process_query prend seulement query en param, pas session_id
            result = orchestrator.process_query("test query")
            assert "response" in result