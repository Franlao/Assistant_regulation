import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class TestProcessingUtils:
    
    @patch('assistant_regulation.processing.process_regulations.Path')
    def test_validate_pdf_directory(self, mock_path):
        from assistant_regulation.processing.process_regulations import validate_pdf_directory
        
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.glob.return_value = [Path("test.pdf")]
        mock_path.return_value = mock_path_instance
        
        result = validate_pdf_directory("test_dir")
        assert result is True
    
    @patch('assistant_regulation.processing.process_regulations.Path')
    def test_validate_pdf_directory_empty(self, mock_path):
        from assistant_regulation.processing.process_regulations import validate_pdf_directory
        
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.glob.return_value = []
        mock_path.return_value = mock_path_instance
        
        result = validate_pdf_directory("test_dir")
        assert result is False

class TestTextRetriever:
    
    def test_text_retriever_init(self):
        from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
        
        with patch('assistant_regulation.processing.Modul_emb.TextRetriever.chromadb'):
            retriever = SimpleTextRetriever()
            # Test que l'objet est créé correctement
            assert retriever is not None
            assert hasattr(retriever, 'collection')
    
    def test_search(self):
        from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
        
        # Créer d'abord le retriever
        retriever = SimpleTextRetriever()
        
        # Mock complètement la méthode de recherche au lieu de mocker la collection interne
        with patch.object(retriever, '_hybrid_search') as mock_search:
            mock_search.return_value = [{
                'document': 'test document',
                'metadata': {'document_name': 'test.pdf', 'page_no': 1},
                'distance': 0.5
            }]
            
            results = retriever.search("test query", top_k=5)
            assert isinstance(results, list)
            assert len(results) > 0
            assert 'document' in results[0]