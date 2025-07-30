"""
Response Builder - Construit les réponses finales avec citations et métadonnées
"""

from typing import Dict, List, Optional
from assistant_regulation.planning.services import MemoryService


class ResponseBuilder:
    """Construit les réponses finales avec citations Vancouver et métadonnées."""
    
    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    def build_response(
        self, 
        query: str, 
        answer: str, 
        chunks: Dict, 
        analysis: Dict, 
        routing_decision=None
    ) -> Dict:
        """Construit la réponse finale avec citations Vancouver intégrées."""
        
        # Extraire les sources enrichies
        sources = self._extract_sources(chunks.get("text", []))
        
        # Ajouter les citations Vancouver dans le texte de réponse
        from ..services.citation_service import citation_service
        enhanced_answer = citation_service.add_vancouver_citations(answer, sources)
        
        # Construire les métadonnées
        metadata = self._build_metadata(chunks, analysis, routing_decision)
        
        # Mémorisation
        self.memory_service.add_turn(query, enhanced_answer, metadata=metadata)

        response = {
            "answer": enhanced_answer,
            "response": enhanced_answer,  # Compatibilité avec l'app
            "analysis": analysis,
            "sources": sources,
            "images": chunks.get("images", []),
            "tables": chunks.get("tables", []),
        }
        
        # Ajouter informations de routage si disponibles
        if routing_decision:
            response["routing_info"] = {
                "strategy": routing_decision.response_strategy.value,
                "confidence": routing_decision.confidence_score,
                "reasoning": routing_decision.reasoning,
            }
        
        return response

    def _build_metadata(self, chunks: Dict, analysis: Dict, routing_decision=None) -> Dict:
        """Construit les métadonnées pour la mémorisation."""
        metadata = {
            "sources_count": len(chunks.get("text", [])),
            "images_count": len(chunks.get("images", [])),
            "tables_count": len(chunks.get("tables", [])),
            "query_type": analysis.get("query_type", "unknown"),
        }
        
        if routing_decision:
            metadata.update({
                "routing_strategy": routing_decision.response_strategy.value,
                "routing_confidence": routing_decision.confidence_score,
            })
        
        return metadata

    @staticmethod
    def _extract_sources(text_chunks: List) -> List[Dict]:
        """Extrait une liste de sources avec métadonnées enrichies."""
        sources = []
        for i, chunk in enumerate(text_chunks):
            # Gestion des différents formats de chunks
            content = chunk.get('content') or chunk.get('documents') or chunk.get('text', '')
            meta = chunk.get("metadata", {})
            
            # Extraction des informations de document (retriever format priority)
            document_name = (
                meta.get('document_name') or 
                chunk.get('document_name') or
                meta.get('document_id') or 
                'Document inconnu'
            )
            
            # Extraction des informations de page (retriever format priority)
            pages = []
            if meta.get('page_number'):
                # Format retriever standard
                pages = [meta['page_number']]
            elif meta.get('page_numbers_str'):
                # Format Late Chunker avec pages multiples
                pages = [int(p) for p in meta['page_numbers_str'].split(',') if p.strip()]
            elif meta.get('page_no'):
                pages = [meta['page_no']]
            elif chunk.get('page_numbers'):
                pages = chunk['page_numbers']
            
            page = pages[0] if pages else None
            
            # Extraction du code de réglementation (retriever format priority)
            regulation_code = (
                meta.get('regulation_code') or
                chunk.get('regulation_code') or
                'Code inconnu'
            )
            
            # Extraction du chemin du document source
            doc_source = meta.get("document_source", "") or chunk.get('document_source', '')
            
            # Construction du lien file:// (URL-encodée)
            import urllib.parse
            source_link = None
            if doc_source:
                # Remplace les backslashes par des slashes pour compatibilité URL
                doc_source_url = doc_source.replace('\\', '/')
                # Encode les espaces et caractères spéciaux
                doc_source_url = urllib.parse.quote(doc_source_url)
                if page:
                    source_link = f"file:///{doc_source_url}#page={page}"
                else:
                    source_link = f"file:///{doc_source_url}"
            
            # Informations Late Chunker spécifiques
            chunk_info = {}
            if meta.get('chunk_type') == 'late_chunker':
                chunk_info = {
                    'chunk_index': meta.get('chunk_index', 0),
                    'chunk_position': meta.get('chunk_position', 0.0),
                    'quality_score': meta.get('chunk_quality', 0.0),
                    'token_count': meta.get('token_count', 0),
                    'char_count': meta.get('char_count', len(content)),
                    'has_global_context': meta.get('has_global_context', False),
                    'content_analysis': {
                        'has_requirement': meta.get('has_requirement', False),
                        'has_definition': meta.get('has_definition', False),
                        'has_article': meta.get('has_article', False),
                        'has_procedure': meta.get('has_procedure', False),
                        'has_reference': meta.get('has_reference', False)
                    }
                }
            
            # Hash du contenu pour la mise en surbrillance
            import hashlib
            content_hash = hashlib.md5(content[:100].encode()).hexdigest()[:8] if content else ''
            
            sources.append({
                # Informations de base
                'id': f'source_{i+1}',
                'text_preview': content[:150] + '...' if len(content) > 150 else content,
                'full_text': content,
                'regulation_code': regulation_code,
                'document_name': document_name,
                'document_source': doc_source,
                'pages': ', '.join(map(str, pages)) if pages else 'Page inconnue',
                'page_display': ', '.join(map(str, pages)) if pages else 'Page inconnue',
                'source_link': source_link,
                'content_hash': content_hash,
                
                # Métadonnées Late Chunker
                'chunk_info': chunk_info,
                
                # Compatibilité avec l'ancien format et display_sources
                "document": document_name,
                "page": page,
                "regulation": regulation_code,
                'section': meta.get('section_id', 'Section inconnue'),
                # Champs requis par display_sources function
                'text': content,  # display_sources attend 'text'
            })
        return sources 