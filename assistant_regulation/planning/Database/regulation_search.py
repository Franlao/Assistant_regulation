"""
Script de recherche spécifique par code de réglementation
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import re

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever


class RegulationSearchManager:
    """Gestionnaire de recherche par réglementation"""
    
    def __init__(self):
        """Initialize le gestionnaire de recherche"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialiser les retrievers
        try:
            self.text_retriever = TextRetriever()
            self.image_retriever = ImageRetriever()
            self.table_retriever = TableRetriever()
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des retrievers: {e}")
            raise
    
    def search_regulation_complete(self, regulation_code: str) -> Dict[str, Any]:
        """
        Récupère toutes les informations d'une réglementation
        
        Args:
            regulation_code: Code de la réglementation (ex: R046, ECE R46)
            
        Returns:
            Dict contenant tous les chunks, métadonnées et statistiques
        """
        try:
            # Normaliser et générer les variantes du code
            regulation_variants = self._generate_regulation_variants(regulation_code)
            
            result = {
                "regulation_code": regulation_code,
                "variants_tried": regulation_variants,
                "found_variant": None,
                "text_chunks": [],
                "image_chunks": [],
                "table_chunks": [],
                "documents": [],
                "statistics": {
                    "total_chunks": 0,
                    "text_chunks_count": 0,
                    "image_chunks_count": 0,
                    "table_chunks_count": 0,
                    "documents_count": 0,
                    "pages_count": 0
                },
                "content_analysis": {
                    "requirements_count": 0,
                    "definitions_count": 0,
                    "procedures_count": 0,
                    "references_count": 0
                }
            }
            
            # Rechercher dans les chunks de texte
            text_results = self._search_text_by_regulation(regulation_variants)
            if text_results:
                result["text_chunks"] = text_results["chunks"]
                result["found_variant"] = text_results["variant"]
                result["statistics"]["text_chunks_count"] = len(text_results["chunks"])
                
                # Analyser le contenu
                self._analyze_content(result)
                
            # Rechercher dans les images (si disponible)
            try:
                image_results = self._search_images_by_regulation(regulation_variants)
                if image_results:
                    result["image_chunks"] = image_results["chunks"]
                    result["statistics"]["image_chunks_count"] = len(image_results["chunks"])
            except Exception as e:
                self.logger.warning(f"Collection images non disponible: {e}")
            
            # Rechercher dans les tables (si disponible)
            try:
                table_results = self._search_tables_by_regulation(regulation_variants)
                if table_results:
                    result["table_chunks"] = table_results["chunks"]
                    result["statistics"]["table_chunks_count"] = len(table_results["chunks"])
            except Exception as e:
                self.logger.warning(f"Collection tables non disponible: {e}")
            
            # Calculer les statistiques finales
            self._calculate_final_statistics(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche de {regulation_code}: {e}")
            return {}
    
    def _generate_regulation_variants(self, regulation_code: str) -> List[str]:
        """Génère les variantes possibles du code de réglementation"""
        variants = [regulation_code]
        
        # Extraire le numéro
        number_match = re.search(r'R?(\d+)', regulation_code)
        if number_match:
            number = number_match.group(1)
            padded_number = number.zfill(3)  # "46" -> "046"
            
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
        
        # Éliminer les doublons tout en préservant l'ordre
        unique_variants = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        
        return unique_variants
    
    def _search_text_by_regulation(self, regulation_variants: List[str]) -> Optional[Dict]:
        """Recherche dans les chunks de texte"""
        try:
            if not self.text_retriever.collection:
                return None
            
            for variant in regulation_variants:
                # Recherche par metadata
                results = self.text_retriever.collection.get(
                    where={"regulation_code": variant},
                    include=['metadatas', 'documents']
                )
                
                if results and results.get('ids'):
                    chunks = []
                    for i, chunk_id in enumerate(results['ids']):
                        chunk = {
                            'id': chunk_id,
                            'content': results['documents'][i] if i < len(results['documents']) else '',
                            'metadata': results['metadatas'][i] if i < len(results['metadatas']) else {}
                        }
                        chunks.append(chunk)
                    
                    self.logger.info(f"Trouvé {len(chunks)} chunks avec variant '{variant}'")
                    return {"chunks": chunks, "variant": variant}
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche text: {e}")
            return None
    
    def _search_images_by_regulation(self, regulation_variants: List[str]) -> Optional[Dict]:
        """Recherche dans les chunks d'images"""
        try:
            if not self.image_retriever.collection:
                return None
            
            for variant in regulation_variants:
                results = self.image_retriever.collection.get(
                    where={"regulation_code": variant},
                    include=['metadatas', 'documents']
                )
                
                if results and results.get('ids'):
                    chunks = []
                    for i, chunk_id in enumerate(results['ids']):
                        chunk = {
                            'id': chunk_id,
                            'content': results['documents'][i] if i < len(results['documents']) else '',
                            'metadata': results['metadatas'][i] if i < len(results['metadatas']) else {}
                        }
                        chunks.append(chunk)
                    
                    return {"chunks": chunks, "variant": variant}
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la recherche images: {e}")
            return None
    
    def _search_tables_by_regulation(self, regulation_variants: List[str]) -> Optional[Dict]:
        """Recherche dans les chunks de tables"""
        try:
            if not self.table_retriever.collection:
                return None
            
            for variant in regulation_variants:
                results = self.table_retriever.collection.get(
                    where={"regulation_code": variant},
                    include=['metadatas', 'documents']
                )
                
                if results and results.get('ids'):
                    chunks = []
                    for i, chunk_id in enumerate(results['ids']):
                        chunk = {
                            'id': chunk_id,
                            'content': results['documents'][i] if i < len(results['documents']) else '',
                            'metadata': results['metadatas'][i] if i < len(results['metadatas']) else {}
                        }
                        chunks.append(chunk)
                    
                    return {"chunks": chunks, "variant": variant}
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la recherche tables: {e}")
            return None
    
    def _analyze_content(self, result: Dict):
        """Analyse le contenu des chunks pour extraire des statistiques"""
        try:
            documents = set()
            pages = set()
            
            # Analyser les chunks de texte
            for chunk in result.get("text_chunks", []):
                metadata = chunk.get("metadata", {})
                content = chunk.get("content", "").lower()
                
                # Documents
                doc_name = (
                    metadata.get('document_name') or 
                    metadata.get('document_id') or 
                    'Document inconnu'
                )
                documents.add(doc_name)
                
                # Pages
                page_num = metadata.get('page_number')
                if page_num:
                    pages.add(page_num)
                
                # Analyse du contenu
                if any(word in content for word in ['doit', 'shall', 'requirement', 'exigence']):
                    result["content_analysis"]["requirements_count"] += 1
                
                if any(word in content for word in ['définition', 'definition', 'signifie', 'means']):
                    result["content_analysis"]["definitions_count"] += 1
                
                if any(word in content for word in ['procédure', 'procedure', 'méthode', 'method']):
                    result["content_analysis"]["procedures_count"] += 1
                
                if any(word in content for word in ['voir', 'see', 'référence', 'reference', 'annexe']):
                    result["content_analysis"]["references_count"] += 1
            
            result["documents"] = list(documents)
            result["statistics"]["documents_count"] = len(documents)
            result["statistics"]["pages_count"] = len(pages)
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'analyse du contenu: {e}")
    
    def _calculate_final_statistics(self, result: Dict):
        """Calcule les statistiques finales"""
        stats = result["statistics"]
        stats["total_chunks"] = (
            stats["text_chunks_count"] + 
            stats["image_chunks_count"] + 
            stats["table_chunks_count"]
        )
    
    def search_regulation_summary(self, regulation_code: str) -> Dict[str, Any]:
        """
        Retourne un résumé rapide d'une réglementation
        
        Args:
            regulation_code: Code de la réglementation
            
        Returns:
            Dict avec résumé
        """
        try:
            result = self.search_regulation_complete(regulation_code)
            
            return {
                "regulation_code": regulation_code,
                "found": bool(result.get("text_chunks")),
                "variant_used": result.get("found_variant"),
                "total_chunks": result.get("statistics", {}).get("total_chunks", 0),
                "documents": result.get("documents", []),
                "documents_count": len(result.get("documents", [])),
                "pages_count": result.get("statistics", {}).get("pages_count", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Erreur lors du résumé de {regulation_code}: {e}")
            return {"regulation_code": regulation_code, "found": False, "error": str(e)}
    
    def print_regulation_info(self, regulation_code: str, detailed: bool = False):
        """
        Affiche les informations d'une réglementation
        
        Args:
            regulation_code: Code de la réglementation
            detailed: Si True, affichage détaillé
        """
        if detailed:
            result = self.search_regulation_complete(regulation_code)
        else:
            result = self.search_regulation_summary(regulation_code)
        
        print("=" * 60)
        print(f"    RÉGLEMENTATION: {regulation_code}")
        print("=" * 60)
        
        if not result.get("found", False):
            print("❌ Réglementation non trouvée dans la base de données")
            if result.get("error"):
                print(f"   Erreur: {result['error']}")
            return
        
        print("✅ Réglementation trouvée")
        
        if result.get("variant_used"):
            print(f"📝 Variant utilisé: {result['variant_used']}")
        
        # Statistiques de base
        if detailed:
            stats = result.get("statistics", {})
            print(f"\n📊 STATISTIQUES:")
            print(f"  • Total chunks: {stats.get('total_chunks', 0)}")
            print(f"  • Chunks texte: {stats.get('text_chunks_count', 0)}")
            print(f"  • Chunks images: {stats.get('image_chunks_count', 0)}")
            print(f"  • Chunks tables: {stats.get('table_chunks_count', 0)}")
            print(f"  • Documents: {stats.get('documents_count', 0)}")
            print(f"  • Pages: {stats.get('pages_count', 0)}")
            
            # Analyse du contenu
            content_analysis = result.get("content_analysis", {})
            print(f"\n📋 ANALYSE DU CONTENU:")
            print(f"  • Exigences: {content_analysis.get('requirements_count', 0)}")
            print(f"  • Définitions: {content_analysis.get('definitions_count', 0)}")
            print(f"  • Procédures: {content_analysis.get('procedures_count', 0)}")
            print(f"  • Références: {content_analysis.get('references_count', 0)}")
        else:
            print(f"📊 Chunks: {result.get('total_chunks', 0)}")
            print(f"📄 Documents: {result.get('documents_count', 0)}")
            print(f"📖 Pages: {result.get('pages_count', 0)}")
        
        # Documents
        documents = result.get("documents", [])
        if documents:
            print(f"\n📚 DOCUMENTS ({len(documents)}):")
            for doc in documents[:5]:  # Limiter à 5
                print(f"  • {doc}")
            if len(documents) > 5:
                print(f"  ... et {len(documents) - 5} autres")
        
        print("\n" + "=" * 60)
    
    def export_regulation_data(
        self, 
        regulation_code: str, 
        output_file: str, 
        format_type: str = "json"
    ):
        """
        Exporte les données d'une réglementation
        
        Args:
            regulation_code: Code de la réglementation
            output_file: Fichier de sortie
            format_type: Format d'export (json, txt, csv)
        """
        try:
            result = self.search_regulation_complete(regulation_code)
            
            if format_type.lower() == "json":
                import json
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                    
            elif format_type.lower() == "txt":
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"RÉGLEMENTATION: {regulation_code}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for chunk in result.get("text_chunks", []):
                        f.write(f"CHUNK ID: {chunk.get('id', 'N/A')}\n")
                        f.write(f"CONTENU:\n{chunk.get('content', '')}\n")
                        f.write("-" * 40 + "\n\n")
                        
            elif format_type.lower() == "csv":
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['chunk_id', 'content', 'document', 'page', 'regulation'])
                    
                    for chunk in result.get("text_chunks", []):
                        metadata = chunk.get("metadata", {})
                        writer.writerow([
                            chunk.get('id', ''),
                            chunk.get('content', '')[:500] + '...' if len(chunk.get('content', '')) > 500 else chunk.get('content', ''),
                            metadata.get('document_name', ''),
                            metadata.get('page_number', ''),
                            metadata.get('regulation_code', '')
                        ])
            
            self.logger.info(f"Données de {regulation_code} exportées vers: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'export: {e}")


def main():
    """Point d'entrée du script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Recherche spécifique par code de réglementation')
    parser.add_argument('regulation_code', help='Code de la réglementation (ex: R046, ECE R46)')
    parser.add_argument('--detailed', action='store_true', help='Affichage détaillé')
    parser.add_argument('--export', help='Exporter les données vers un fichier')
    parser.add_argument('--format', choices=['json', 'txt', 'csv'], default='json', help='Format d\'export')
    parser.add_argument('--summary-only', action='store_true', help='Afficher seulement le résumé')
    
    args = parser.parse_args()
    
    manager = RegulationSearchManager()
    
    print(f"Recherche de la réglementation: {args.regulation_code}")
    
    if args.summary_only:
        summary = manager.search_regulation_summary(args.regulation_code)
        print(f"Trouvée: {summary.get('found', False)}")
        if summary.get('found'):
            print(f"Chunks: {summary.get('total_chunks', 0)}")
            print(f"Documents: {summary.get('documents_count', 0)}")
    else:
        manager.print_regulation_info(args.regulation_code, detailed=args.detailed)
    
    if args.export:
        print(f"\nExport vers: {args.export}")
        manager.export_regulation_data(
            args.regulation_code, 
            args.export, 
            args.format
        )


if __name__ == "__main__":
    main()