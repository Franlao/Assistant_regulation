"""
Script pour vider/nettoyer la base de données ChromaDB
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever


class DatabaseCleanupManager:
    """Gestionnaire de nettoyage de la base de données"""
    
    def __init__(self):
        """Initialize le gestionnaire de nettoyage"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur la base de données avant nettoyage
        
        Returns:
            Dict avec les informations sur les collections
        """
        info = {
            "collections": {},
            "total_documents": 0,
            "database_paths": []
        }
        
        try:
            # Information collection Text
            text_retriever = TextRetriever()
            if text_retriever.collection:
                count = text_retriever.collection.count()
                info["collections"]["text"] = {
                    "exists": True,
                    "count": count,
                    "name": text_retriever.collection.name
                }
                info["total_documents"] += count
            else:
                info["collections"]["text"] = {"exists": False, "count": 0}
                
        except Exception as e:
            self.logger.warning(f"Erreur avec collection text: {e}")
            info["collections"]["text"] = {"exists": False, "count": 0, "error": str(e)}
        
        try:
            # Information collection Images
            image_retriever = ImageRetriever()
            if image_retriever.collection:
                count = image_retriever.collection.count()
                info["collections"]["images"] = {
                    "exists": True,
                    "count": count,
                    "name": image_retriever.collection.name
                }
                info["total_documents"] += count
            else:
                info["collections"]["images"] = {"exists": False, "count": 0}
                
        except Exception as e:
            self.logger.warning(f"Erreur avec collection images: {e}")
            info["collections"]["images"] = {"exists": False, "count": 0, "error": str(e)}
        
        try:
            # Information collection Tables
            table_retriever = TableRetriever()
            if table_retriever.collection:
                count = table_retriever.collection.count()
                info["collections"]["tables"] = {
                    "exists": True,
                    "count": count,
                    "name": table_retriever.collection.name
                }
                info["total_documents"] += count
            else:
                info["collections"]["tables"] = {"exists": False, "count": 0}
                
        except Exception as e:
            self.logger.warning(f"Erreur avec collection tables: {e}")
            info["collections"]["tables"] = {"exists": False, "count": 0, "error": str(e)}
        
        # Chemins potentiels de la base de données
        potential_paths = [
            "DB/chroma_db/",
            "./chroma_db/",  # Legacy
            "./chroma_collections/",  # Legacy
            os.path.expanduser("~/chroma_db/"),  # Legacy
            "./Data/chroma_db/"  # Legacy
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                info["database_paths"].append(os.path.abspath(path))
        
        return info
    
    def clear_collection(self, collection_type: str) -> bool:
        """
        Vide une collection spécifique
        
        Args:
            collection_type: Type de collection ('text', 'images', 'tables')
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            self.logger.info(f"Nettoyage de la collection: {collection_type}")
            
            if collection_type == "text":
                retriever = TextRetriever()
            elif collection_type == "images":
                retriever = ImageRetriever()
            elif collection_type == "tables":
                retriever = TableRetriever()
            else:
                self.logger.error(f"Type de collection inconnu: {collection_type}")
                return False
            
            if not retriever.collection:
                self.logger.warning(f"Collection {collection_type} n'existe pas")
                return True
            
            # Obtenir le nombre d'éléments avant suppression
            count_before = retriever.collection.count()
            
            if count_before == 0:
                self.logger.info(f"Collection {collection_type} déjà vide")
                return True
            
            # Supprimer tous les documents
            # ChromaDB ne permet pas de supprimer directement tous les documents
            # Il faut récupérer tous les IDs puis les supprimer
            results = retriever.collection.get()
            if results.get('ids'):
                retriever.collection.delete(ids=results['ids'])
                self.logger.info(f"Supprimé {len(results['ids'])} documents de la collection {collection_type}")
            
            # Vérifier que la collection est vide
            count_after = retriever.collection.count()
            if count_after == 0:
                self.logger.info(f"Collection {collection_type} vidée avec succès")
                return True
            else:
                self.logger.warning(f"Collection {collection_type} contient encore {count_after} documents")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage de la collection {collection_type}: {e}")
            return False
    
    def clear_all_collections(self) -> Dict[str, bool]:
        """
        Vide toutes les collections
        
        Returns:
            Dict avec le résultat pour chaque collection
        """
        results = {}
        
        for collection_type in ["text", "images", "tables"]:
            results[collection_type] = self.clear_collection(collection_type)
        
        return results
    
    def delete_database_files(self, force: bool = False) -> bool:
        """
        Supprime physiquement les fichiers de la base de données
        
        Args:
            force: Si True, force la suppression sans confirmation
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            info = self.get_database_info()
            db_paths = info.get("database_paths", [])
            
            if not db_paths:
                self.logger.info("Aucun dossier de base de données trouvé")
                return True
            
            if not force:
                print(f"⚠️  ATTENTION: Cette action va supprimer définitivement:")
                for path in db_paths:
                    print(f"   📁 {path}")
                
                confirm = input("\nÊtes-vous sûr? (oui/non): ").lower().strip()
                if confirm not in ['oui', 'yes', 'y', 'o']:
                    print("Opération annulée")
                    return False
            
            # Supprimer les dossiers
            success_count = 0
            for path in db_paths:
                try:
                    if os.path.exists(path):
                        shutil.rmtree(path)
                        self.logger.info(f"Dossier supprimé: {path}")
                        success_count += 1
                    else:
                        self.logger.warning(f"Dossier déjà supprimé: {path}")
                        success_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Erreur lors de la suppression de {path}: {e}")
            
            return success_count == len(db_paths)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression des fichiers: {e}")
            return False
    
    def clean_cache_files(self) -> bool:
        """
        Nettoie les fichiers de cache (.pkl, joblib, etc.)
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            cache_patterns = [
                "./joblib_cache/",
                "./.joblib_cache/",
                "./Data/*.pkl",
                "./Data/**/*.pkl",
                "./.conversation_memory/",
                "./logs/"
            ]
            
            import glob
            files_deleted = 0
            
            for pattern in cache_patterns:
                try:
                    if pattern.endswith('/'):
                        # Dossier
                        if os.path.exists(pattern):
                            shutil.rmtree(pattern)
                            self.logger.info(f"Dossier cache supprimé: {pattern}")
                            files_deleted += 1
                    else:
                        # Fichiers avec pattern
                        files = glob.glob(pattern, recursive=True)
                        for file_path in files:
                            try:
                                os.remove(file_path)
                                self.logger.info(f"Fichier cache supprimé: {file_path}")
                                files_deleted += 1
                            except Exception as e:
                                self.logger.warning(f"Impossible de supprimer {file_path}: {e}")
                                
                except Exception as e:
                    self.logger.warning(f"Erreur avec pattern {pattern}: {e}")
            
            self.logger.info(f"Nettoyage cache terminé: {files_deleted} éléments supprimés")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage du cache: {e}")
            return False
    
    def selective_cleanup(self, regulation_codes: List[str]) -> Dict[str, Any]:
        """
        Nettoyage sélectif par codes de réglementation
        
        Args:
            regulation_codes: Liste des codes de réglementation à supprimer
            
        Returns:
            Dict avec les résultats de suppression
        """
        results = {
            "deleted_documents": 0,
            "regulations_processed": [],
            "errors": []
        }
        
        try:
            for reg_code in regulation_codes:
                try:
                    self.logger.info(f"Suppression de la réglementation: {reg_code}")
                    
                    # Générer les variantes du code
                    variants = self._generate_regulation_variants(reg_code)
                    
                    deleted_count = 0
                    
                    # Supprimer de la collection text
                    try:
                        text_retriever = TextRetriever()
                        if text_retriever.collection:
                            for variant in variants:
                                results_to_delete = text_retriever.collection.get(
                                    where={"regulation_code": variant},
                                    # IDs are returned by default, no need for include
                                )
                                
                                if results_to_delete.get('ids'):
                                    text_retriever.collection.delete(ids=results_to_delete['ids'])
                                    deleted_count += len(results_to_delete['ids'])
                                    self.logger.info(f"Supprimé {len(results_to_delete['ids'])} documents text pour {variant}")
                    
                    except Exception as e:
                        self.logger.warning(f"Erreur collection text pour {reg_code}: {e}")
                    
                    # Supprimer de la collection images
                    try:
                        image_retriever = ImageRetriever()
                        if image_retriever.collection:
                            for variant in variants:
                                results_to_delete = image_retriever.collection.get(
                                    where={"regulation_code": variant},
                                    # IDs are returned by default, no need for include
                                )
                                
                                if results_to_delete.get('ids'):
                                    image_retriever.collection.delete(ids=results_to_delete['ids'])
                                    deleted_count += len(results_to_delete['ids'])
                                    self.logger.info(f"Supprimé {len(results_to_delete['ids'])} documents images pour {variant}")
                    
                    except Exception as e:
                        self.logger.warning(f"Erreur collection images pour {reg_code}: {e}")
                    
                    # Supprimer de la collection tables
                    try:
                        table_retriever = TableRetriever()
                        if table_retriever.collection:
                            for variant in variants:
                                results_to_delete = table_retriever.collection.get(
                                    where={"regulation_code": variant},
                                    # IDs are returned by default, no need for include
                                )
                                
                                if results_to_delete.get('ids'):
                                    table_retriever.collection.delete(ids=results_to_delete['ids'])
                                    deleted_count += len(results_to_delete['ids'])
                                    self.logger.info(f"Supprimé {len(results_to_delete['ids'])} documents tables pour {variant}")
                    
                    except Exception as e:
                        self.logger.warning(f"Erreur collection tables pour {reg_code}: {e}")
                    
                    results["deleted_documents"] += deleted_count
                    results["regulations_processed"].append({
                        "code": reg_code,
                        "deleted_count": deleted_count
                    })
                    
                except Exception as e:
                    error_msg = f"Erreur lors de la suppression de {reg_code}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage sélectif: {e}")
            results["errors"].append(str(e))
            return results
    
    def _generate_regulation_variants(self, regulation_code: str) -> List[str]:
        """Génère les variantes possibles du code de réglementation"""
        import re
        
        variants = [regulation_code]
        
        number_match = re.search(r'R?(\d+)', regulation_code)
        if number_match:
            number = number_match.group(1)
            padded_number = number.zfill(3)
            
            variants.extend([
                f"R{number}",
                f"R{padded_number}",
                f"R.{padded_number}",
                f"UN R{padded_number}",
                f"ECE R{padded_number}",
                f"ECE R{number}",
                regulation_code.replace("ECE ", ""),
                regulation_code.replace("UN ", ""),
            ])
        
        return list(set(variants))  # Éliminer doublons
    
    def print_cleanup_summary(self, before_info: Dict, after_info: Dict):
        """Affiche un résumé du nettoyage"""
        print("=" * 60)
        print("         RÉSUMÉ DU NETTOYAGE")
        print("=" * 60)
        
        print("\n📊 AVANT NETTOYAGE:")
        before_total = before_info.get("total_documents", 0)
        print(f"  Total documents: {before_total:,}")
        
        for col_type, col_info in before_info.get("collections", {}).items():
            if isinstance(col_info, dict):
                count = col_info.get("count", 0)
                print(f"  {col_type.capitalize()}: {count:,}")
        
        print("\n📊 APRÈS NETTOYAGE:")
        after_total = after_info.get("total_documents", 0)
        print(f"  Total documents: {after_total:,}")
        
        for col_type, col_info in after_info.get("collections", {}).items():
            if isinstance(col_info, dict):
                count = col_info.get("count", 0)
                print(f"  {col_type.capitalize()}: {count:,}")
        
        deleted_total = before_total - after_total
        print(f"\n🗑️  DOCUMENTS SUPPRIMÉS: {deleted_total:,}")
        
        if deleted_total > 0:
            percentage = (deleted_total / before_total) * 100 if before_total > 0 else 0
            print(f"📈 POURCENTAGE NETTOYÉ: {percentage:.1f}%")
        
        print("\n" + "=" * 60)


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nettoyage de la base de données ChromaDB')
    parser.add_argument('--collection', choices=['text', 'images', 'tables'], help='Vider une collection spécifique')
    parser.add_argument('--all-collections', action='store_true', help='Vider toutes les collections')
    parser.add_argument('--delete-files', action='store_true', help='Supprimer physiquement les fichiers de la DB')
    parser.add_argument('--clean-cache', action='store_true', help='Nettoyer les fichiers de cache')
    parser.add_argument('--regulations', nargs='+', help='Suppression sélective par codes de réglementation')
    parser.add_argument('--force', action='store_true', help='Forcer la suppression sans confirmation')
    parser.add_argument('--info-only', action='store_true', help='Afficher seulement les informations sur la DB')
    
    args = parser.parse_args()
    
    manager = DatabaseCleanupManager()
    
    # Informations avant nettoyage
    before_info = manager.get_database_info()
    
    if args.info_only:
        print("=" * 60)
        print("    INFORMATIONS BASE DE DONNÉES")
        print("=" * 60)
        
        print(f"\nTotal documents: {before_info.get('total_documents', 0):,}")
        
        for col_type, col_info in before_info.get("collections", {}).items():
            if isinstance(col_info, dict):
                status = "✅" if col_info.get("exists", False) else "❌"
                count = col_info.get("count", 0)
                print(f"{status} {col_type.capitalize()}: {count:,}")
        
        db_paths = before_info.get("database_paths", [])
        if db_paths:
            print(f"\n📁 Dossiers de base de données:")
            for path in db_paths:
                print(f"  • {path}")
        
        return
    
    # Effectuer les opérations de nettoyage
    operations_performed = []
    
    if args.collection:
        print(f"Nettoyage de la collection: {args.collection}")
        success = manager.clear_collection(args.collection)
        operations_performed.append(f"Collection {args.collection}: {'✅' if success else '❌'}")
    
    if args.all_collections:
        print("Nettoyage de toutes les collections...")
        results = manager.clear_all_collections()
        for col_type, success in results.items():
            operations_performed.append(f"Collection {col_type}: {'✅' if success else '❌'}")
    
    if args.regulations:
        print(f"Suppression sélective des réglementations: {', '.join(args.regulations)}")
        results = manager.selective_cleanup(args.regulations)
        operations_performed.append(f"Documents supprimés: {results.get('deleted_documents', 0)}")
        if results.get('errors'):
            for error in results['errors']:
                print(f"Erreur: {error}")
    
    if args.clean_cache:
        print("Nettoyage des fichiers de cache...")
        success = manager.clean_cache_files()
        operations_performed.append(f"Cache nettoyé: {'✅' if success else '❌'}")
    
    if args.delete_files:
        print("Suppression des fichiers de base de données...")
        success = manager.delete_database_files(force=args.force)
        operations_performed.append(f"Fichiers supprimés: {'✅' if success else '❌'}")
    
    # Afficher le résumé si des opérations ont été effectuées
    if operations_performed:
        after_info = manager.get_database_info()
        
        print("\n" + "=" * 40)
        print("OPÉRATIONS EFFECTUÉES:")
        for op in operations_performed:
            print(f"  • {op}")
        
        manager.print_cleanup_summary(before_info, after_info)
    else:
        print("Aucune opération de nettoyage spécifiée.")
        print("Utilisez --help pour voir les options disponibles.")


if __name__ == "__main__":
    main()