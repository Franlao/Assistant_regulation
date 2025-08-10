"""
Script de résumé des informations de la base de données ChromaDB
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from collections import Counter, defaultdict

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever


class DatabaseSummaryManager:
    """Gestionnaire de résumé de la base de données"""
    
    def __init__(self):
        """Initialize le gestionnaire de résumé"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_complete_summary(self) -> Dict[str, Any]:
        """
        Génère un résumé complet de la base de données
        
        Returns:
            Dict contenant toutes les informations de résumé
        """
        try:
            summary = {
                "collections": self._get_collections_summary(),
                "documents": self._get_documents_summary(),
                "regulations": self._get_regulations_summary(),
                "statistics": self._get_general_statistics()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du résumé: {e}")
            return {}
    
    def _get_collections_summary(self) -> Dict[str, Any]:
        """Résumé des collections ChromaDB"""
        collections_info = {}
        
        # Collection Text
        try:
            text_retriever = TextRetriever()
            if text_retriever.collection:
                collections_info["text"] = {
                    "exists": True,
                    "count": text_retriever.collection.count(),
                    "name": text_retriever.collection.name
                }
            else:
                collections_info["text"] = {"exists": False, "count": 0}
        except Exception as e:
            self.logger.warning(f"Erreur avec collection text: {e}")
            collections_info["text"] = {"exists": False, "count": 0, "error": str(e)}
        
        # Collection Images
        try:
            image_retriever = ImageRetriever()
            if image_retriever.collection:
                collections_info["images"] = {
                    "exists": True,
                    "count": image_retriever.collection.count(),
                    "name": image_retriever.collection.name
                }
            else:
                collections_info["images"] = {"exists": False, "count": 0}
        except Exception as e:
            self.logger.warning(f"Erreur avec collection images: {e}")
            collections_info["images"] = {"exists": False, "count": 0, "error": str(e)}
        
        # Collection Tables
        try:
            table_retriever = TableRetriever()
            if table_retriever.collection:
                collections_info["tables"] = {
                    "exists": True,
                    "count": table_retriever.collection.count(),
                    "name": table_retriever.collection.name
                }
            else:
                collections_info["tables"] = {"exists": False, "count": 0}
        except Exception as e:
            self.logger.warning(f"Erreur avec collection tables: {e}")
            collections_info["tables"] = {"exists": False, "count": 0, "error": str(e)}
        
        return collections_info
    
    def _get_documents_summary(self) -> Dict[str, Any]:
        """Résumé des documents dans la base"""
        documents_info = {
            "unique_documents": set(),
            "documents_by_regulation": defaultdict(set),
            "total_pages": 0,
            "documents_details": []
        }
        
        # Analyser la collection text (principale)
        try:
            text_retriever = TextRetriever()
            if text_retriever.collection and text_retriever.collection.count() > 0:
                # Récupérer tous les documents avec métadonnées
                results = text_retriever.collection.get(include=['metadatas'])
                
                for metadata in results.get('metadatas', []):
                    if not metadata:
                        continue
                    
                    # Extraire les informations du document
                    doc_name = (
                        metadata.get('document_name') or 
                        metadata.get('document_id') or 
                        'Document inconnu'
                    )
                    
                    reg_code = (
                        metadata.get('regulation_code') or
                        'Code inconnu'
                    )
                    
                    page_num = metadata.get('page_number', 0)
                    
                    documents_info["unique_documents"].add(doc_name)
                    documents_info["documents_by_regulation"][reg_code].add(doc_name)
                    
                    if page_num:
                        documents_info["total_pages"] = max(
                            documents_info["total_pages"], 
                            page_num
                        )
        
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse des documents: {e}")
        
        # Convertir sets en listes pour la sérialisation JSON
        documents_info["unique_documents"] = list(documents_info["unique_documents"])
        documents_info["documents_by_regulation"] = {
            reg: list(docs) for reg, docs in documents_info["documents_by_regulation"].items()
        }
        
        return documents_info
    
    def _get_regulations_summary(self) -> Dict[str, Any]:
        """Résumé des réglementations disponibles"""
        regulations_info = {
            "total_regulations": 0,
            "regulations_list": [],
            "regulations_details": {},
            "chunks_per_regulation": {}
        }
        
        try:
            text_retriever = TextRetriever()
            if text_retriever.collection and text_retriever.collection.count() > 0:
                results = text_retriever.collection.get(include=['metadatas'])
                
                regulation_stats = defaultdict(lambda: {
                    'documents': set(),
                    'chunks_count': 0,
                    'pages': set()
                })
                
                for metadata in results.get('metadatas', []):
                    if not metadata:
                        continue
                    
                    reg_code = (
                        metadata.get('regulation_code') or
                        'Code inconnu'
                    )
                    
                    doc_name = (
                        metadata.get('document_name') or 
                        metadata.get('document_id') or 
                        'Document inconnu'
                    )
                    
                    page_num = metadata.get('page_number')
                    
                    regulation_stats[reg_code]['documents'].add(doc_name)
                    regulation_stats[reg_code]['chunks_count'] += 1
                    
                    if page_num:
                        regulation_stats[reg_code]['pages'].add(page_num)
                
                # Convertir en format final
                for reg_code, stats in regulation_stats.items():
                    regulations_info["regulations_list"].append(reg_code)
                    regulations_info["regulations_details"][reg_code] = {
                        "documents_count": len(stats['documents']),
                        "documents": list(stats['documents']),
                        "chunks_count": stats['chunks_count'],
                        "pages_count": len(stats['pages']),
                        "pages_range": f"{min(stats['pages'])}-{max(stats['pages'])}" if stats['pages'] else "N/A"
                    }
                    regulations_info["chunks_per_regulation"][reg_code] = stats['chunks_count']
                
                regulations_info["total_regulations"] = len(regulation_stats)
                regulations_info["regulations_list"].sort()
        
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse des réglementations: {e}")
        
        return regulations_info
    
    def _get_general_statistics(self) -> Dict[str, Any]:
        """Statistiques générales de la base"""
        stats = {
            "total_chunks": 0,
            "total_unique_documents": 0,
            "total_regulations": 0,
            "average_chunks_per_regulation": 0,
            "largest_regulation": None,
            "smallest_regulation": None,
            "storage_info": {}
        }
        
        try:
            # Statistiques des collections
            collections = self._get_collections_summary()
            
            stats["total_chunks"] = sum(
                col_info.get("count", 0) 
                for col_info in collections.values() 
                if isinstance(col_info, dict)
            )
            
            # Statistiques des documents et réglementations
            docs_info = self._get_documents_summary()
            regs_info = self._get_regulations_summary()
            
            stats["total_unique_documents"] = len(docs_info.get("unique_documents", []))
            stats["total_regulations"] = regs_info.get("total_regulations", 0)
            
            # Moyennes et extrêmes
            chunks_per_reg = regs_info.get("chunks_per_regulation", {})
            if chunks_per_reg:
                stats["average_chunks_per_regulation"] = sum(chunks_per_reg.values()) / len(chunks_per_reg)
                
                max_chunks = max(chunks_per_reg.values())
                min_chunks = min(chunks_per_reg.values())
                
                stats["largest_regulation"] = {
                    "code": next(reg for reg, count in chunks_per_reg.items() if count == max_chunks),
                    "chunks_count": max_chunks
                }
                
                stats["smallest_regulation"] = {
                    "code": next(reg for reg, count in chunks_per_reg.items() if count == min_chunks),
                    "chunks_count": min_chunks
                }
            
            # Informations de stockage (approximatives)
            stats["storage_info"] = {
                "estimated_size_mb": stats["total_chunks"] * 0.1,  # Estimation grossière
                "database_path": "./chroma_db/"
            }
        
        except Exception as e:
            self.logger.warning(f"Erreur lors du calcul des statistiques: {e}")
        
        return stats
    
    def print_summary(self, detailed: bool = False):
        """
        Affiche le résumé de la base de données
        
        Args:
            detailed: Si True, affiche un résumé détaillé
        """
        summary = self.get_complete_summary()
        
        print("=" * 60)
        print("         RÉSUMÉ DE LA BASE DE DONNÉES")
        print("=" * 60)
        
        # Collections
        collections = summary.get("collections", {})
        print("\n📚 COLLECTIONS:")
        for col_type, col_info in collections.items():
            if isinstance(col_info, dict):
                status = "✅" if col_info.get("exists", False) else "❌"
                count = col_info.get("count", 0)
                print(f"  {status} {col_type.upper()}: {count:,} documents")
        
        # Statistiques générales
        stats = summary.get("statistics", {})
        print(f"\n📊 STATISTIQUES GÉNÉRALES:")
        print(f"  • Total chunks: {stats.get('total_chunks', 0):,}")
        print(f"  • Documents uniques: {stats.get('total_unique_documents', 0)}")
        print(f"  • Réglementations: {stats.get('total_regulations', 0)}")
        print(f"  • Moyenne chunks/réglementation: {stats.get('average_chunks_per_regulation', 0):.1f}")
        
        # Réglementations
        regulations = summary.get("regulations", {})
        print(f"\n⚖️  RÉGLEMENTATIONS DISPONIBLES ({regulations.get('total_regulations', 0)}):")
        
        if detailed:
            regs_details = regulations.get("regulations_details", {})
            for reg_code in sorted(regulations.get("regulations_list", [])):
                details = regs_details.get(reg_code, {})
                print(f"  • {reg_code}:")
                print(f"    - Documents: {details.get('documents_count', 0)}")
                print(f"    - Chunks: {details.get('chunks_count', 0)}")
                print(f"    - Pages: {details.get('pages_range', 'N/A')}")
        else:
            regs_list = regulations.get("regulations_list", [])[:10]  # Top 10
            print(f"  {', '.join(regs_list)}")
            if len(regulations.get("regulations_list", [])) > 10:
                print(f"  ... et {len(regulations.get('regulations_list', [])) - 10} autres")
        
        # Plus grandes/petites réglementations
        if stats.get("largest_regulation"):
            largest = stats["largest_regulation"]
            print(f"\n🏆 PLUS GRANDE RÉGLEMENTATION: {largest['code']} ({largest['chunks_count']:,} chunks)")
        
        if stats.get("smallest_regulation"):
            smallest = stats["smallest_regulation"]
            print(f"📝 PLUS PETITE RÉGLEMENTATION: {smallest['code']} ({smallest['chunks_count']} chunks)")
        
        # Stockage
        storage = stats.get("storage_info", {})
        print(f"\n💾 STOCKAGE:")
        print(f"  • Taille estimée: {storage.get('estimated_size_mb', 0):.1f} MB")
        print(f"  • Chemin base: {storage.get('database_path', 'N/A')}")
        
        print("\n" + "=" * 60)
    
    def export_summary(self, output_file: str = "database_summary.json"):
        """
        Exporte le résumé vers un fichier JSON
        
        Args:
            output_file: Nom du fichier de sortie
        """
        import json
        
        try:
            summary = self.get_complete_summary()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Résumé exporté vers: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export: {e}")


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Résumé de la base de données ChromaDB')
    parser.add_argument('--detailed', action='store_true', help='Affichage détaillé')
    parser.add_argument('--export', help='Exporter le résumé vers un fichier JSON')
    parser.add_argument('--quiet', action='store_true', help='Mode silencieux (pas d\'affichage console)')
    
    args = parser.parse_args()
    
    manager = DatabaseSummaryManager()
    
    if not args.quiet:
        print("Génération du résumé de la base de données...")
        manager.print_summary(detailed=args.detailed)
    
    if args.export:
        print(f"\nExport vers: {args.export}")
        manager.export_summary(args.export)
    
    if args.quiet and not args.export:
        # Mode silencieux sans export - juste retourner les statistiques de base
        summary = manager.get_complete_summary()
        stats = summary.get("statistics", {})
        print(f"Chunks: {stats.get('total_chunks', 0)}, "
              f"Documents: {stats.get('total_unique_documents', 0)}, "
              f"Réglementations: {stats.get('total_regulations', 0)}")


if __name__ == "__main__":
    main()