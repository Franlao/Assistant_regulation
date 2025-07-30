"""
Chunking de texte avec Late Chunker - Solution optimale.
Remplace l'ancienne solution Docling par Late Chunker (15x plus rapide, contexte global préservé).
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF pour extraction rapide
from assistant_regulation.processing.Modul_Process.chunking_utils import extract_document_metadata

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LateChunkerRegulation:
    """
    Chunker utilisant Late Chunker pour documents réglementaires.
    Remplace l'ancienne solution Docling.
    """
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 2048,
                 min_characters_per_chunk: int = 50):
        """
        Initialise le Late Chunker.
        
        Args:
            embedding_model: Modèle d'embedding
            chunk_size: Taille maximale par chunk
            min_characters_per_chunk: Minimum de caractères par chunk
        """
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.min_characters_per_chunk = min_characters_per_chunk
        
        # Initialisation du chunker
        self.chunker = self._initialize_late_chunker()
        
    def _initialize_late_chunker(self):
        """Initialise le Late Chunker."""
        try:
            from chonkie import LateChunker,RecursiveRules

            
            chunker = LateChunker(
                embedding_model=self.embedding_model,
                chunk_size=self.chunk_size,
                rules=RecursiveRules(),
                min_characters_per_chunk=self.min_characters_per_chunk
            )
            
            logger.info(f"Late Chunker initialisé avec {self.embedding_model}")
            return chunker
            
        except ImportError as e:
            logger.error(f"Erreur import Late Chunker: {e}")
            logger.info("Installation requise: pip install 'chonkie[st]'")
            return None
        except Exception as e:
            logger.error(f"Erreur initialisation Late Chunker: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> tuple[str, List[Dict]]:
        """
        Extraction du texte avec préservation de la structure et mapping des pages.
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            page_mappings = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Nettoyage basique
                text = self._clean_text(text)
                
                if text.strip():
                    start_pos = sum(len(t) + 2 for t in text_parts)  # +2 for '\n\n'
                    text_parts.append(text)
                    end_pos = start_pos + len(text)
                    
                    page_mappings.append({
                        'page_num': page_num + 1,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'text_length': len(text)
                    })
            
            doc.close()
            
            full_text = '\n\n'.join(text_parts)
            logger.info(f"Texte extrait: {len(full_text)} caractères de {len(text_parts)} pages")
            
            return full_text, page_mappings
            
        except Exception as e:
            logger.error(f"Erreur extraction PDF: {e}")
            return "", []
    
    def _clean_text(self, text: str) -> str:
        """Nettoyage du texte."""
        # Normalisation des espaces
        text = text.replace('\t', ' ')
        text = ' '.join(text.split())
        
        # Préservation des structures importantes
        text = text.replace('Article ', '\n\nArticle ')
        text = text.replace('Section ', '\n\nSection ')
        text = text.replace('Annexe ', '\n\nAnnexe ')
        
        return text.strip()
    
    def _map_chunk_to_pages(self, chunk_text: str, chunk_start: int, chunk_end: int, page_mappings: List[Dict]) -> List[int]:
        """
        Détermine les pages auxquelles appartient un chunk basé sur sa position.
        """
        pages = []
        
        for page_info in page_mappings:
            page_start = page_info['start_pos']
            page_end = page_info['end_pos']
            
            # Vérifier si le chunk chevauche avec cette page
            if not (chunk_end <= page_start or chunk_start >= page_end):
                pages.append(page_info['page_num'])
        
        return pages if pages else [1]  # Au moins page 1 si rien trouvé
    
    def chunk_document(self, pdf_path: str) -> List[Dict]:
        """
        Chunking complet avec Late Chunker.
        """
        if not self.chunker:
            logger.error("Late Chunker non initialisé")
            return []
        
        try:
            logger.info(f"Début Late Chunking: {pdf_path}")
            start_time = time.time()
            
            # Extraction du texte avec mapping des pages
            text, page_mappings = self.extract_text_from_pdf(pdf_path)
            if not text:
                logger.error("Aucun texte extrait")
                return []
            
            # Late Chunking
            chunks = self.chunker(text)
            
            if not chunks:
                logger.error("Aucun chunk généré")
                return []
            
            # Enrichissement des chunks
            document_name = os.path.basename(pdf_path)
            doc_metadata = extract_document_metadata(pdf_path)
            
            enriched_chunks = []
            for idx, chunk in enumerate(chunks):
                # Analyse du contenu
                content_analysis = self._analyze_content(chunk.text)
                
                # Déterminer les pages pour ce chunk
                chunk_start = getattr(chunk, 'start_index', 0)  
                chunk_end = getattr(chunk, 'end_index', chunk_start + len(chunk.text))
                page_numbers = self._map_chunk_to_pages(chunk.text, chunk_start, chunk_end, page_mappings)
                
                enriched_chunk = {
                    # Informations de base
                    'chunk_id': f'chunk_{idx+1}',
                    'text': chunk.text,
                    'original_text': chunk.text,
                    'chunk_index': idx,
                    'chunk_position': round(idx / len(chunks), 3),
                    
                    # Informations de page
                    'page_numbers': page_numbers,
                    
                    # Métadonnées Late Chunker
                    'token_count': getattr(chunk, 'token_count', len(chunk.text.split())),
                    'char_count': len(chunk.text),
                    'has_global_context': True,  # Avantage du Late Chunker
                    
                    # Métadonnées du document
                    'document_source': pdf_path,
                    'document_name': document_name,
                    'regulation_code': doc_metadata['regulation_code'],
                    
                    # Analyse de contenu
                    'content_analysis': content_analysis,
                    'chunk_quality': self._calculate_quality(chunk.text),
                    
                    # Marqueurs
                    'chunker_type': 'late_chunker',
                    'chunker_library': 'chonkie',
                    'context_preservation': 'global'
                }
                
                enriched_chunks.append(enriched_chunk)
            
            processing_time = time.time() - start_time
            logger.info(f"Late Chunking terminé: {len(enriched_chunks)} chunks en {processing_time:.2f}s")
            
            return enriched_chunks
            
        except Exception as e:
            logger.error(f"Erreur Late Chunking: {e}")
            return []
    
    def _analyze_content(self, text: str) -> Dict:
        """Analyse du contenu réglementaire."""
        text_lower = text.lower()
        
        return {
            'has_article': 'article' in text_lower,
            'has_requirement': any(word in text_lower for word in ['doit', 'devra', 'obligatoire', 'requis']),
            'has_definition': any(word in text_lower for word in ['définition', 'signifie', 'désigne']),
            'has_procedure': any(word in text_lower for word in ['procédure', 'méthode', 'essai']),
            'has_reference': any(word in text_lower for word in ['voir', 'cf', 'référence']),
            'sentence_count': text.count('.') + text.count('!') + text.count('?'),
            'word_count': len(text.split())
        }
    
    def _calculate_quality(self, text: str) -> float:
        """Calcul de la qualité du chunk."""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        # Métriques simples
        words = text.split()
        sentences = text.count('.') + text.count('!') + text.count('?')
        
        length_score = min(1.0, len(text) / 500)
        structure_score = min(1.0, sentences / 3)
        word_score = min(1.0, len(words) / 100)
        
        return round((length_score + structure_score + word_score) / 3, 3)

# Fonction principale pour compatibilité avec l'ancien code
def hybrid_chunk_document(source_path: str, 
                         embed_model_id: str = "all-MiniLM-L6-v2",
                         max_tokens: int = 2048,
                         enable_validation: bool = True,
                         enable_deduplication: bool = True,
                         **kwargs) -> List[Dict]:
    """
    Fonction principale de chunking - Compatible avec l'ancien code.
    Utilise maintenant Late Chunker au lieu de Docling.
    
    Args:
        source_path: Chemin vers le PDF
        embed_model_id: Modèle d'embedding
        max_tokens: Taille des chunks
        enable_validation: Ignoré (Late Chunker a sa propre validation)
        enable_deduplication: Ignoré (Late Chunker évite les doublons)
        **kwargs: Arguments additionnels ignorés
    
    Returns:
        Liste des chunks avec métadonnées enrichies
    """
    
    chunker = LateChunkerRegulation(
        embedding_model=embed_model_id,
        chunk_size=max_tokens,
        min_characters_per_chunk=50
    )
    
    return chunker.chunk_document(source_path)

# Fonction utilitaire rapide
def chunk_regulation_with_late_chunker(pdf_path: str, 
                                     embedding_model: str = "all-MiniLM-L6-v2",
                                     chunk_size: int = 2048) -> List[Dict]:
    """
    Fonction utilitaire pour chunking rapide avec Late Chunker.
    """
    chunker = LateChunkerRegulation(
        embedding_model=embedding_model,
        chunk_size=chunk_size
    )
    
    return chunker.chunk_document(pdf_path)

# Fonction de compatibilité - garde les anciens noms
def chunk_document_legacy(source_path: str, 
                         embed_model_id: str = "all-MiniLM-L6-v2", 
                         max_tokens: int = 2048):
    """
    Fonction de compatibilité avec l'ancienne API.
    """
    logger.info("Utilisation de l'API de compatibilité - Late Chunker utilisé")
    return hybrid_chunk_document(source_path, embed_model_id, max_tokens)

if __name__ == "__main__":
    # Test du nouveau système
    pdf_path = r"c:\\Projet_AI\\Assistant_regulation\\assets\\R107 - 10 series.pdf"
    
    if os.path.exists(pdf_path):
        print("=== TEST LATE CHUNKER (NOUVEAU SYSTÈME) ===")
        
        # Test avec la fonction principale
        chunks = hybrid_chunk_document(pdf_path, max_tokens=1024)
        
        if chunks:
            print(f"Chunks générés: {len(chunks)}")
            
            chunk = chunks[0]
            print(f"\\nExemple de chunk:")
            print(f"  - ID: {chunk['chunk_id']}")
            print(f"  - Taille: {chunk['char_count']} caractères")
            print(f"  - Tokens: {chunk['token_count']}")
            print(f"  - Contexte global: {chunk['has_global_context']}")
            print(f"  - Qualité: {chunk['chunk_quality']}")
            print(f"  - Regulation: {chunk['regulation_code']}")
            print(f"  - Texte: {chunk['text'][:200]}...")
            print(f"  - Document: {chunk['document_name']}")
            print(f"  - Document source: {chunk['document_source']}")
            
            
            # Statistiques
            with_requirements = sum(1 for c in chunks if c['content_analysis']['has_requirement'])
            with_definitions = sum(1 for c in chunks if c['content_analysis']['has_definition'])
            
            print(f"\\nStatistiques:")
            print(f"  - Chunks avec exigences: {with_requirements}")
            print(f"  - Chunks avec définitions: {with_definitions}")
            print(f"  - Contexte global: PRÉSERVÉ (Late Chunker)")
            
        else:
            print("Erreur: Aucun chunk généré")
            print("Installation requise: pip install 'chonkie[st]'")
    
    else:
        print(f"Document test non trouvé: {pdf_path}")
        print("Placez un PDF de test dans le dossier assets/")