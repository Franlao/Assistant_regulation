"""
Script de nettoyage du cache d'images corrompu.
Résout les problèmes de sérialisation JSON causés par les types NumPy.
"""

import json
import logging
from pathlib import Path
from typing import List

# Configuration logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def find_corrupted_cache_files(cache_dir: str = "description_cache") -> List[Path]:
    """
    Trouve les fichiers de cache corrompus.
    
    Args:
        cache_dir: Répertoire du cache
        
    Returns:
        Liste des fichiers corrompus
    """
    cache_path = Path(cache_dir)
    corrupted_files = []
    
    if not cache_path.exists():
        logger.info(f"Répertoire de cache {cache_dir} n'existe pas")
        return []
    
    json_files = list(cache_path.glob("*.json"))
    logger.info(f"Vérification de {len(json_files)} fichiers de cache...")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Vérifier la structure attendue
            required_fields = ['description', 'metadata', 'timestamp', 'model_used']
            if not isinstance(data, dict) or not all(field in data for field in required_fields):
                corrupted_files.append(json_file)
                logger.warning(f"Structure invalide: {json_file.name}")
                
        except json.JSONDecodeError as e:
            corrupted_files.append(json_file)
            logger.warning(f"JSON corrompu: {json_file.name} - {e}")
        except Exception as e:
            corrupted_files.append(json_file)
            logger.warning(f"Erreur lecture: {json_file.name} - {e}")
    
    return corrupted_files

def clean_corrupted_cache(cache_dir: str = "description_cache", 
                         dry_run: bool = False) -> bool:
    """
    Nettoie les fichiers de cache corrompus.
    
    Args:
        cache_dir: Répertoire du cache
        dry_run: Si True, montre les fichiers à supprimer sans les supprimer
        
    Returns:
        True si le nettoyage a réussi
    """
    try:
        corrupted_files = find_corrupted_cache_files(cache_dir)
        
        if not corrupted_files:
            logger.info("✓ Aucun fichier de cache corrompu trouvé")
            return True
        
        logger.info(f"Trouvé {len(corrupted_files)} fichiers corrompus")
        
        if dry_run:
            logger.info("Mode DRY RUN - Fichiers qui seraient supprimés:")
            for file in corrupted_files:
                logger.info(f"  - {file.name}")
            return True
        
        # Supprimer les fichiers corrompus
        deleted_count = 0
        for file in corrupted_files:
            try:
                file.unlink()
                deleted_count += 1
                logger.info(f"Supprimé: {file.name}")
            except Exception as e:
                logger.error(f"Erreur suppression {file.name}: {e}")
        
        logger.info(f"✓ Nettoyage terminé: {deleted_count}/{len(corrupted_files)} fichiers supprimés")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage: {e}")
        return False

def validate_cache_structure(cache_dir: str = "description_cache") -> bool:
    """
    Valide la structure de tous les fichiers de cache.
    
    Args:
        cache_dir: Répertoire du cache
        
    Returns:
        True si tous les fichiers sont valides
    """
    cache_path = Path(cache_dir)
    
    if not cache_path.exists():
        logger.info(f"Répertoire de cache {cache_dir} n'existe pas")
        return True
    
    json_files = list(cache_path.glob("*.json"))
    valid_files = 0
    total_files = len(json_files)
    
    logger.info(f"Validation de {total_files} fichiers de cache...")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Vérifications de structure
            if not isinstance(data, dict):
                logger.warning(f"Format invalide: {json_file.name}")
                continue
                
            required_fields = ['description', 'metadata', 'timestamp', 'model_used']
            if not all(field in data for field in required_fields):
                logger.warning(f"Champs manquants: {json_file.name}")
                continue
            
            # Vérifier les types dans metadata
            metadata = data.get('metadata', {})
            if not isinstance(metadata, dict):
                logger.warning(f"Métadonnées invalides: {json_file.name}")
                continue
            
            valid_files += 1
            
        except Exception as e:
            logger.warning(f"Erreur validation {json_file.name}: {e}")
    
    logger.info(f"Validation terminée: {valid_files}/{total_files} fichiers valides")
    return valid_files == total_files

def main():
    """Fonction principale du script de nettoyage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nettoyage du cache d'images corrompu")
    parser.add_argument("--cache-dir", default="description_cache", 
                       help="Répertoire du cache (défaut: description_cache)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Afficher les fichiers à supprimer sans les supprimer")
    parser.add_argument("--validate-only", action="store_true", 
                       help="Seulement valider les fichiers sans nettoyage")
    
    args = parser.parse_args()
    
    logger.info("=== NETTOYAGE DU CACHE D'IMAGES ===")
    
    try:
        if args.validate_only:
            logger.info("Mode validation uniquement")
            is_valid = validate_cache_structure(args.cache_dir)
            if is_valid:
                logger.info("✓ Tous les fichiers de cache sont valides")
            else:
                logger.warning("⚠ Certains fichiers de cache sont corrompus")
                logger.info("Utilisez --clean pour les supprimer")
            return is_valid
        
        # Validation avant nettoyage
        logger.info("1. Validation du cache...")
        validate_cache_structure(args.cache_dir)
        
        # Nettoyage
        logger.info("2. Nettoyage des fichiers corrompus...")
        success = clean_corrupted_cache(args.cache_dir, args.dry_run)
        
        if success:
            logger.info("✓ Nettoyage terminé avec succès")
            if not args.dry_run:
                logger.info("3. Validation finale...")
                validate_cache_structure(args.cache_dir)
        else:
            logger.error("✗ Erreur lors du nettoyage")
            return False
        
        logger.info("=== NETTOYAGE TERMINÉ ===")
        return True
        
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1) 