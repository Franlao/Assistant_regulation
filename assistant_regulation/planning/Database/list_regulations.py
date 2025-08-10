"""
Script pour lister toutes les réglementations disponibles dans la base de données
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from collections import Counter, defaultdict

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever


class RegulationListManager:
    """Gestionnaire de listage des réglementations"""
    
    def __init__(self):
        """Initialize le gestionnaire de listage"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialiser les retrievers
        try:
            self.text_retriever = TextRetriever()
            self.image_retriever = None
            self.table_retriever = None
            
            try:
                self.image_retriever = ImageRetriever()
            except Exception as e:
                self.logger.warning(f"Collection images non disponible: {e}")
            
            try:
                self.table_retriever = TableRetriever()
            except Exception as e:
                self.logger.warning(f"Collection tables non disponible: {e}")
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des retrievers: {e}")
            raise
    
    def get_all_regulations(self) -> Dict[str, Any]:
        """
        Récupère la liste complète de toutes les réglementations
        
        Returns:
            Dict contenant les réglementations et leurs statistiques
        """
        try:
            regulations_data = {
                "regulations_list": [],
                "regulations_details": {},
                "statistics": {
                    "total_regulations": 0,
                    "total_documents": 0,
                    "total_chunks": 0,
                    "average_chunks_per_regulation": 0,
                    "largest_regulation": None,
                    "smallest_regulation": None
                },
                "content_breakdown": {
                    "text_chunks": 0,
                    "image_chunks": 0,
                    "table_chunks": 0
                }
            }
            
            # Analyser la collection text (principale)
            if self.text_retriever.collection and self.text_retriever.collection.count() > 0:
                self._analyze_text_collection(regulations_data)
            
            # Analyser la collection images
            if self.image_retriever and self.image_retriever.collection and self.image_retriever.collection.count() > 0:
                self._analyze_image_collection(regulations_data)
            
            # Analyser la collection tables
            if self.table_retriever and self.table_retriever.collection and self.table_retriever.collection.count() > 0:
                self._analyze_table_collection(regulations_data)
            
            # Calculer les statistiques finales
            self._calculate_final_statistics(regulations_data)
            
            return regulations_data
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des réglementations: {e}")
            return {}
    
    def _analyze_text_collection(self, regulations_data: Dict):
        """Analyse la collection de texte"""
        try:
            results = self.text_retriever.collection.get(include=['metadatas'])
            
            regulation_stats = defaultdict(lambda: {
                'documents': set(),
                'text_chunks': 0,
                'image_chunks': 0,
                'table_chunks': 0,
                'pages': set(),
                'content_analysis': {
                    'has_requirements': 0,
                    'has_definitions': 0,
                    'has_procedures': 0,
                    'has_references': 0
                }
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
                
                # Statistiques de base
                regulation_stats[reg_code]['documents'].add(doc_name)
                regulation_stats[reg_code]['text_chunks'] += 1
                
                if page_num:
                    regulation_stats[reg_code]['pages'].add(page_num)
                
                # Analyse du contenu Late Chunker si disponible
                if metadata.get('chunk_type') == 'late_chunker':
                    if metadata.get('has_requirement'):
                        regulation_stats[reg_code]['content_analysis']['has_requirements'] += 1
                    if metadata.get('has_definition'):
                        regulation_stats[reg_code]['content_analysis']['has_definitions'] += 1
                    if metadata.get('has_procedure'):
                        regulation_stats[reg_code]['content_analysis']['has_procedures'] += 1
                    if metadata.get('has_reference'):
                        regulation_stats[reg_code]['content_analysis']['has_references'] += 1
            
            # Convertir en format final
            for reg_code, stats in regulation_stats.items():
                regulations_data["regulations_list"].append(reg_code)
                
                total_chunks = stats['text_chunks'] + stats['image_chunks'] + stats['table_chunks']
                
                regulations_data["regulations_details"][reg_code] = {
                    "documents": list(stats['documents']),
                    "documents_count": len(stats['documents']),
                    "chunks": {
                        "text": stats['text_chunks'],
                        "images": stats['image_chunks'],
                        "tables": stats['table_chunks'],
                        "total": total_chunks
                    },
                    "pages": {
                        "count": len(stats['pages']),
                        "range": f"{min(stats['pages'])}-{max(stats['pages'])}" if stats['pages'] else "N/A",
                        "list": sorted(list(stats['pages']))
                    },
                    "content_analysis": stats['content_analysis']
                }
            
            regulations_data["content_breakdown"]["text_chunks"] = sum(
                details["chunks"]["text"] 
                for details in regulations_data["regulations_details"].values()
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de la collection text: {e}")
    
    def _analyze_image_collection(self, regulations_data: Dict):
        """Analyse la collection d'images"""
        try:
            results = self.image_retriever.collection.get(include=['metadatas'])
            
            for metadata in results.get('metadatas', []):
                if not metadata:
                    continue
                
                reg_code = metadata.get('regulation_code', 'Code inconnu')
                
                # Ajouter à la liste si pas déjà présent
                if reg_code not in regulations_data["regulations_list"]:
                    regulations_data["regulations_list"].append(reg_code)
                    regulations_data["regulations_details"][reg_code] = {
                        "documents": [],
                        "documents_count": 0,
                        "chunks": {"text": 0, "images": 0, "tables": 0, "total": 0},
                        "pages": {"count": 0, "range": "N/A", "list": []},
                        "content_analysis": {
                            'has_requirements': 0,
                            'has_definitions': 0,
                            'has_procedures': 0,
                            'has_references': 0
                        }
                    }
                
                # Incrémenter le compteur d'images
                regulations_data["regulations_details"][reg_code]["chunks"]["images"] += 1
                regulations_data["regulations_details"][reg_code]["chunks"]["total"] += 1
            
            regulations_data["content_breakdown"]["image_chunks"] = sum(
                details["chunks"]["images"] 
                for details in regulations_data["regulations_details"].values()
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de la collection images: {e}")
    
    def _analyze_table_collection(self, regulations_data: Dict):
        """Analyse la collection de tables"""
        try:
            results = self.table_retriever.collection.get(include=['metadatas'])
            
            for metadata in results.get('metadatas', []):
                if not metadata:
                    continue
                
                reg_code = metadata.get('regulation_code', 'Code inconnu')
                
                # Ajouter à la liste si pas déjà présent
                if reg_code not in regulations_data["regulations_list"]:
                    regulations_data["regulations_list"].append(reg_code)
                    regulations_data["regulations_details"][reg_code] = {
                        "documents": [],
                        "documents_count": 0,
                        "chunks": {"text": 0, "images": 0, "tables": 0, "total": 0},
                        "pages": {"count": 0, "range": "N/A", "list": []},
                        "content_analysis": {
                            'has_requirements': 0,
                            'has_definitions': 0,
                            'has_procedures': 0,
                            'has_references': 0
                        }
                    }
                
                # Incrémenter le compteur de tables
                regulations_data["regulations_details"][reg_code]["chunks"]["tables"] += 1
                regulations_data["regulations_details"][reg_code]["chunks"]["total"] += 1
            
            regulations_data["content_breakdown"]["table_chunks"] = sum(
                details["chunks"]["tables"] 
                for details in regulations_data["regulations_details"].values()
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de la collection tables: {e}")
    
    def _calculate_final_statistics(self, regulations_data: Dict):
        """Calcule les statistiques finales"""
        try:
            details = regulations_data["regulations_details"]
            
            # Trier la liste des réglementations
            regulations_data["regulations_list"].sort()
            
            # Statistiques générales
            regulations_data["statistics"]["total_regulations"] = len(details)
            
            if details:
                # Total des documents uniques
                all_documents = set()
                total_chunks = 0
                chunks_per_regulation = {}
                
                for reg_code, reg_details in details.items():
                    all_documents.update(reg_details.get("documents", []))
                    reg_chunks = reg_details["chunks"]["total"]
                    total_chunks += reg_chunks
                    chunks_per_regulation[reg_code] = reg_chunks
                
                regulations_data["statistics"]["total_documents"] = len(all_documents)
                regulations_data["statistics"]["total_chunks"] = total_chunks
                
                # Moyenne
                if len(details) > 0:
                    regulations_data["statistics"]["average_chunks_per_regulation"] = total_chunks / len(details)
                
                # Plus grande et plus petite réglementation
                if chunks_per_regulation:
                    max_chunks = max(chunks_per_regulation.values())
                    min_chunks = min(chunks_per_regulation.values())
                    
                    regulations_data["statistics"]["largest_regulation"] = {
                        "code": next(reg for reg, count in chunks_per_regulation.items() if count == max_chunks),
                        "chunks_count": max_chunks
                    }
                    
                    regulations_data["statistics"]["smallest_regulation"] = {
                        "code": next(reg for reg, count in chunks_per_regulation.items() if count == min_chunks),
                        "chunks_count": min_chunks
                    }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des statistiques: {e}")
    
    def get_regulations_by_criteria(
        self, 
        min_chunks: Optional[int] = None,
        max_chunks: Optional[int] = None,
        has_images: Optional[bool] = None,
        has_tables: Optional[bool] = None,
        contains_text: Optional[str] = None
    ) -> List[str]:
        """
        Filtre les réglementations selon des critères
        
        Args:
            min_chunks: Nombre minimum de chunks
            max_chunks: Nombre maximum de chunks
            has_images: Si True, seulement les réglementations avec images
            has_tables: Si True, seulement les réglementations avec tables
            contains_text: Filtre par texte dans le nom de réglementation
            
        Returns:
            Liste des codes de réglementation qui correspondent aux critères
        """
        try:
            all_data = self.get_all_regulations()
            filtered_regulations = []
            
            for reg_code, details in all_data.get("regulations_details", {}).items():
                # Filtrer par nombre de chunks
                total_chunks = details["chunks"]["total"]
                
                if min_chunks is not None and total_chunks < min_chunks:
                    continue
                
                if max_chunks is not None and total_chunks > max_chunks:
                    continue
                
                # Filtrer par images
                if has_images is not None:
                    has_img = details["chunks"]["images"] > 0
                    if has_images != has_img:
                        continue
                
                # Filtrer par tables
                if has_tables is not None:
                    has_tbl = details["chunks"]["tables"] > 0
                    if has_tables != has_tbl:
                        continue
                
                # Filtrer par texte
                if contains_text is not None:
                    if contains_text.lower() not in reg_code.lower():
                        continue
                
                filtered_regulations.append(reg_code)
            
            return sorted(filtered_regulations)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du filtrage: {e}")
            return []
    
    def print_regulations_list(self, detailed: bool = False, limit: Optional[int] = None):
        """
        Affiche la liste des réglementations
        
        Args:
            detailed: Si True, affichage détaillé
            limit: Nombre maximum de réglementations à afficher
        """
        try:
            data = self.get_all_regulations()
            
            print("=" * 70)
            print("         LISTE DES RÉGLEMENTATIONS DISPONIBLES")
            print("=" * 70)
            
            # Statistiques générales
            stats = data.get("statistics", {})
            print(f"\n📊 RÉSUMÉ GÉNÉRAL:")
            print(f"  • Total réglementations: {stats.get('total_regulations', 0)}")
            print(f"  • Total documents uniques: {stats.get('total_documents', 0)}")
            print(f"  • Total chunks: {stats.get('total_chunks', 0):,}")
            print(f"  • Moyenne chunks/réglementation: {stats.get('average_chunks_per_regulation', 0):.1f}")
            
            # Répartition par type de contenu
            breakdown = data.get("content_breakdown", {})
            print(f"\n📋 RÉPARTITION DU CONTENU:")
            print(f"  • Chunks texte: {breakdown.get('text_chunks', 0):,}")
            print(f"  • Chunks images: {breakdown.get('image_chunks', 0):,}")
            print(f"  • Chunks tables: {breakdown.get('table_chunks', 0):,}")
            
            # Liste des réglementations
            regulations_list = data.get("regulations_list", [])
            details = data.get("regulations_details", {})
            
            if limit:
                regulations_list = regulations_list[:limit]
            
            if detailed:
                print(f"\n⚖️ RÉGLEMENTATIONS DÉTAILLÉES ({len(regulations_list)}):")
                print("-" * 70)
                
                for i, reg_code in enumerate(regulations_list, 1):
                    reg_details = details.get(reg_code, {})
                    chunks = reg_details.get("chunks", {})
                    pages = reg_details.get("pages", {})
                    content_analysis = reg_details.get("content_analysis", {})
                    
                    print(f"\n{i:2d}. {reg_code}")
                    print(f"    📄 Documents: {reg_details.get('documents_count', 0)}")
                    print(f"    📊 Chunks: {chunks.get('total', 0)} "
                          f"(T:{chunks.get('text', 0)}, I:{chunks.get('images', 0)}, Tb:{chunks.get('tables', 0)})")
                    print(f"    📖 Pages: {pages.get('count', 0)} ({pages.get('range', 'N/A')})")
                    
                    if any(content_analysis.values()):
                        print(f"    🔍 Contenu: "
                              f"Req:{content_analysis.get('has_requirements', 0)}, "
                              f"Def:{content_analysis.get('has_definitions', 0)}, "
                              f"Proc:{content_analysis.get('has_procedures', 0)}, "
                              f"Ref:{content_analysis.get('has_references', 0)}")
                    
                    # Lister les documents
                    documents = reg_details.get("documents", [])
                    if documents:
                        print(f"    📚 Docs: {', '.join(documents[:2])}")
                        if len(documents) > 2:
                            print(f"         ... et {len(documents) - 2} autres")
            else:
                print(f"\n⚖️ RÉGLEMENTATIONS ({len(regulations_list)}):")
                
                # Affichage en colonnes
                cols = 4
                for i in range(0, len(regulations_list), cols):
                    row = regulations_list[i:i+cols]
                    formatted_row = []
                    
                    for reg_code in row:
                        reg_details = details.get(reg_code, {})
                        chunks_total = reg_details.get("chunks", {}).get("total", 0)
                        formatted_row.append(f"{reg_code} ({chunks_total})")
                    
                    print(f"  {' | '.join(formatted_row)}")
            
            # Top réglementations
            if stats.get("largest_regulation"):
                largest = stats["largest_regulation"]
                print(f"\n🏆 PLUS GRANDE: {largest['code']} ({largest['chunks_count']:,} chunks)")
            
            if stats.get("smallest_regulation"):
                smallest = stats["smallest_regulation"]
                print(f"📝 PLUS PETITE: {smallest['code']} ({smallest['chunks_count']} chunks)")
            
            if limit and len(data.get("regulations_list", [])) > limit:
                print(f"\n... et {len(data.get('regulations_list', [])) - limit} autres réglementations")
            
            print("\n" + "=" * 70)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'affichage: {e}")
            print("Erreur lors de l'affichage de la liste des réglementations")
    
    def export_regulations_list(
        self, 
        output_file: str, 
        format_type: str = "json",
        include_details: bool = True
    ):
        """
        Exporte la liste des réglementations
        
        Args:
            output_file: Fichier de sortie
            format_type: Format d'export (json, csv, txt)
            include_details: Inclure les détails ou juste la liste
        """
        try:
            data = self.get_all_regulations()
            
            if format_type.lower() == "json":
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data if include_details else data.get("regulations_list", []), 
                             f, indent=2, ensure_ascii=False)
                             
            elif format_type.lower() == "csv":
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    if include_details:
                        writer = csv.writer(f)
                        writer.writerow([
                            'regulation_code', 'documents_count', 'total_chunks', 
                            'text_chunks', 'image_chunks', 'table_chunks', 'pages_count'
                        ])
                        
                        for reg_code, details in data.get("regulations_details", {}).items():
                            chunks = details.get("chunks", {})
                            writer.writerow([
                                reg_code,
                                details.get("documents_count", 0),
                                chunks.get("total", 0),
                                chunks.get("text", 0),
                                chunks.get("images", 0),
                                chunks.get("tables", 0),
                                details.get("pages", {}).get("count", 0)
                            ])
                    else:
                        writer = csv.writer(f)
                        writer.writerow(['regulation_code'])
                        for reg_code in data.get("regulations_list", []):
                            writer.writerow([reg_code])
                            
            elif format_type.lower() == "txt":
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("LISTE DES RÉGLEMENTATIONS\n")
                    f.write("=" * 50 + "\n\n")
                    
                    if include_details:
                        for reg_code, details in data.get("regulations_details", {}).items():
                            chunks = details.get("chunks", {})
                            f.write(f"{reg_code}:\n")
                            f.write(f"  Documents: {details.get('documents_count', 0)}\n")
                            f.write(f"  Chunks: {chunks.get('total', 0)} "
                                   f"(T:{chunks.get('text', 0)}, I:{chunks.get('images', 0)}, Tb:{chunks.get('tables', 0)})\n")
                            f.write(f"  Pages: {details.get('pages', {}).get('count', 0)}\n\n")
                    else:
                        for reg_code in data.get("regulations_list", []):
                            f.write(f"{reg_code}\n")
            
            self.logger.info(f"Liste des réglementations exportée vers: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export: {e}")


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lister les réglementations de la base de données')
    parser.add_argument('--detailed', action='store_true', help='Affichage détaillé')
    parser.add_argument('--limit', type=int, help='Limiter le nombre de réglementations affichées')
    parser.add_argument('--export', help='Exporter la liste vers un fichier')
    parser.add_argument('--format', choices=['json', 'csv', 'txt'], default='json', help='Format d\'export')
    parser.add_argument('--summary-only', action='store_true', help='Exporter seulement la liste des codes')
    parser.add_argument('--min-chunks', type=int, help='Filtrer par nombre minimum de chunks')
    parser.add_argument('--max-chunks', type=int, help='Filtrer par nombre maximum de chunks')
    parser.add_argument('--with-images', action='store_true', help='Seulement les réglementations avec images')
    parser.add_argument('--with-tables', action='store_true', help='Seulement les réglementations avec tables')
    parser.add_argument('--contains', help='Filtrer par texte dans le nom de réglementation')
    
    args = parser.parse_args()
    
    manager = RegulationListManager()
    
    # Appliquer les filtres si spécifiés
    if any([args.min_chunks, args.max_chunks, args.with_images, args.with_tables, args.contains]):
        print("Application des filtres...")
        filtered_regulations = manager.get_regulations_by_criteria(
            min_chunks=args.min_chunks,
            max_chunks=args.max_chunks,
            has_images=args.with_images,
            has_tables=args.with_tables,
            contains_text=args.contains
        )
        
        print(f"Réglementations filtrées ({len(filtered_regulations)}):")
        for reg_code in filtered_regulations:
            print(f"  • {reg_code}")
    else:
        # Affichage normal
        manager.print_regulations_list(detailed=args.detailed, limit=args.limit)
    
    # Export si demandé
    if args.export:
        print(f"\nExport vers: {args.export}")
        manager.export_regulations_list(
            args.export, 
            format_type=args.format,
            include_details=not args.summary_only
        )


if __name__ == "__main__":
    main()