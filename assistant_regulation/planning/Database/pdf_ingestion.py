"""
Script d'ingestion de documents PDF dans la base de données ChromaDB
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import logging

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.process_regulations import (
    process_regulation_document,
    process_single_pdf_file,
    get_default_config
)
from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever


class PDFIngestionManager:
    """Gestionnaire d'ingestion de documents PDF"""
    
    def __init__(self, base_path: str = None):
        """
        Initialize l'ingestion manager
        
        Args:
            base_path: Chemin de base pour les données (défaut: ./Data)
        """
        self.base_path = base_path or "./Data"
        self.config = get_default_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def ingest_from_folder(
        self, 
        folder_path: str, 
        text_only: bool = False,
        parallel: bool = True,
        workers: int = 4
    ) -> bool:
        """
        Ingère tous les PDFs d'un dossier dans la base de données
        Utilise process_regulation_document pour l'ingestion complète
        
        Args:
            folder_path: Chemin vers le dossier contenant les PDFs
            text_only: Si True, traite seulement le texte (plus rapide)
            parallel: Si True, utilise le traitement parallèle (ignoré pour l'instant)
            workers: Nombre de workers pour le traitement parallèle (ignoré pour l'instant)
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            if not os.path.exists(folder_path):
                self.logger.error(f"Le dossier {folder_path} n'existe pas")
                return False
            
            pdf_files = self._find_pdf_files(folder_path)
            if not pdf_files:
                self.logger.warning(f"Aucun fichier PDF trouvé dans {folder_path}")
                return True
            
            self.logger.info(f"Trouvé {len(pdf_files)} fichiers PDF à traiter")
            self.logger.info("Début de l'ingestion complète du dossier...")
            
            # Utiliser process_regulation_document pour traiter tout le dossier
            # Cette fonction nettoie la base et traite tous les PDFs d'un coup
            success = process_regulation_document(folder_path, text_only=text_only)
            
            if success:
                self.logger.info("Ingestion terminée avec succès")
                return True
            else:
                self.logger.error("Erreurs lors de l'ingestion")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ingestion: {e}")
            return False
    
    def ingest_single_pdf(self, pdf_path: str, text_only: bool = False) -> bool:
        """
        Ingère un seul fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            text_only: Si True, traite seulement le texte
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            if not os.path.exists(pdf_path):
                self.logger.error(f"Le fichier {pdf_path} n'existe pas")
                return False
            
            if not pdf_path.lower().endswith('.pdf'):
                self.logger.error(f"Le fichier {pdf_path} n'est pas un PDF")
                return False
            
            self.logger.info(f"Traitement du fichier: {pdf_path}")
            
            # Utiliser la nouvelle fonction pour traiter un seul fichier PDF
            success = process_single_pdf_file(pdf_path, text_only=text_only)
            
            if success:
                self.logger.info(f"Fichier {pdf_path} traité avec succès")
                return True
            else:
                self.logger.error(f"Erreur lors du traitement de {pdf_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de {pdf_path}: {e}")
            return False
    
    def _find_pdf_files(self, folder_path: str) -> List[str]:
        """Trouve tous les fichiers PDF dans un dossier"""
        pdf_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files
    
    def _process_sequential(self, pdf_files: List[str], text_only: bool) -> bool:
        """Traitement séquentiel des PDFs"""
        success_count = 0
        
        for pdf_file in pdf_files:
            try:
                if self.ingest_single_pdf(pdf_file, text_only=text_only):
                    success_count += 1
                else:
                    self.logger.warning(f"Échec du traitement de {pdf_file}")
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement de {pdf_file}: {e}")
        
        self.logger.info(f"Traitement terminé: {success_count}/{len(pdf_files)} fichiers réussis")
        return success_count == len(pdf_files)
    
    def _process_parallel(self, pdf_files: List[str], text_only: bool, workers: int) -> bool:
        """Traitement parallèle des PDFs"""
        try:
            from concurrent.futures import ThreadPoolExecutor
            
            def process_single(pdf_file):
                return self.ingest_single_pdf(pdf_file, text_only=text_only)
            
            success_count = 0
            with ThreadPoolExecutor(max_workers=workers) as executor:
                results = list(executor.map(process_single, pdf_files))
                success_count = sum(results)
            
            self.logger.info(f"Traitement parallèle terminé: {success_count}/{len(pdf_files)} fichiers réussis")
            return success_count == len(pdf_files)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement parallèle: {e}")
            return self._process_sequential(pdf_files, text_only)
    
    def verify_ingestion(self) -> dict:
        """Vérifie l'état de l'ingestion"""
        try:
            # Initialiser les retrievers pour vérifier les collections
            text_retriever = TextRetriever()
            
            stats = {
                "text_collection_exists": True,
                "text_documents_count": 0,
                "image_collection_exists": False,
                "image_documents_count": 0,
                "table_collection_exists": False,
                "table_documents_count": 0
            }
            
            try:
                # Vérifier collection de texte
                collection = text_retriever.collection
                if collection:
                    stats["text_documents_count"] = collection.count()
                else:
                    stats["text_collection_exists"] = False
            except Exception as e:
                self.logger.warning(f"Impossible de vérifier la collection text: {e}")
                stats["text_collection_exists"] = False
            
            try:
                # Vérifier collection d'images
                image_retriever = ImageRetriever()
                collection = image_retriever.collection
                if collection:
                    stats["image_collection_exists"] = True
                    stats["image_documents_count"] = collection.count()
            except Exception as e:
                self.logger.warning(f"Collection images non disponible: {e}")
            
            try:
                # Vérifier collection de tables
                table_retriever = TableRetriever()
                collection = table_retriever.collection
                if collection:
                    stats["table_collection_exists"] = True
                    stats["table_documents_count"] = collection.count()
            except Exception as e:
                self.logger.warning(f"Collection tables non disponible: {e}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification: {e}")
            return {}


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingestion de documents PDF dans ChromaDB')
    parser.add_argument('folder_path', help='Chemin vers le dossier contenant les PDFs')
    parser.add_argument('--text-only', action='store_true', help='Traiter seulement le texte (plus rapide)')
    parser.add_argument('--sequential', action='store_true', help='Traitement séquentiel (plus lent mais plus stable)')
    parser.add_argument('--workers', type=int, default=4, help='Nombre de workers pour le traitement parallèle')
    parser.add_argument('--single-file', help='Traiter un seul fichier PDF spécifique')
    parser.add_argument('--verify', action='store_true', help='Vérifier l\'état de l\'ingestion')
    
    args = parser.parse_args()
    
    manager = PDFIngestionManager()
    
    if args.verify:
        print("Vérification de l'état de la base de données...")
        stats = manager.verify_ingestion()
        print("\n=== État de la base de données ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        return
    
    if args.single_file:
        print(f"Traitement du fichier: {args.single_file}")
        success = manager.ingest_single_pdf(args.single_file, text_only=args.text_only)
    else:
        print(f"Ingestion depuis le dossier: {args.folder_path}")
        success = manager.ingest_from_folder(
            args.folder_path,
            text_only=args.text_only,
            parallel=not args.sequential,
            workers=args.workers
        )
    
    if success:
        print("Ingestion terminée avec succès!")
        
        # Afficher les statistiques
        stats = manager.verify_ingestion()
        print("\n=== Statistiques post-ingestion ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
    else:
        print("Erreurs lors de l'ingestion. Consultez les logs pour plus de détails.")


if __name__ == "__main__":
    main()