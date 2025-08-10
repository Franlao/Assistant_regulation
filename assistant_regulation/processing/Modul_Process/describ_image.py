import os
import json
import time
import hashlib
from pathlib import Path
from mistralai import Mistral
from typing import Dict, Optional
import logging
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Configuration logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class EnhancedImageDescriber:
    """
    Système amélioré de description d'images avec cache intelligent et prompts adaptatifs.
    """
    
    def __init__(self, cache_dir: str = "description_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialisation du client Mistral
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("La clé API Mistral est introuvable dans les variables d'environnement")
        
        self.client = Mistral(api_key=api_key)
        self.model = "pixtral-12b-2409"
        
        # Statistiques
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
    
    def _convert_numpy_types(self, obj):
        """
        Convertit récursivement les types NumPy en types Python natifs pour la sérialisation JSON.
        
        Args:
            obj: Objet à convertir
            
        Returns:
            Objet avec types Python natifs
        """
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    def _get_cache_path(self, image_hash: str) -> Path:
        """Génère le chemin du cache pour un hash d'image."""
        return self.cache_dir / f"{image_hash}.json"
    
    def _load_from_cache(self, image_hash: str) -> Optional[Dict]:
        """Charge une description depuis le cache avec gestion robuste des erreurs."""
        cache_path = self._get_cache_path(image_hash)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    
                # Validation des données du cache
                if not isinstance(cached_data, dict):
                    logger.warning(f"Format de cache invalide pour {image_hash[:12]}...")
                    self._remove_corrupted_cache(cache_path)
                    self.cache_misses += 1
                    return None
                
                # Vérifier les champs requis
                required_fields = ['description', 'metadata', 'timestamp', 'model_used']
                if not all(field in cached_data for field in required_fields):
                    logger.warning(f"Cache incomplet pour {image_hash[:12]}...")
                    self._remove_corrupted_cache(cache_path)
                    self.cache_misses += 1
                    return None
                
                self.cache_hits += 1
                logger.info(f"Cache hit pour {image_hash[:12]}...")
                return cached_data
                
            except json.JSONDecodeError as e:
                logger.warning(f"Cache corrompu pour {image_hash}: {e}")
                self._remove_corrupted_cache(cache_path)
            except Exception as e:
                logger.warning(f"Erreur lecture cache {image_hash}: {e}")
        
        self.cache_misses += 1
        return None
    
    def _remove_corrupted_cache(self, cache_path: Path):
        """Supprime un fichier de cache corrompu."""
        try:
            cache_path.unlink()
            logger.info(f"Cache corrompu supprimé: {cache_path.name}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer le cache corrompu: {e}")
    
    def _save_to_cache(self, image_hash: str, description: str, metadata: Dict):
        """Sauvegarde une description dans le cache avec conversion des types NumPy."""
        cache_path = self._get_cache_path(image_hash)
        
        cache_data = {
            "description": description,
            "metadata": self._convert_numpy_types(metadata),
            "timestamp": time.time(),
            "model_used": self.model
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Cache sauvegardé pour {image_hash[:12]}...")
        except Exception as e:
            logger.warning(f"Erreur sauvegarde cache {image_hash}: {e}")
    
    def _create_adaptive_prompt(self, chunk: Dict) -> str:
        """Crée un prompt adaptatif selon le type d'image et ses métadonnées."""
        
        # Récupération des métadonnées enrichies
        image_type = chunk.get('image_classification', {}).get('type', 'unknown')
        quality_score = chunk.get('quality_analysis', {}).get('overall_quality', 0.0)
        has_text = chunk.get('ocr_info', {}).get('has_text', False)
        text_score = chunk.get('ocr_info', {}).get('text_score', 0.0)
        geometric_shapes = chunk.get('image_classification', {}).get('geometric_shapes', 0)
        confidence = chunk.get('image_classification', {}).get('confidence', 0.0)
        
        # Prompt de base
        base_prompt = f"""Analysez cette image extraite d'un document PDF (page {chunk['page_number']}) dans le contexte d'un document de réglementation automobile UN/ECE."""
        
        # Prompt adaptatif selon le type
        if image_type == 'chart':
            specific_prompt = """
            Cette image est identifiée comme un GRAPHIQUE/TABLEAU.
            Concentrez-vous sur:
            - Les données numériques et unités présentées
            - Les axes, légendes et titres
            - Les tendances ou comparaisons illustrées
            - La relation avec les exigences réglementaires"""
            
        elif image_type == 'diagram':
            specific_prompt = """
            Cette image est identifiée comme un DIAGRAMME.
            Concentrez-vous sur:
            - Les composants et leurs relations
            - Les flèches et connexions
            - Les processus ou séquences illustrés
            - Les spécifications techniques montrées"""
            
        elif image_type == 'technical':
            specific_prompt = """
            Cette image est identifiée comme un SCHÉMA TECHNIQUE.
            Concentrez-vous sur:
            - Les dimensions et mesures
            - Les annotations techniques
            - Les détails de construction ou assemblage
            - Les normes et spécifications référencées"""
            
        elif image_type == 'photo':
            specific_prompt = """
            Cette image est identifiée comme une PHOTO.
            Concentrez-vous sur:
            - Les objets et équipements visibles
            - Les conditions d'utilisation montrées
            - Les éléments de sécurité ou conformité
            - Le contexte d'application pratique"""
        else:
            specific_prompt = """
            Type d'image non déterminé avec certitude.
            Analysez de manière générale:
            - Le contenu visuel principal
            - Les éléments textuels significatifs
            - La fonction probable dans le document
            - La relation avec les exigences réglementaires"""
        
        # Ajout d'informations sur les métadonnées
        metadata_info = f"""
        
        Métadonnées de l'image:
        - Qualité: {quality_score:.2f}/1.0
        - Présence de texte: {'Forte' if text_score > 0.3 else 'Faible' if has_text else 'Aucune'}
        - Formes géométriques: {geometric_shapes}
        - Confiance classification: {confidence:.2f}/1.0"""
        
        # Instructions de réponse
        response_instructions = """
        
        Réponse attendue:
        - Soyez précis et concis (200-300 mots)
        - Utilisez un langage technique approprié
        - Mentionnez les références réglementaires si visibles
        - Indiquez l'importance dans le contexte du document"""
        
        return base_prompt + specific_prompt + metadata_info + response_instructions
    
    def _should_skip_description(self, chunk: Dict) -> bool:
        """Détermine si une image doit être ignorée pour la description."""
        
        # Qualité trop faible
        quality_score = chunk.get('quality_analysis', {}).get('overall_quality', 0.0)
        if quality_score < 0.2:
            return True
        
        # Image trop petite
        dimensions = chunk.get('dimensions', (0, 0))
        if dimensions[0] < 50 or dimensions[1] < 50:
            return True
        
        # Image noire/blanche
        quality_analysis = chunk.get('quality_analysis', {})
        if quality_analysis.get('is_black') or quality_analysis.get('is_white'):
            return True
        
        return False
    
    def enrich_chunk_with_context(self, chunk: Dict) -> Dict:
        """
        Enrichit un chunk d'image avec une description générée par IA avec cache et optimisations.
        
        Args:
            chunk (dict): Chunk d'image avec métadonnées enrichies
        
        Returns:
            dict: Chunk enrichi avec la description générée
        """
        
        # Convertir les types NumPy dans le chunk entrant
        chunk = self._convert_numpy_types(chunk)
        
        # Vérification si on doit ignorer cette image
        if self._should_skip_description(chunk):
            chunk["description"] = "Image ignorée (qualité insuffisante)"
            chunk["model_used"] = "skipped"
            chunk["cached"] = False
            return chunk
        
        # Récupération du hash pour le cache
        image_hash = chunk.get('image_hash')
        if not image_hash:
            # Générer hash si absent (compatibilité)
            image_url = chunk.get('image_url', '')
            if image_url.startswith('data:image/'):
                image_data = image_url.split(',')[1]
                image_hash = hashlib.md5(image_data.encode()).hexdigest()
            else:
                image_hash = hashlib.md5(str(chunk).encode()).hexdigest()
        
        # Tentative de récupération depuis le cache
        cached_result = self._load_from_cache(image_hash)
        if cached_result:
            chunk["description"] = cached_result["description"]
            chunk["model_used"] = cached_result["model_used"]
            chunk["cached"] = True
            chunk["cache_timestamp"] = cached_result["timestamp"]
            return chunk
        
        # Génération de la description
        try:
            prompt = self._create_adaptive_prompt(chunk)
            
            logger.info(f"Génération description pour {image_hash[:12]}... (Type: {chunk.get('image_classification', {}).get('type', 'unknown')})")
            
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": chunk['full_page_url']},
                            {"type": "image_url", "image_url": chunk['image_url']}
                        ]
                    }
                ],
                max_tokens=1024
            )
            
            description = response.choices[0].message.content
            self.api_calls += 1
            
            # Sauvegarde dans le cache
            metadata = {
                "image_type": chunk.get('image_classification', {}).get('type', 'unknown'),
                "quality_score": chunk.get('quality_analysis', {}).get('overall_quality', 0.0),
                "has_text": chunk.get('ocr_info', {}).get('has_text', False),
                "page_number": chunk.get('page_number', 0)
            }
            
            self._save_to_cache(image_hash, description, metadata)
            
            chunk["description"] = description
            chunk["model_used"] = self.model
            chunk["cached"] = False
            
        except Exception as e:
            logger.error(f"Erreur génération description pour {image_hash[:12]}...: {e}")
            chunk["description"] = f"Échec de la génération de description: {str(e)}"
            chunk["model_used"] = "error"
            chunk["cached"] = False
        
        return chunk
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques du cache."""
        total_requests = self.cache_hits + self.cache_misses
        cache_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_calls": self.api_calls,
            "cache_rate": f"{cache_rate:.1f}%",
            "total_requests": total_requests
        }

# Instance globale pour compatibilité
_global_describer = None

def get_describer() -> EnhancedImageDescriber:
    """Retourne l'instance globale du descripteur."""
    global _global_describer
    if _global_describer is None:
        _global_describer = EnhancedImageDescriber()
    return _global_describer

def enrich_chunk_with_context(chunk: Dict) -> Dict:
    """
    Fonction de compatibilité avec l'API existante.
    
    Args:
        chunk (dict): Chunk d'image avec métadonnées enrichies
    
    Returns:
        dict: Chunk enrichi avec la description générée
    """
    describer = get_describer()
    return describer.enrich_chunk_with_context(chunk)

def get_description_stats() -> Dict:
    """Retourne les statistiques de description."""
    describer = get_describer()
    return describer.get_stats()