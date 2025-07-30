import os
import sys
import time
import pickle
import uuid
import logging
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
from .Modul_Process.chunking_text import hybrid_chunk_document
from .Modul_Process.chunking_image import pdf_to_image_chunks
from .Modul_Process.chunking_table import extract_tables
from .Modul_emb.TextRetriever import SimpleTextRetriever
from .Modul_emb.ImageRetriever import ImageRetriever
from .Modul_emb.TableRetriever import TableRetriever
from .Modul_Process.chunking_utils import process_pdf_directory
from .Modul_Process.describ_image import enrich_chunk_with_context

# Configuration du logging
def setup_logging():
    """Configure le logging avec gestion d'erreurs."""
    try:
        # Créer le répertoire logs s'il n'existe pas
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "process_regulations.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("Système de logging initialisé")
        return logger
    except Exception as e:
        print(f"Erreur lors de l'initialisation du logging: {e}")
        # Fallback vers un logger basique
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

logger = setup_logging()

def validate_pdf_directory(pdf_directory: str) -> bool:
    """Valide que le répertoire PDF existe et contient des fichiers PDF."""
    try:
        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            logger.error(f"Le répertoire {pdf_directory} n'existe pas")
            return False
        
        if not pdf_dir.is_dir():
            logger.error(f"{pdf_directory} n'est pas un répertoire")
            return False
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"Aucun fichier PDF trouvé dans {pdf_directory}")
            return False
        
        logger.info(f"Répertoire valide: {len(pdf_files)} fichiers PDF trouvés")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la validation du répertoire: {e}")
        return False

def process_text_chunks_with_late_chunker(pdf_directory: str) -> list:
    """
    Traite les chunks de texte avec Late Chunker (nouvelle solution optimale).
    """
    if not validate_pdf_directory(pdf_directory):
        return []
    
    pdf_dir = Path(pdf_directory)
    pdf_files = list(pdf_dir.glob("*.pdf"))
    all_chunks = []
    
    logger.info(f"Début du traitement de {len(pdf_files)} fichiers PDF")
    
    for pdf_file in tqdm(pdf_files, desc="Traitement des PDFs"):
        logger.info(f"Traitement Late Chunker: {pdf_file.name}")
        
        try:
            # Vérifier que le fichier existe et est lisible
            if not pdf_file.exists() or pdf_file.stat().st_size == 0:
                logger.warning(f"Fichier vide ou inexistant: {pdf_file.name}")
                continue
            
            # Utilisation du Late Chunker (15x plus rapide, contexte global préservé)
            chunks = hybrid_chunk_document(
                source_path=str(pdf_file),
                embed_model_id="all-MiniLM-L6-v2",
                max_tokens=1024  # Optimal pour documents réglementaires
            )
            
            if chunks:
                all_chunks.extend(chunks)
                logger.info(f"Chunks extraits de {pdf_file.name}: {len(chunks)}")
            else:
                logger.warning(f"Aucun chunk extrait de {pdf_file.name}")
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {pdf_file.name}: {e}")
            continue
    
    logger.info(f"Traitement terminé: {len(all_chunks)} chunks au total")
    return all_chunks

def remove_duplicates(chunks):
    """Supprime les chunks dupliqués basés sur leur ID."""
    if not chunks:
        return []
    
    try:
        seen_ids = set()
        unique_chunks = []
        
        for chunk in chunks:
            if not isinstance(chunk, dict):
                logger.warning(f"Chunk invalide ignoré: {type(chunk)}")
                continue
                
            chunk_id = chunk.get("id")
            if not chunk_id:
                # Générer un ID si manquant
                chunk_id = str(uuid.uuid4())
                chunk["id"] = chunk_id
                
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
        
        removed_count = len(chunks) - len(unique_chunks)
        if removed_count > 0:
            logger.info(f"Supprimé {removed_count} chunks dupliqués")
        
        return unique_chunks
    except Exception as e:
        logger.error(f"Erreur lors de la suppression des doublons: {e}")
        return chunks

def save_chunks_to_file(chunks, file_path):
    """Sauvegarde les chunks dans un fichier pour éviter de refaire le chunking en cas d'échec."""
    if not chunks:
        logger.warning("Aucun chunk à sauvegarder")
        return False
        
    try:
        # Créer le répertoire parent si nécessaire
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder avec une version temporaire pour éviter la corruption
        temp_path = file_path.with_suffix('.tmp')
        with open(temp_path, "wb") as f:
            pickle.dump(chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Renommer le fichier temporaire
        temp_path.replace(file_path)
        
        logger.info(f"Chunks sauvegardés: {len(chunks)} dans {file_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des chunks: {e}")
        return False

def load_chunks_from_file(file_path):
    """Charge les chunks depuis un fichier s'ils existent."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.info(f"Fichier de chunks non trouvé: {file_path}")
        return None
        
    try:
        with open(file_path, "rb") as f:
            chunks = pickle.load(f)
        
        if not isinstance(chunks, list):
            logger.error(f"Format de chunks invalide dans {file_path}")
            return None
            
        logger.info(f"Chunks chargés: {len(chunks)} depuis {file_path}")
        return chunks
    except Exception as e:
        logger.error(f"Erreur lors du chargement des chunks: {e}")
        # Essayer de récupérer avec un fichier de sauvegarde
        backup_path = file_path.with_suffix('.backup')
        if backup_path.exists():
            try:
                with open(backup_path, "rb") as f:
                    chunks = pickle.load(f)
                logger.info(f"Chunks récupérés depuis la sauvegarde: {backup_path}")
                return chunks
            except Exception:
                logger.error(f"Impossible de récupérer depuis la sauvegarde")
        return None

def clean_database_collections():
    """Nettoie les collections de la base de données."""
    try:
        logger.info("Nettoyage de la base de données...")
        
        # Initialiser temporairement pour nettoyer
        temp_text_retriever = SimpleTextRetriever()
        temp_image_retriever = ImageRetriever()
        temp_table_retriever = TableRetriever()
        
        # Nettoyer les collections
        try:
            temp_text_retriever.client.delete_collection("hierarchical_text")
        except Exception as e:
            logger.warning(f"Collection 'hierarchical_text' déjà supprimée ou introuvable: {e}")
            
        try:
            temp_image_retriever.client.delete_collection("pdf_images")
        except Exception as e:
            logger.warning(f"Collection 'pdf_images' déjà supprimée ou introuvable: {e}")
            
        try:
            temp_table_retriever.client.delete_collection("pdf_tables")
        except Exception as e:
            logger.warning(f"Collection 'pdf_tables' déjà supprimée ou introuvable: {e}")
        
        logger.info("Base de données nettoyée avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage de la base de données: {e}")
        return False

def ensure_chunk_ids(chunk_list):
    """Garantit que chaque chunk possède un ID unique et cohérent.

    - Si le champ `chunk_id` existe, il est utilisé comme source principale.
    - Si l'ID est dupliqué, un nouvel UUID est généré et appliqué à **chunk_id** et **id**.
    - S'il manque un champ, il est créé.
    """
    if not chunk_list:
        return []

    try:
        seen_ids = set()

        for chunk in chunk_list:
            if not isinstance(chunk, dict):
                continue

            # Déterminer l'ID existant (chunk_id prioritaire)
            current_id = chunk.get("chunk_id") or chunk.get("id")

            # Si dupliqué ou absent → générer nouveau UUID
            if not current_id or current_id in seen_ids:
                current_id = str(uuid.uuid4())

            # Mettre à jour les deux clés pour cohérence
            chunk["chunk_id"] = current_id
            chunk["id"] = current_id

            seen_ids.add(current_id)

        return chunk_list
    except Exception as e:
        logger.error(f"Erreur lors de l'assignation des IDs: {e}")
        return chunk_list

def clean_chunk_metadata(chunks):
    """
    Nettoie les métadonnées des chunks pour s'assurer qu'elles sont compatibles avec ChromaDB.
    ChromaDB ne supporte que: str, int, float, bool et None.
    """
    if not chunks:
        return []
    
    import json
    cleaned_chunks = []
    
    for chunk in chunks:
        if not isinstance(chunk, dict):
            logger.warning(f"Chunk non-dict ignoré: {type(chunk)}")
            continue
        
        try:
            cleaned_chunk = {}
            
            for key, value in chunk.items():
                # Types supportés directement
                if isinstance(value, (str, int, float, bool)) or value is None:
                    cleaned_chunk[key] = value
                
                # Listes: convertir en string JSON ou prendre le premier élément selon le contexte
                elif isinstance(value, list):
                    if key == 'page_numbers' and value and all(isinstance(x, (int, float)) for x in value):
                        # Cas spécial: garder le premier numéro de page comme int
                        cleaned_chunk[key] = int(value[0])
                        cleaned_chunk[f'{key}_str'] = ','.join(map(str, value))
                    else:
                        try:
                            cleaned_chunk[key] = json.dumps(value)
                        except (TypeError, ValueError):
                            cleaned_chunk[key] = str(value)
                
                # Dictionnaires: convertir en string JSON
                elif isinstance(value, dict):
                    try:
                        cleaned_chunk[key] = json.dumps(value)
                    except (TypeError, ValueError):
                        cleaned_chunk[key] = str(value)
                
                # Autres types: convertir en string
                else:
                    try:
                        cleaned_chunk[key] = str(value)
                    except Exception:
                        logger.warning(f"Impossible de convertir {key}: {type(value)}")
                        continue
            
            cleaned_chunks.append(cleaned_chunk)
            
        except Exception as e:
            logger.error(f"Erreur nettoyage chunk: {e}")
            # En cas d'erreur, essayer de sauver au moins les champs basiques
            try:
                basic_chunk = {
                    'id': chunk.get('id', str(uuid.uuid4())),
                    'text': str(chunk.get('text', '')),
                    'document_name': str(chunk.get('document_name', 'unknown')),
                    'page_no': int(chunk.get('page_numbers', [0])[0] if chunk.get('page_numbers') else 0)
                }
                cleaned_chunks.append(basic_chunk)
            except Exception:
                logger.error(f"Impossible de nettoyer le chunk, ignoré")
                continue
    
    logger.info(f"Nettoyage terminé: {len(cleaned_chunks)}/{len(chunks)} chunks conservés")
    return cleaned_chunks

def store_chunks_safely(text_retriever, image_retriever, table_retriever, 
                       text_chunks, image_chunks, table_chunks):
    """Stocke les chunks avec gestion d'erreurs améliorée."""
    import traceback
    success_count = 0
    
    # Stocker les chunks de texte
    if text_chunks:
        try:
            logger.info(f"Début stockage chunks texte: {len(text_chunks)} chunks")
            
            # Nettoyer les métadonnées avant stockage
            cleaned_text_chunks = clean_chunk_metadata(text_chunks)
            logger.info(f"Chunks texte nettoyés: {len(cleaned_text_chunks)} chunks")
            
            text_retriever.store_chunks(cleaned_text_chunks)
            logger.info(f"Chunks texte stockés avec succès: {len(cleaned_text_chunks)}")
            success_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du stockage des chunks texte: {e}")
            logger.error(f"Traceback complet:")
            logger.error(traceback.format_exc())
            
            # Diagnostiquer le problème
            try:
                logger.info("Analyse du premier chunk texte problématique:")
                if text_chunks:
                    first_chunk = text_chunks[0]
                    logger.info(f"Type: {type(first_chunk)}")
                    if isinstance(first_chunk, dict):
                        for key, value in first_chunk.items():
                            logger.info(f"  {key}: {type(value)} = {str(value)[:100]}...")
            except Exception as diag_e:
                logger.error(f"Erreur lors du diagnostic: {diag_e}")
    
    # Stocker les chunks d'images
    if image_chunks:
        try:
            logger.info(f"Début stockage chunks image: {len(image_chunks)} chunks")
            cleaned_image_chunks = clean_chunk_metadata(image_chunks)
            image_retriever.store_chunks(cleaned_image_chunks)
            logger.info(f"Chunks image stockés avec succès: {len(cleaned_image_chunks)}")
            success_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du stockage des chunks image: {e}")
            logger.error(traceback.format_exc())
    
    # Stocker les chunks de tableaux
    if table_chunks:
        try:
            logger.info(f"Début stockage chunks tableau: {len(table_chunks)} chunks")
            cleaned_table_chunks = clean_chunk_metadata(table_chunks)
            table_retriever.store_chunks(cleaned_table_chunks)
            logger.info(f"Chunks tableau stockés avec succès: {len(cleaned_table_chunks)}")
            success_count += 1
        except Exception as e:
            logger.error(f"Erreur lors du stockage des chunks tableau: {e}")
            logger.error(traceback.format_exc())
 
    # --------------------------------------------------------------
    # Persistance immédiate pour rendre les données visibles
    # --------------------------------------------------------------
    try:
        for client in {text_retriever.client, image_retriever.client, table_retriever.client}:
            client.persist()
    except Exception:
        pass  # Ignorer les erreurs de persistance

    return success_count

def ensure_chunk_ids(chunks):
    """Assure que chaque chunk a un ID unique pour éviter les conflits dans ChromaDB."""
    import uuid
    import hashlib
    
    if not chunks:
        return []
    
    unique_chunks = []
    
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
            
        # Créer un ID unique basé sur le contenu et les métadonnées
        content_for_id = f"{chunk.get('text', '')[:200]}_{chunk.get('regulation_code', 'unknown')}_{chunk.get('chunk_index', 0)}"
        unique_id = hashlib.md5(content_for_id.encode()).hexdigest()
        
        # Ajouter un timestamp pour garantir l'unicité
        import time
        unique_id = f"{unique_id}_{int(time.time()*1000000) % 1000000}"
        
        # Mettre à jour l'ID
        chunk_copy = chunk.copy()
        chunk_copy['id'] = unique_id
        chunk_copy['chunk_id'] = unique_id  # Backup au cas où
        
        unique_chunks.append(chunk_copy)
    
    logger.info(f"IDs uniques générés pour {len(unique_chunks)} chunks")
    return unique_chunks

def process_regulation_document(folder_path, *, text_only: bool = False):
    """
    Traite un document réglementaire avec gestion d'erreurs robuste.
    """
    start_time = time.time()
    logger.info(f"=== DÉBUT DU TRAITEMENT POUR {folder_path} ===")

    try:
        # 1. Validation du répertoire
        if not validate_pdf_directory(folder_path):
            logger.error("Arrêt du traitement: répertoire invalide")
            return False

        # 2. Nettoyage de la base de données
        if not clean_database_collections():
            logger.error("Arrêt du traitement: nettoyage de la base échoué")
            return False

        # 3. Initialisation des retrievers
        try:
            text_retriever = SimpleTextRetriever()
            image_retriever = ImageRetriever()
            table_retriever = TableRetriever()
            logger.info("Retrievers initialisés avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des retrievers: {e}")
            return False

        # 4. Chargement des chunks depuis les fichiers
        data_dir = Path("Data")
        
        result_text = load_chunks_from_file(data_dir / "chunks_text.pkl")

        if text_only:
            result_image = []
            result_table = []
        else:
            result_image = load_chunks_from_file(data_dir / "chunks_image.pkl")
            result_table = load_chunks_from_file(data_dir / "chunks_table.pkl")

        # Vérifier qu'au moins un type de chunks est disponible
        if not any([result_text, result_image, result_table]):
            logger.error("Aucun chunk trouvé dans les fichiers de données")
            return False

        # 5. Traitement des chunks
        # Générer des IDs uniques et nettoyer
        if result_text:
            result_text = ensure_chunk_ids(result_text)
            result_text = remove_duplicates(result_text)
        else:
            result_text = []
            
        if result_image:
            result_image = ensure_chunk_ids(result_image)
            result_image = remove_duplicates(result_image)
        else:
            result_image = []
            
        if result_table:
            result_table = ensure_chunk_ids(result_table)
            result_table = remove_duplicates(result_table)
        else:
            result_table = []

        # 6. Stockage dans les retrievers
        success_count = store_chunks_safely(
            text_retriever, image_retriever, table_retriever,
            result_text, result_image, result_table
        )

        # 7. Rapport final
        total_time = time.time() - start_time
        total_chunks = len(result_text) + (0 if text_only else len(result_image) + len(result_table))
        
        logger.info(f"=== TRAITEMENT TERMINÉ ===")
        logger.info(f"Durée: {total_time:.2f} secondes")
        if text_only:
            logger.info(f"Chunks traités: {len(result_text)} textes (mode text-only)")
        else:
            logger.info(f"Chunks traités: {len(result_text)} textes, {len(result_image)} images, {len(result_table)} tableaux")
        logger.info(f"Total: {total_chunks} chunks")
        logger.info(f"Retrievers mis à jour avec succès: {success_count}/{'1' if text_only else '3'}")
        
        return success_count >= 1  # Succès si au moins un retriever a fonctionné

    except Exception as e:
        logger.error(f"Erreur fatale lors du traitement: {e}")
        return False

def main():
    """Fonction principale avec gestion des arguments de ligne de commande."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Traite les documents réglementaires et stocke les chunks dans la base vectorielle"
    )
    parser.add_argument(
        "--data-dir", 
        default="Data", 
        help="Répertoire contenant les fichiers PDF (défaut: Data)"
    )
    parser.add_argument(
        "--clean-only", 
        action="store_true", 
        help="Nettoie seulement la base de données sans traiter"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Mode test: valide l'environnement sans traitement"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Mode verbeux avec plus de logs"
    )
    parser.add_argument(
        "--regenerate", 
        action="store_true", 
        help="Régénère les chunks depuis zéro à partir des PDFs"
    )
    parser.add_argument(
        "--regenerate-parallel", 
        action="store_true", 
        help="Régénère les chunks en parallèle (plus rapide)"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=3, 
        help="Nombre de workers parallèles (défaut: 3)"
    )
    parser.add_argument(
        "--output-dir", 
        default="Data", 
        help="Répertoire de sortie pour les chunks (défaut: Data)"
    )
    parser.add_argument(
        "--no-image-description", 
        action="store_true", 
        help="Désactive la génération automatique de descriptions d'images"
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Traite uniquement les chunks de texte (ignore images et tableaux)"
    )
    
    args = parser.parse_args()
    
    # Configuration du niveau de log
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.test:
            logger.info("=== MODE TEST ===")
            return test_environment(args.data_dir)
        
        elif args.clean_only:
            logger.info("=== NETTOYAGE UNIQUEMENT ===")
            return clean_database_collections()
        
        elif args.regenerate:
            logger.info("=== RÉGÉNÉRATION DE CHUNKS ===")
            enable_desc = not args.no_image_description and not args.text_only
            if enable_desc:
                logger.info("Description d'images activée")
            else:
                logger.info("Description d'images désactivée")
            success = generate_chunks_from_scratch(
                args.data_dir,
                args.output_dir,
                enable_desc,
                text_only=args.text_only
            )
            if success:
                logger.info("Régénération terminée. Lancement du traitement...")
                return process_regulation_document(args.data_dir, text_only=args.text_only)
            return False
        
        elif args.regenerate_parallel:
            logger.info("=== RÉGÉNÉRATION PARALLÈLE DE CHUNKS ===")
            enable_desc = not args.no_image_description and not args.text_only
            if enable_desc:
                logger.info("Description d'images activée")
            else:
                logger.info("Description d'images désactivée")
            success = generate_chunks_parallel(
                args.data_dir,
                args.output_dir,
                args.workers,
                enable_desc,
                text_only=args.text_only
            )
            if success:
                logger.info("Régénération parallèle terminée. Lancement du traitement...")
                return process_regulation_document(args.data_dir, text_only=args.text_only)
            return False
        
        else:
            logger.info("=== TRAITEMENT COMPLET (CHUNKS EXISTANTS) ===")
            return process_regulation_document(args.data_dir, text_only=args.text_only)
            
    except KeyboardInterrupt:
        logger.info("Traitement interrompu par l'utilisateur")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False

def generate_chunks_from_scratch(pdf_directory: str, data_dir: str = "Data", enable_image_description: bool = True, *, text_only: bool = False) -> bool:
    """
    Génère tous les chunks depuis zéro à partir des fichiers PDF.
    
    Args:
        pdf_directory: Répertoire contenant les PDFs
        data_dir: Répertoire où sauvegarder les chunks
        
    Returns:
        True si la génération a réussi
    """
    logger.info("=== GÉNÉRATION DE CHUNKS DEPUIS ZÉRO ===")
    
    if not validate_pdf_directory(pdf_directory):
        return False
    
    try:
        # Créer le répertoire de données
        data_path = Path(data_dir)
        data_path.mkdir(exist_ok=True)
        
        # Génération des chunks de texte
        logger.info("1/3 - Génération des chunks de texte...")
        text_chunks = generate_text_chunks(pdf_directory)
        if text_chunks:
            text_file = data_path / "chunks_text.pkl"
            if save_chunks_to_file(text_chunks, text_file):
                logger.info(f"✓ Chunks texte sauvegardés: {len(text_chunks)}")
            else:
                logger.error("✗ Erreur sauvegarde chunks texte")
                return False
        else:
            logger.warning("Aucun chunk de texte généré")
        
        if text_only:
            image_chunks = []
            table_chunks = []
        else:
            # Génération des chunks d'images
            logger.info("2/3 - Génération des chunks d'images...")
            image_chunks = generate_image_chunks(pdf_directory, enable_description=enable_image_description)
            if image_chunks:
                image_file = data_path / "chunks_image.pkl"
                if save_chunks_to_file(image_chunks, image_file):
                    logger.info(f"✓ Chunks image sauvegardés: {len(image_chunks)}")
                else:
                    logger.error("✗ Erreur sauvegarde chunks image")
                    return False
            else:
                logger.warning("Aucun chunk d'image généré")
            
            # Génération des chunks de tableaux
            logger.info("3/3 - Génération des chunks de tableaux...")
            table_chunks = generate_table_chunks(pdf_directory)
            if table_chunks:
                table_file = data_path / "chunks_table.pkl"
                if save_chunks_to_file(table_chunks, table_file):
                    logger.info(f"✓ Chunks tableau sauvegardés: {len(table_chunks)}")
                else:
                    logger.error("✗ Erreur sauvegarde chunks tableau")
                    return False
            else:
                logger.warning("Aucun chunk de tableau généré")
        
        total_chunks = len(text_chunks) + (0 if text_only else len(image_chunks) + len(table_chunks))
        logger.info(f"=== GÉNÉRATION TERMINÉE ===")
        logger.info(f"Total chunks générés: {total_chunks}")
        if text_only:
            logger.info(f"- Texte: {len(text_chunks)} (mode text-only)")
        else:
            logger.info(f"- Texte: {len(text_chunks)}")
            logger.info(f"- Images: {len(image_chunks)}")
            logger.info(f"- Tableaux: {len(table_chunks)}")
        
        return total_chunks > 0
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération des chunks: {e}")
        return False

def generate_text_chunks(pdf_directory: str) -> List[Dict]:
    """Génère les chunks de texte à partir des PDFs avec métadonnées."""
    logger.info("Début de la génération des chunks de texte...")
    
    try:
        from .Modul_Process.chunking_utils import extract_document_metadata
        
        pdf_dir = Path(pdf_directory)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        all_text_chunks = []
        
        for pdf_file in tqdm(pdf_files, desc="Génération chunks texte"):
            logger.debug(f"Traitement texte: {pdf_file.name}")
            
            try:
                # Extraire les métadonnées du document
                metadata = extract_document_metadata(str(pdf_file))
                
                # Générer les chunks avec Late Chunker
                chunks = hybrid_chunk_document(
                    source_path=str(pdf_file),
                    embed_model_id="all-MiniLM-L6-v2",
                    max_tokens=1024
                )
                
                if chunks:
                    # Ajouter les métadonnées à tous les chunks
                    for chunk in chunks:
                        chunk.update(metadata)
                        # S'assurer que l'ID est unique
                        if not chunk.get("id"):
                            chunk["id"] = str(uuid.uuid4())
                    
                    all_text_chunks.extend(chunks)
                    logger.debug(f"Chunks texte de {pdf_file.name}: {len(chunks)}")
                    
            except Exception as e:
                logger.error(f"Erreur traitement texte de {pdf_file.name}: {e}")
                continue
        
        logger.info(f"Total chunks de texte générés: {len(all_text_chunks)}")
        return all_text_chunks
        
    except Exception as e:
        logger.error(f"Erreur génération chunks texte: {e}")
        return []

def generate_image_chunks(pdf_directory: str, enable_description: bool = True) -> List[Dict]:
    """Génère les chunks d'images à partir des PDFs avec description automatique et métadonnées."""
    logger.info("Début de la génération des chunks d'images...")
    
    try:
        from .Modul_Process.chunking_utils import extract_document_metadata
        
        pdf_dir = Path(pdf_directory)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        all_image_chunks = []
        
        # Initialiser le descripteur d'images si activé
        if enable_description:
            try:
                from .Modul_Process.describ_image import enrich_chunk_with_context
                logger.info("Description automatique des images activée")
            except ImportError as e:
                logger.warning(f"Impossible d'importer le descripteur d'images: {e}")
                enable_description = False
        
        for pdf_file in tqdm(pdf_files, desc="Extraction d'images"):
            logger.debug(f"Traitement images: {pdf_file.name}")
            
            try:
                # Extraire les métadonnées du document
                metadata = extract_document_metadata(str(pdf_file))
                
                # Utiliser la fonction d'extraction d'images
                chunks = pdf_to_image_chunks(str(pdf_file))
                
                if chunks:
                    # Ajouter les métadonnées à tous les chunks d'abord
                    for chunk in chunks:
                        chunk.update(metadata)
                        # S'assurer que l'ID est unique
                        if not chunk.get("id"):
                            chunk["id"] = str(uuid.uuid4())
                    
                    # Enrichir avec des descriptions si activé
                    if enable_description:
                        enriched_chunks = []
                        
                        logger.info(f"Génération de descriptions pour {len(chunks)} images de {pdf_file.name}")
                        
                        for i, chunk in enumerate(chunks):
                            try:
                                # Ajouter une description automatique
                                enriched_chunk = enrich_chunk_with_context(chunk)
                                enriched_chunks.append(enriched_chunk)
                                
                                if (i + 1) % 5 == 0:  # Log tous les 5 chunks
                                    logger.debug(f"Descriptions générées: {i + 1}/{len(chunks)}")
                                    
                            except Exception as e:
                                logger.warning(f"Erreur description chunk {i}: {e}")
                                # Garder le chunk sans description en cas d'erreur
                                chunk["description"] = f"Erreur de description: {str(e)}"
                                chunk["model_used"] = "error"
                                enriched_chunks.append(chunk)
                        
                        all_image_chunks.extend(enriched_chunks)
                        logger.info(f"Images enrichies de {pdf_file.name}: {len(enriched_chunks)}")
                    else:
                        # Ajouter sans description
                        for chunk in chunks:
                            chunk["description"] = "Description automatique désactivée"
                            chunk["model_used"] = "disabled"
                        all_image_chunks.extend(chunks)
                        logger.debug(f"Images extraites de {pdf_file.name}: {len(chunks)}")
                    
            except Exception as e:
                logger.error(f"Erreur extraction images de {pdf_file.name}: {e}")
                continue
        
        logger.info(f"Total chunks d'images générés: {len(all_image_chunks)}")
        if enable_description:
            described_count = len([c for c in all_image_chunks if c.get("model_used") not in ["error", "disabled", "skipped"]])
            logger.info(f"Chunks avec description: {described_count}/{len(all_image_chunks)}")
        
        return all_image_chunks
        
    except Exception as e:
        logger.error(f"Erreur génération chunks images: {e}")
        return []

def generate_table_chunks(pdf_directory: str) -> List[Dict]:
    """Génère les chunks de tableaux à partir des PDFs avec métadonnées."""
    logger.info("Début de la génération des chunks de tableaux...")
    
    try:
        from .Modul_Process.chunking_utils import extract_document_metadata
        
        pdf_dir = Path(pdf_directory)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        all_table_chunks = []
        
        for pdf_file in tqdm(pdf_files, desc="Extraction de tableaux"):
            logger.debug(f"Traitement tableaux: {pdf_file.name}")
            
            try:
                # Extraire les métadonnées du document
                metadata = extract_document_metadata(str(pdf_file))
                
                # Utiliser la fonction d'extraction de tableaux
                chunks = extract_tables(str(pdf_file))
                
                if chunks:
                    # Ajouter les métadonnées à tous les chunks
                    for chunk in chunks:
                        chunk.update(metadata)
                        # S'assurer que l'ID est unique
                        if not chunk.get("id"):
                            chunk["id"] = str(uuid.uuid4())
                    
                    all_table_chunks.extend(chunks)
                    logger.debug(f"Tableaux extraits de {pdf_file.name}: {len(chunks)}")
                    
            except Exception as e:
                logger.error(f"Erreur extraction tableaux de {pdf_file.name}: {e}")
                continue
        
        logger.info(f"Total chunks de tableaux générés: {len(all_table_chunks)}")
        return all_table_chunks
        
    except Exception as e:
        logger.error(f"Erreur génération chunks tableaux: {e}")
        return []

def generate_chunks_parallel(pdf_directory: str, data_dir: str = "Data", max_workers: int = 3, enable_image_description: bool = True, *, text_only: bool = False) -> bool:
    """
    Génère les chunks en parallèle pour améliorer les performances.
    
    Args:
        pdf_directory: Répertoire contenant les PDFs
        data_dir: Répertoire où sauvegarder les chunks
        max_workers: Nombre de workers parallèles
        
    Returns:
        True si la génération a réussi
    """
    logger.info("=== GÉNÉRATION PARALLÈLE DE CHUNKS ===")
    
    if not validate_pdf_directory(pdf_directory):
        return False
    
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Créer le répertoire de données
        data_path = Path(data_dir)
        data_path.mkdir(exist_ok=True)
        
        # Liste des tâches (type, fonction de génération, fichier de sortie)
        tasks = [("text", generate_text_chunks, "chunks_text.pkl")]
        if not text_only:
            tasks.extend([
                ("image", lambda pdf_dir: generate_image_chunks(pdf_dir, enable_description=enable_image_description), "chunks_image.pkl"),
                ("table", generate_table_chunks, "chunks_table.pkl")
            ])
        
        results = {}
        
        # Exécution parallèle avec ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_type = {
                executor.submit(task_func, pdf_directory): (chunk_type, filename)
                for chunk_type, task_func, filename in tasks
            }
            
            # Récupérer les résultats
            for future in as_completed(future_to_type):
                chunk_type, filename = future_to_type[future]
                
                try:
                    chunks = future.result()
                    results[chunk_type] = chunks
                    
                    # Sauvegarder immédiatement
                    file_path = data_path / filename
                    if save_chunks_to_file(chunks, file_path):
                        logger.info(f"✓ {chunk_type}: {len(chunks)} chunks sauvegardés")
                    else:
                        logger.error(f"✗ Erreur sauvegarde {chunk_type}")
                        
                except Exception as e:
                    logger.error(f"Erreur génération {chunk_type}: {e}")
                    results[chunk_type] = []
        
        # Résumé final
        total_chunks = sum(len(chunks) for chunks in results.values())
        logger.info(f"=== GÉNÉRATION PARALLÈLE TERMINÉE ===")
        logger.info(f"Total chunks générés: {total_chunks}")
        if text_only:
            logger.info(f"- Texte: {len(results.get('text', []))} (mode text-only)")
        else:
            for chunk_type, chunks in results.items():
                logger.info(f"- {chunk_type.capitalize()}: {len(chunks)}")
        
        return total_chunks > 0
        
    except Exception as e:
        logger.error(f"Erreur génération parallèle: {e}")
        return False

def test_environment(data_dir):
    """Test l'environnement avant traitement."""
    logger.info("Test de l'environnement...")
    
    success = True
    
    # Test 1: Répertoire de données
    if validate_pdf_directory(data_dir):
        logger.info("✓ Répertoire de données valide")
    else:
        logger.error("✗ Répertoire de données invalide")
        success = False
    
    # Test 2: Fichiers de chunks
    data_dir_path = Path(data_dir)
    chunk_files = [
        "chunks_text.pkl",
        "chunks_image.pkl", 
        "chunks_table.pkl"
    ]
    
    found_chunks = 0
    for chunk_file in chunk_files:
        chunk_path = data_dir_path / chunk_file
        if chunk_path.exists():
            try:
                chunks = load_chunks_from_file(chunk_path)
                if chunks:
                    logger.info(f"✓ {chunk_file}: {len(chunks)} chunks")
                    found_chunks += 1
                else:
                    logger.warning(f"? {chunk_file}: fichier vide")
            except Exception as e:
                logger.error(f"✗ {chunk_file}: erreur de lecture - {e}")
        else:
            logger.warning(f"? {chunk_file}: fichier manquant")
    
    if found_chunks == 0:
        logger.error("✗ Aucun fichier de chunks valide trouvé")
        success = False
    else:
        logger.info(f"✓ {found_chunks}/3 fichiers de chunks trouvés")
    
    # Test 3: Retrievers
    try:
        from .Modul_emb.TextRetriever import SimpleTextRetriever
        from .Modul_emb.ImageRetriever import ImageRetriever
        from .Modul_emb.TableRetriever import TableRetriever
        
        SimpleTextRetriever()
        ImageRetriever()
        TableRetriever()
        logger.info("✓ Retrievers initialisables")
    except Exception as e:
        logger.error(f"✗ Erreur d'initialisation des retrievers: {e}")
        success = False
    
    # Test 4: Répertoire de logs
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        logger.info("✓ Répertoire de logs disponible")
    except Exception as e:
        logger.error(f"✗ Erreur avec le répertoire de logs: {e}")
        success = False
    
    if success:
        logger.info("✓ Environnement prêt pour le traitement")
    else:
        logger.error("✗ Problèmes détectés dans l'environnement")
    
    return success

# Usage
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
