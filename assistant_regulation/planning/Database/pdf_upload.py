"""
Script pour uploader un ou plusieurs PDFs dans une base de données existante
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.process_regulations import (
    process_regulation_document,
    process_single_pdf_file,
    get_default_config
)
from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever


class PDFUploadManager:
    """Gestionnaire d'upload de PDFs dans une base existante"""
    
    def __init__(self, data_folder: str = "./Data"):
        """
        Initialize l'upload manager
        
        Args:
            data_folder: Dossier où stocker les PDFs uploadés
        """
        self.data_folder = data_folder
        self.config = get_default_config()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Créer le dossier data s'il n'existe pas
        os.makedirs(self.data_folder, exist_ok=True)
    
    def check_database_status(self) -> Dict[str, Any]:
        """
        Vérifie l'état de la base de données existante
        
        Returns:
            Dict avec informations sur la base existante
        """
        try:
            status = {
                "database_exists": False,
                "collections": {},
                "total_documents": 0,
                "regulations_count": 0,
                "can_upload": False
            }
            
            # Vérifier la collection text
            try:
                text_retriever = TextRetriever()
                if text_retriever.collection:
                    count = text_retriever.collection.count()
                    status["collections"]["text"] = {
                        "exists": True,
                        "count": count
                    }
                    status["total_documents"] += count
                    status["database_exists"] = True
                else:
                    status["collections"]["text"] = {"exists": False, "count": 0}
            except Exception as e:
                self.logger.warning(f"Erreur collection text: {e}")
                status["collections"]["text"] = {"exists": False, "count": 0, "error": str(e)}
            
            # Obtenir le nombre de réglementations
            if status["database_exists"]:
                try:
                    regulations = set()
                    results = text_retriever.collection.get(include=['metadatas'])
                    for metadata in results.get('metadatas', []):
                        if metadata and metadata.get('regulation_code'):
                            regulations.add(metadata['regulation_code'])
                    status["regulations_count"] = len(regulations)
                except Exception as e:
                    self.logger.warning(f"Impossible de compter les réglementations: {e}")
            
            status["can_upload"] = status["database_exists"]
            return status
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification du statut: {e}")
            return {"database_exists": False, "can_upload": False, "error": str(e)}
    
    def upload_single_pdf(
        self, 
        pdf_path: str, 
        copy_to_data: bool = True,
        text_only: bool = False,
        overwrite_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Upload un seul PDF dans la base existante
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            copy_to_data: Si True, copie le PDF dans le dossier data
            text_only: Si True, traite seulement le texte (plus rapide)
            overwrite_existing: Si True, écrase le fichier existant
            
        Returns:
            Dict avec résultat de l'upload
        """
        result = {
            "success": False,
            "pdf_path": pdf_path,
            "copied_to": None,
            "processed": False,
            "error": None,
            "chunks_added": 0
        }
        
        try:
            # Vérifier que le PDF existe
            if not os.path.exists(pdf_path):
                result["error"] = f"Le fichier {pdf_path} n'existe pas"
                return result
            
            if not pdf_path.lower().endswith('.pdf'):
                result["error"] = f"Le fichier {pdf_path} n'est pas un PDF"
                return result
            
            # Vérifier l'état de la base
            db_status = self.check_database_status()
            if not db_status.get("can_upload", False):
                result["error"] = "Base de données non accessible ou inexistante"
                return result
            
            filename = os.path.basename(pdf_path)
            target_path = os.path.join(self.data_folder, filename)
            
            # Copier le fichier si demandé
            if copy_to_data:
                if os.path.exists(target_path) and not overwrite_existing:
                    result["error"] = f"Le fichier {filename} existe déjà dans {self.data_folder}. Utilisez --overwrite pour écraser."
                    return result
                
                try:
                    shutil.copy2(pdf_path, target_path)
                    result["copied_to"] = target_path
                    self.logger.info(f"PDF copié vers: {target_path}")
                except Exception as e:
                    result["error"] = f"Erreur lors de la copie: {e}"
                    return result
            
            # Traiter le PDF
            source_path = target_path if copy_to_data else pdf_path
            source_folder = os.path.dirname(source_path)
            source_filename = os.path.basename(source_path)
            
            # Compter les documents avant traitement
            count_before = db_status.get("total_documents", 0)
            
            self.logger.info(f"Traitement du PDF: {source_filename}")
            self.logger.info(f"text_only parameter dans PDFUploadManager: {text_only}")
            
            # Utiliser la nouvelle fonction pour traiter un seul fichier PDF
            source_path = os.path.join(source_folder, source_filename)
            self.logger.info(f"Appel de process_single_pdf_file avec path: {source_path}")
            processed = process_single_pdf_file(source_path, text_only=text_only)
            self.logger.info(f"process_single_pdf_file retourné: {processed}")
            
            if processed:
                result["processed"] = True
                
                # Compter les documents après traitement
                db_status_after = self.check_database_status()
                count_after = db_status_after.get("total_documents", 0)
                result["chunks_added"] = count_after - count_before
                
                result["success"] = True
                self.logger.info(f"PDF traité avec succès: {result['chunks_added']} nouveaux chunks")
            else:
                result["error"] = "Erreur lors du traitement du PDF"
                
        except Exception as e:
            result["error"] = f"Erreur lors de l'upload: {e}"
            self.logger.error(f"Erreur lors de l'upload de {pdf_path}: {e}")
        
        return result
    
    def upload_multiple_pdfs(
        self, 
        pdf_paths: List[str], 
        copy_to_data: bool = True,
        text_only: bool = False,
        overwrite_existing: bool = False,
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Upload plusieurs PDFs dans la base existante
        
        Args:
            pdf_paths: Liste des chemins vers les PDFs
            copy_to_data: Si True, copie les PDFs dans le dossier data
            text_only: Si True, traite seulement le texte
            overwrite_existing: Si True, écrase les fichiers existants
            continue_on_error: Si True, continue même en cas d'erreur
            
        Returns:
            Dict avec résultats de l'upload
        """
        results = {
            "total_files": len(pdf_paths),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_chunks_added": 0,
            "results": [],
            "errors": []
        }
        
        try:
            for i, pdf_path in enumerate(pdf_paths, 1):
                self.logger.info(f"Traitement {i}/{len(pdf_paths)}: {os.path.basename(pdf_path)}")
                
                try:
                    result = self.upload_single_pdf(
                        pdf_path,
                        copy_to_data=copy_to_data,
                        text_only=text_only,
                        overwrite_existing=overwrite_existing
                    )
                    
                    results["results"].append(result)
                    
                    if result["success"]:
                        results["successful_uploads"] += 1
                        results["total_chunks_added"] += result.get("chunks_added", 0)
                    else:
                        results["failed_uploads"] += 1
                        if result.get("error"):
                            results["errors"].append(f"{os.path.basename(pdf_path)}: {result['error']}")
                        
                        if not continue_on_error:
                            break
                            
                except Exception as e:
                    error_msg = f"Erreur lors du traitement de {os.path.basename(pdf_path)}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["failed_uploads"] += 1
                    
                    if not continue_on_error:
                        break
            
            return results
            
        except Exception as e:
            results["errors"].append(f"Erreur générale: {e}")
            self.logger.error(f"Erreur lors de l'upload multiple: {e}")
            return results
    
    def upload_from_folder(
        self,
        folder_path: str,
        copy_to_data: bool = True,
        text_only: bool = False,
        overwrite_existing: bool = False,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        Upload tous les PDFs d'un dossier
        
        Args:
            folder_path: Chemin vers le dossier contenant les PDFs
            copy_to_data: Si True, copie les PDFs dans le dossier data
            text_only: Si True, traite seulement le texte
            overwrite_existing: Si True, écrase les fichiers existants
            recursive: Si True, cherche récursivement dans les sous-dossiers
            
        Returns:
            Dict avec résultats de l'upload
        """
        try:
            if not os.path.exists(folder_path):
                return {
                    "total_files": 0,
                    "successful_uploads": 0,
                    "failed_uploads": 0,
                    "errors": [f"Le dossier {folder_path} n'existe pas"]
                }
            
            # Trouver tous les PDFs
            pdf_files = []
            
            if recursive:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(folder_path):
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(folder_path, file))
            
            if not pdf_files:
                return {
                    "total_files": 0,
                    "successful_uploads": 0,
                    "failed_uploads": 0,
                    "errors": [f"Aucun PDF trouvé dans {folder_path}"]
                }
            
            self.logger.info(f"Trouvé {len(pdf_files)} PDFs dans {folder_path}")
            
            # Upload des PDFs
            return self.upload_multiple_pdfs(
                pdf_files,
                copy_to_data=copy_to_data,
                text_only=text_only,
                overwrite_existing=overwrite_existing,
                continue_on_error=True
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'upload depuis dossier: {e}")
            return {
                "total_files": 0,
                "successful_uploads": 0,
                "failed_uploads": 1,
                "errors": [f"Erreur: {e}"]
            }
    
    def print_upload_summary(self, results: Dict[str, Any]):
        """Affiche un résumé de l'upload"""
        print("=" * 60)
        print("         RÉSUMÉ DE L'UPLOAD")
        print("=" * 60)
        
        total = results.get("total_files", 0)
        success = results.get("successful_uploads", 0)
        failed = results.get("failed_uploads", 0)
        chunks_added = results.get("total_chunks_added", 0)
        
        print(f"\n📊 STATISTIQUES:")
        print(f"  • Total fichiers: {total}")
        print(f"  • Succès: {success} ✅")
        print(f"  • Échecs: {failed} ❌")
        print(f"  • Nouveaux chunks: {chunks_added:,}")
        
        if total > 0:
            success_rate = (success / total) * 100
            print(f"  • Taux de réussite: {success_rate:.1f}%")
        
        # Erreurs
        errors = results.get("errors", [])
        if errors:
            print(f"\n❌ ERREURS ({len(errors)}):")
            for error in errors[:5]:  # Limiter à 5 erreurs
                print(f"  • {error}")
            if len(errors) > 5:
                print(f"  ... et {len(errors) - 5} autres erreurs")
        
        print("\n" + "=" * 60)


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload de PDFs dans une base de données existante')
    parser.add_argument('source', help='Fichier PDF ou dossier contenant les PDFs')
    parser.add_argument('--data-folder', default='./Data', help='Dossier de destination des PDFs (défaut: ./Data)')
    parser.add_argument('--no-copy', action='store_true', help='Ne pas copier les PDFs dans le dossier data')
    parser.add_argument('--text-only', action='store_true', help='Traiter seulement le texte (plus rapide)')
    parser.add_argument('--overwrite', action='store_true', help='Écraser les fichiers existants')
    parser.add_argument('--recursive', action='store_true', help='Chercher récursivement dans les sous-dossiers')
    parser.add_argument('--check-status', action='store_true', help='Vérifier seulement l\'état de la base')
    
    args = parser.parse_args()
    
    manager = PDFUploadManager(data_folder=args.data_folder)
    
    if args.check_status:
        print("Vérification de l'état de la base de données...")
        status = manager.check_database_status()
        
        print("\n=== ÉTAT DE LA BASE DE DONNÉES ===")
        print(f"Base existante: {'✅' if status.get('database_exists') else '❌'}")
        print(f"Peut uploader: {'✅' if status.get('can_upload') else '❌'}")
        print(f"Total documents: {status.get('total_documents', 0):,}")
        print(f"Réglementations: {status.get('regulations_count', 0)}")
        
        if not status.get('can_upload'):
            print("\n⚠️  La base de données n'est pas accessible ou n'existe pas.")
            print("Veuillez d'abord créer une base avec le script d'ingestion.")
        
        return
    
    # Vérifier l'état de la base avant upload
    status = manager.check_database_status()
    if not status.get("can_upload"):
        print("❌ Erreur: Base de données non accessible ou inexistante")
        print("Utilisez --check-status pour plus de détails")
        return
    
    print(f"📊 Base existante: {status.get('total_documents', 0):,} documents, {status.get('regulations_count', 0)} réglementations")
    
    # Upload selon le type de source
    if os.path.isfile(args.source):
        # Upload d'un seul fichier
        print(f"Upload du fichier: {args.source}")
        result = manager.upload_single_pdf(
            args.source,
            copy_to_data=not args.no_copy,
            text_only=args.text_only,
            overwrite_existing=args.overwrite
        )
        
        if result["success"]:
            print(f"✅ Upload réussi: {result.get('chunks_added', 0)} nouveaux chunks")
        else:
            print(f"❌ Upload échoué: {result.get('error', 'Erreur inconnue')}")
    
    elif os.path.isdir(args.source):
        # Upload depuis un dossier
        print(f"Upload depuis le dossier: {args.source}")
        results = manager.upload_from_folder(
            args.source,
            copy_to_data=not args.no_copy,
            text_only=args.text_only,
            overwrite_existing=args.overwrite,
            recursive=args.recursive
        )
        
        manager.print_upload_summary(results)
    
    else:
        print(f"❌ Erreur: {args.source} n'existe pas ou n'est ni un fichier ni un dossier")


if __name__ == "__main__":
    main()