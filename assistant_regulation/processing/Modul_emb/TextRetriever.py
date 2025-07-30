from typing import List, Dict, Optional
import chromadb
import uuid,re
import hashlib
import numpy as np
from .BaseRetriever import BaseRetriever, batch_processing

class SimpleTextRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("simple_text")

    def store_chunks(self, chunks: List[Dict]):
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for chunk in chunks:
            content = chunk['text']
            # S'assurer que l'ID est unique dans le batch
            base_id = chunk.get('chunk_id', str(uuid.uuid4()))
            chunk_id = base_id
            while chunk_id in ids:
                chunk_id = f"{base_id}_{uuid.uuid4().hex[:4]}"
            page_numbers = chunk.get('page_numbers', [])
            if isinstance(page_numbers, list):
                page_no = page_numbers[0] if page_numbers else 0
            elif isinstance(page_numbers, int):
                page_no = page_numbers
                page_numbers = [page_numbers]
            else:
                page_no = 0
                page_numbers = []
            
            metadata = {
                'type': 'text',
                'document_id': chunk.get('document_name', 'unknown'),
                'regulation_code': chunk.get('regulation_code', self._extract_regulation_code(chunk)),
                'page_no': int(page_no),
                'page_numbers_str': ','.join(map(str, page_numbers)) if isinstance(page_numbers, list) and page_numbers else str(page_numbers) if page_numbers else '',
                'chunk_index': chunk.get('chunk_index', 0),
                'chunk_position': chunk.get('chunk_position', 0.0),
                'chunk_type': 'late_chunker',
                'chunker_type': chunk.get('chunker_type', 'late_chunker'),
                'chunker_library': chunk.get('chunker_library', 'chonkie'),
                'content_hash': chunk_id,
                'document_source': chunk.get('document_source', ''),
                'document_name': chunk.get('document_name', ''),
                'token_count': chunk.get('token_count', 0),
                'char_count': chunk.get('char_count', 0),
                'chunk_quality': chunk.get('chunk_quality', 0.0),
                'has_global_context': chunk.get('has_global_context', True),
                'context_preservation': chunk.get('context_preservation', 'global'),
                'has_requirement': self._safe_get_nested(chunk, 'content_analysis', 'has_requirement', False),
                'has_definition': self._safe_get_nested(chunk, 'content_analysis', 'has_definition', False),
                'has_article': self._safe_get_nested(chunk, 'content_analysis', 'has_article', False),
                'has_procedure': self._safe_get_nested(chunk, 'content_analysis', 'has_procedure', False),
                'has_reference': self._safe_get_nested(chunk, 'content_analysis', 'has_reference', False)
            }

            ids.append(chunk_id)
            documents.append(content)
            embeddings.append(self._get_embedding(content))
            metadatas.append(metadata)
            
        batch_processing(self.collection, ids, documents, embeddings, metadatas)

    def _extract_regulation_code(self, chunk: Dict) -> str:
        """Extrait le code de réglementation du nom de document"""
        # Priorité au regulation_code direct s'il existe
        if 'regulation_code' in chunk:
            return chunk['regulation_code']
        
        # Sinon, extraire du nom de document
        doc_name = chunk.get('document_name', '') or chunk.get('extra_metadata', {}).get('schema_name', '')
        match = re.search(r'R\d+', doc_name, re.IGNORECASE)
        return match.group(0).upper() if match else 'UNKNOWN'


    def _safe_get_nested(self, chunk: Dict, parent_key: str, child_key: str, default):
        """Récupère de manière sûre une valeur nested qui peut être un dict ou une string JSON"""
        import json
        
        parent_value = chunk.get(parent_key, {})
        
        # Si c'est déjà un dictionnaire, utilisation normale
        if isinstance(parent_value, dict):
            return parent_value.get(child_key, default)
        
        # Si c'est une string (JSON), essayer de la parser
        elif isinstance(parent_value, str):
            try:
                parsed = json.loads(parent_value)
                if isinstance(parsed, dict):
                    return parsed.get(child_key, default)
            except (json.JSONDecodeError, ValueError):
                pass
        
        return default


    def search_by_content_type(self, query: str, content_type: str, top_k: int = 5) -> List[Dict]:
        """Recherche par type de contenu spécifique (requirements, definitions, etc.)"""
        content_type_mapping = {
            'requirements': 'has_requirement',
            'definitions': 'has_definition',
            'articles': 'has_article',
            'procedures': 'has_procedure',
            'references': 'has_reference'
        }
        
        if content_type not in content_type_mapping:
            return self.search_with_context(query, top_k)
            
        filter_field = content_type_mapping[content_type]
        
        # Recherche avec filtre sur le type de contenu
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 2,
            where={filter_field: True}
        )
        
        formatted_results = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            if metadata['chunk_type'] == 'late_chunker':
                formatted_results.append(self._format_late_chunker_result(metadata, doc))
        
        return sorted(formatted_results, key=lambda x: x['score'], reverse=True)[:top_k]

    def search_by_quality_threshold(self, query: str, min_quality: float = 0.8, top_k: int = 5) -> List[Dict]:
        """Recherche avec seuil de qualité minimum"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 3,
            where={'chunk_quality': {'$gte': min_quality}}
        )
        
        formatted_results = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            if metadata['chunk_type'] == 'late_chunker':
                formatted_results.append(self._format_late_chunker_result(metadata, doc))
        
        return sorted(formatted_results, key=lambda x: x['quality_score'], reverse=True)[:top_k]

    def get_document_overview(self, document_name: str) -> Dict:
        chunks = self.collection.get(
            where={'document_name': document_name}
        )
        
        if not chunks['metadatas']:
            return {}
        
        metadatas = chunks['metadatas']
        
        total_chunks = len(metadatas)
        avg_quality = sum(m.get('chunk_quality', 0) for m in metadatas) / total_chunks
        
        content_stats = {
            'requirements': sum(1 for m in metadatas if m.get('has_requirement', False)),
            'definitions': sum(1 for m in metadatas if m.get('has_definition', False)),
            'articles': sum(1 for m in metadatas if m.get('has_article', False)),
            'procedures': sum(1 for m in metadatas if m.get('has_procedure', False)),
            'references': sum(1 for m in metadatas if m.get('has_reference', False))
        }
        
        return {
            'document_name': document_name,
            'regulation_code': metadatas[0].get('regulation_code', 'UNKNOWN'),
            'total_chunks': total_chunks,
            'average_quality': round(avg_quality, 3),
            'content_distribution': content_stats,
            'chunker_type': metadatas[0].get('chunker_type', 'unknown'),
            'has_global_context': metadatas[0].get('has_global_context', False)
        }