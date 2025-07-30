from .BaseRetriever import BaseRetriever, batch_processing
from typing import List, Dict
import uuid


class ImageRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("pdf_images")

    def store_chunks(self, chunks: List[Dict]):
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # Contexte enrichi avec classification et qualité (support JSON string)
            image_type = self._safe_get_nested(chunk, 'image_classification', 'type', 'unknown')
            quality_score = self._safe_get_nested(chunk, 'quality_analysis', 'overall_quality', 0.0)
            has_text = self._safe_get_nested(chunk, 'ocr_info', 'has_text', False)
            
            context = f"Image page {chunk['page_number']} - Type: {image_type} - Qualité: {quality_score:.2f} - Texte: {'Oui' if has_text else 'Non'} - {chunk.get('description', '')}"
            
            ids.append(str(uuid.uuid4()))
            documents.append(context)
            embeddings.append(self._get_embedding(context))
            # Gérer le cas où dimensions contient plus de deux valeurs (par ex. [w,h,c])
            dimensions = chunk.get('dimensions', [0, 0])
            if isinstance(dimensions, (list, tuple)) and len(dimensions) >= 2:
                width, height = dimensions[0], dimensions[1]
            else:
                width, height = 0, 0

            metadatas.append({
                'type': 'image',
                'page': chunk['page_number'],
                'width': width,   # Type int
                'height': height, # Type int
                'image_url': chunk['image_url'],
                'document_source': chunk.get('document_source', ''),
                'document_name': chunk.get('document_name', ''),
                'regulation_code': chunk.get('regulation_code', ''),
                # Nouvelles métadonnées enrichies
                'image_hash': chunk.get('image_hash', ''),
                'image_type': image_type,
                'quality_score': quality_score,
                'has_text': str(has_text),  # Conversion en string pour éviter l'erreur de métadonnées
                'text_score': self._safe_get_nested(chunk, 'ocr_info', 'text_score', 0.0),
                'confidence': self._safe_get_nested(chunk, 'image_classification', 'confidence', 0.0),
                'geometric_shapes': self._safe_get_nested(chunk, 'image_classification', 'geometric_shapes', 0),
                'unique_colors': self._safe_get_nested(chunk, 'quality_analysis', 'unique_colors', 0),
                'format': chunk.get('format', 'unknown'),
                'size_bytes': chunk.get('size_bytes', 0)
            })

        batch_processing(self.collection, ids, documents, embeddings, metadatas)

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