#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de Résumé Intelligent - Résumé proportionnel et hiérarchique de réglementations complètes
Utilise l'approche Map-Reduce pour traiter de longs documents de manière intelligente.
"""

import os
import json
import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import ollama
from mistralai import Mistral, UserMessage

# Configuration du logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

@dataclass
class SummaryConfig:
    """Configuration du résumé"""
    regulation_code: str
    target_pages: int
    words_per_page: int = 500  # Estimation mots par page
    chunks_per_section: int = 30  # Nombre de chunks par section (limite LLM)
    min_summary_ratio: float = 0.10  # 10% minimum du document original
    max_summary_ratio: float = 0.20  # 20% maximum du document original

@dataclass
class SummaryResult:
    """Résultat du résumé"""
    regulation_code: str
    original_pages: int
    summary_length: int
    summary_ratio: float
    sections_count: int
    summary_text: str
    sections_summaries: List[Dict]
    processing_time: float
    metadata: Dict[str, Any]

class IntelligentSummaryService:
    """
    Service de résumé intelligent avec approche Map-Reduce hiérarchique.
    Génère des résumés proportionnels à la taille des documents.
    """
    
    def __init__(self, llm_provider: str = "mistral", model_name: str = "mistral-medium", max_workers: int = 4):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.mistral_client = None
        self.max_workers = max_workers
        self._lock = threading.Lock()  # Pour la sécurité thread
        
        if llm_provider == "mistral":
            try:
                import os
                api_key = os.getenv("MISTRAL_API_KEY")
                if api_key:
                    self.mistral_client = Mistral(api_key=api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Mistral: {e}")
                self.llm_provider = "ollama"
    
    def calculate_target_length(self, total_pages: int, total_chunks: int) -> Tuple[int, float]:
        """
        Calcule la longueur cible du résumé basée sur la taille du document.
        
        Args:
            total_pages: Nombre total de pages
            total_chunks: Nombre total de chunks
            
        Returns:
            Tuple (pages_cible, ratio)
        """
        if total_pages <= 15:
            # Documents courts : 1 page de résumé
            target_pages = 1
        elif total_pages <= 30:
            # Documents moyens : 2 pages
            target_pages = 2
        elif total_pages <= 60:
            # Documents longs : 3-4 pages
            target_pages = max(3, total_pages // 15)
        elif total_pages <= 100:
            # Documents très longs : 5-7 pages
            target_pages = max(5, total_pages // 16)
        else:
            # Documents massifs : 8-12 pages max
            target_pages = min(12, max(8, total_pages // 18))
        
        ratio = target_pages / total_pages
        
        # Limites de sécurité
        ratio = max(0.05, min(0.25, ratio))  # Entre 5% et 25%
        target_pages = max(1, min(15, target_pages))  # Entre 1 et 15 pages
        
        return target_pages, ratio
    
    def group_chunks_by_sections(self, chunks: List[Dict], chunks_per_section: int = 12) -> List[List[Dict]]:
        """
        Groupe les chunks en sections logiques pour le traitement Map-Reduce.
        
        Args:
            chunks: Liste des chunks à grouper
            chunks_per_section: Nombre maximum de chunks par section
            
        Returns:
            Liste de sections (groupes de chunks)
        """
        sections = []
        current_section = []
        current_page = None
        
        for chunk in chunks:
            page_no = chunk.get('page_no', 0)
            
            # Nouvelle section si :
            # 1. Trop de chunks dans la section actuelle
            # 2. Changement de chapitre/section important (gap de pages > 5)
            if (len(current_section) >= chunks_per_section or 
                (current_page is not None and page_no > current_page + 5)):
                
                if current_section:
                    sections.append(current_section)
                    current_section = []
            
            current_section.append(chunk)
            current_page = page_no
        
        # Ajouter la dernière section
        if current_section:
            sections.append(current_section)
        
        # Éviter les sections trop petites - fusionner si nécessaire
        if len(sections) > 1 and len(sections[-1]) < 3:
            sections[-2].extend(sections[-1])
            sections.pop()
        
        return sections
    
    def create_section_summary_prompt(self, chunks: List[Dict], regulation_code: str, section_num: int, target_words: int) -> str:
        """Crée le prompt pour résumer une section"""
        
        # Combiner le contenu des chunks
        section_content = "\n\n".join([
            f"[Page {chunk.get('page_no', '?')}] {chunk.get('documents', '')}"
            for chunk in chunks
        ])
        
        pages_range = f"{chunks[0].get('page_no', '?')}-{chunks[-1].get('page_no', '?')}"
        
        return f"""Tu es un expert en réglementations automobiles UN/ECE. Ta mission est de créer un résumé professionnel et structuré d'une section de la réglementation {regulation_code}.

SECTION À RÉSUMER:
Réglementation: {regulation_code}
Section: {section_num}
Pages: {pages_range}
Nombre de chunks: {len(chunks)}

CONTENU:
{section_content}

INSTRUCTIONS:
1. Résume cette section en {target_words} mots maximum
2. Préserve TOUS les points techniques importants
3. Conserve les valeurs numériques, dimensions, exigences précises
4. Structure le résumé avec des sous-titres clairs
5. Utilise un ton professionnel et technique
6. Mentionne les références aux annexes/articles si présentes

STRUCTURE ATTENDUE:
- Titre de section
- Points principaux avec puces
- Exigences techniques précises
- Références réglementaires

RÉSUMÉ DE SECTION:"""

    def create_final_summary_prompt(self, sections_summaries: List[str], config: SummaryConfig) -> str:
        """Crée le prompt pour le résumé final"""
        
        combined_sections = "\n\n=== SECTION SUIVANTE ===\n\n".join(sections_summaries)
        target_words = config.target_pages * config.words_per_page
        
        return f"""Tu es un expert en réglementations automobiles UN/ECE. Ta mission est de créer un résumé COMPLET et PROFESSIONNEL de la réglementation {config.regulation_code}.

RÉSUMÉS DE SECTIONS À CONSOLIDER:
{combined_sections}

INSTRUCTIONS POUR LE RÉSUMÉ FINAL:
1. Longueur cible: {target_words} mots ({config.target_pages} pages)
2. Créer un document professionnel et structuré
3. Préserver TOUTES les informations techniques importantes
4. Organiser par thèmes logiques (sécurité, construction, tests, etc.)
5. Inclure un sommaire exécutif en début
6. Conserver les valeurs numériques et exigences précises
7. Mentionner les procédures de test importantes
8. Ton professionnel adapté aux experts automobiles

STRUCTURE ATTENDUE:
# RÉSUMÉ EXÉCUTIF - RÉGLEMENTATION {config.regulation_code}

## 1. SOMMAIRE EXÉCUTIF
[Vue d'ensemble en 2-3 paragraphes]

## 2. DOMAINE D'APPLICATION
[Véhicules concernés, champ d'application]

## 3. EXIGENCES PRINCIPALES
### 3.1 Exigences de Construction
### 3.2 Exigences de Performance  
### 3.3 Exigences de Sécurité

## 4. PROCÉDURES DE TEST
[Tests requis, conditions d'homologation]

## 5. DISPOSITIONS SPÉCIALES
[PMR, cas particuliers, exemptions]

## 6. POINTS CLÉS À RETENIR
[Liste des points essentiels]

RÉSUMÉ COMPLET:"""

    def call_llm_for_summary(self, prompt: str, max_tokens: int = 1500, thread_safe: bool = True) -> str:
        """Appelle le LLM pour générer un résumé (thread-safe)"""
        try:
            if self.llm_provider == "mistral" and self.mistral_client:
                # Mistral API est thread-safe
                messages = [UserMessage(content=prompt)]
                response = self.mistral_client.chat.complete(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            else:
                # Ollama avec protection thread si nécessaire
                if thread_safe:
                    with self._lock:
                        response = ollama.chat(
                            model=self.model_name,
                            messages=[{"role": "user", "content": prompt}],
                            options={
                                "temperature": 0.1,
                                "num_predict": max_tokens
                            }
                        )
                else:
                    response = ollama.chat(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        options={
                            "temperature": 0.1,
                            "num_predict": max_tokens
                        }
                    )
                return response['message']['content'].strip()
                
        except Exception as e:
            logger.error(f"Erreur lors de l'appel LLM: {e}")
            return f"Erreur lors de la génération du résumé: {e}"
    
    def summarize_section(self, chunks: List[Dict], regulation_code: str, section_num: int, target_words: int) -> Dict:
        """
        Résume une section de chunks (étape MAP).
        
        Args:
            chunks: Chunks de la section
            regulation_code: Code de la réglementation
            section_num: Numéro de la section
            target_words: Nombre de mots cible
            
        Returns:
            Dict avec le résumé de section
        """
        start_time = datetime.now()
        
        # Créer le prompt
        prompt = self.create_section_summary_prompt(chunks, regulation_code, section_num, target_words)
        
        # Générer le résumé
        summary_text = self.call_llm_for_summary(prompt, max_tokens=target_words * 2)
        
        # Métadonnées
        pages_covered = sorted(list(set(chunk.get('page_no', 0) for chunk in chunks)))
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'section_num': section_num,
            'summary': summary_text,
            'chunks_count': len(chunks),
            'pages_covered': pages_covered,
            'target_words': target_words,
            'actual_words': len(summary_text.split()),
            'processing_time': processing_time
        }
    
    def _summarize_section_worker(self, args: Tuple) -> Dict:
        """Worker function pour le traitement parallèle des sections"""
        section_chunks, regulation_code, section_num, target_words = args
        return self.summarize_section(section_chunks, regulation_code, section_num, target_words)
    
    def summarize_sections_parallel(self, sections: List[List[Dict]], regulation_code: str, target_words_per_section: int) -> List[Dict]:
        """
        Traite les sections en parallèle pour accélérer le processus.
        
        Args:
            sections: Liste des sections (groupes de chunks)
            regulation_code: Code de la réglementation
            target_words_per_section: Nombre de mots cible par section
            
        Returns:
            Liste des résumés de sections
        """
        start_time = time.time()
        
        # Préparer les arguments pour chaque worker
        worker_args = [
            (section_chunks, regulation_code, i + 1, target_words_per_section)
            for i, section_chunks in enumerate(sections)
        ]
        
        sections_summaries = []
        completed_count = 0
        
        # Traitement parallèle avec ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre tous les jobs
            future_to_section = {
                executor.submit(self._summarize_section_worker, args): args[2]  # args[2] = section_num
                for args in worker_args
            }
            
            # Récupérer les résultats au fur et à mesure
            for future in as_completed(future_to_section):
                section_num = future_to_section[future]
                try:
                    result = future.result()
                    sections_summaries.append(result)
                    completed_count += 1
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Section {section_num} terminée ({completed_count}/{len(sections)}) - {elapsed:.1f}s")
                    
                except Exception as e:
                    logger.error(f"Erreur section {section_num}: {e}")
                    # Créer un résumé de fallback
                    sections_summaries.append({
                        'section_num': section_num,
                        'summary': f"Erreur lors du résumé de la section {section_num}: {e}",
                        'chunks_count': 0,
                        'pages_covered': [],
                        'target_words': target_words_per_section,
                        'actual_words': 0,
                        'processing_time': 0
                    })
        
        # Trier les résultats par numéro de section
        sections_summaries.sort(key=lambda x: x['section_num'])
        
        total_time = time.time() - start_time
        logger.info(f"Traitement parallèle terminé: {len(sections)} sections en {total_time:.1f}s")
        
        return sections_summaries
    
    def _optimize_workers_count(self, sections_count: int) -> int:
        """Optimise le nombre de workers selon le nombre de sections"""
        if sections_count <= 2:
            return 1  # Pas besoin de parallélisation pour peu de sections
        elif sections_count <= 4:
            return 2  # 2 workers pour les petits documents
        elif sections_count <= 8:
            return min(3, self.max_workers)  # 3 workers max pour les documents moyens
        else:
            return self.max_workers  # Tous les workers pour les gros documents
    
    def generate_regulation_summary(self, regulation_code: str) -> SummaryResult:
        """
        Génère un résumé complet d'une réglementation avec approche Map-Reduce.
        
        Args:
            regulation_code: Code de la réglementation (ex: 'R107')
            
        Returns:
            SummaryResult avec le résumé complet
        """
        start_time = datetime.now()
        
        try:
            # Importer le retriever
            from assistant_regulation.processing.Modul_emb.TextRetriever import TextRetriever
            
            # Récupérer tous les chunks de la réglementation
            retriever = TextRetriever()
            all_chunks = retriever.get_all_chunks_for_regulation(regulation_code)
            
            if not all_chunks:
                raise ValueError(f"Aucun chunk trouvé pour la réglementation {regulation_code}")
            
            # Statistiques du document
            total_chunks = len(all_chunks)
            pages_covered = sorted(list(set(chunk.get('page_no', 0) for chunk in all_chunks)))
            total_pages = len(pages_covered)
            
            logger.info(f"Traitement de {regulation_code}: {total_chunks} chunks, {total_pages} pages")
            
            # Calculer la configuration du résumé
            target_pages, ratio = self.calculate_target_length(total_pages, total_chunks)
            config = SummaryConfig(
                regulation_code=regulation_code,
                target_pages=target_pages
            )
            
            # ÉTAPE MAP: Grouper et résumer par sections EN PARALLÈLE
            sections = self.group_chunks_by_sections(all_chunks, chunks_per_section=18)
            target_words_per_section = (config.target_pages * config.words_per_page) // len(sections)
            
            logger.info(f"Division en {len(sections)} sections, {target_words_per_section} mots par section")
            
            # Optimiser le nombre de workers
            optimal_workers = self._optimize_workers_count(len(sections))
            original_workers = self.max_workers
            self.max_workers = optimal_workers
            
            logger.info(f"Traitement parallèle avec {optimal_workers} workers")
            
            # Utiliser le traitement parallèle
            sections_summaries = self.summarize_sections_parallel(
                sections, regulation_code, target_words_per_section
            )
            
            # Restaurer le nombre de workers original
            self.max_workers = original_workers
            
            # ÉTAPE REDUCE: Créer le résumé final
            logger.info("Création du résumé final...")
            section_texts = [s['summary'] for s in sections_summaries]
            final_prompt = self.create_final_summary_prompt(section_texts, config)
            
            final_summary = self.call_llm_for_summary(
                final_prompt, 
                max_tokens=config.target_pages * config.words_per_page * 2
            )
            
            # Résultat final
            processing_time = (datetime.now() - start_time).total_seconds()
            actual_words = len(final_summary.split())
            actual_ratio = actual_words / (total_chunks * 100)  # Approximation
            
            result = SummaryResult(
                regulation_code=regulation_code,
                original_pages=total_pages,
                summary_length=actual_words,
                summary_ratio=actual_ratio,
                sections_count=len(sections),
                summary_text=final_summary,
                sections_summaries=sections_summaries,
                processing_time=processing_time,
                metadata={
                    'total_chunks': total_chunks,
                    'target_pages': target_pages,
                    'target_words': config.target_pages * config.words_per_page,
                    'llm_provider': self.llm_provider,
                    'model': self.model_name,
                    'pages_covered': pages_covered
                }
            )
            
            logger.info(f"Résumé terminé: {actual_words} mots, {processing_time:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {e}")
            raise e
    
    def export_summary_to_file(self, result: SummaryResult, output_path: str, format: str = "markdown") -> str:
        """
        Exporte le résumé vers un fichier.
        
        Args:
            result: Résultat du résumé
            output_path: Chemin de sortie
            format: Format d'export (markdown, txt, json)
            
        Returns:
            Chemin du fichier créé
        """
        try:
            if format.lower() == "markdown":
                filename = f"{result.regulation_code}_resume_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
                filepath = os.path.join(output_path, filename)
                
                content = f"""# Résumé Professionnel - Réglementation {result.regulation_code}

**Généré le:** {datetime.now().strftime('%d/%m/%Y à %H:%M')}  
**Document original:** {result.original_pages} pages  
**Résumé:** {result.summary_length} mots ({result.sections_count} sections)  
**Ratio de compression:** {result.summary_ratio:.1%}  

---

{result.summary_text}

---

## Métadonnées Techniques

- **Chunks analysés:** {result.metadata.get('total_chunks', 'N/A')}
- **Pages couvertes:** {len(result.metadata.get('pages_covered', []))} pages
- **Modèle utilisé:** {result.metadata.get('llm_provider', 'N/A')} ({result.metadata.get('model', 'N/A')})
- **Temps de traitement:** {result.processing_time:.1f} secondes

### Détails des Sections
"""
                
                for section in result.sections_summaries:
                    content += f"""
**Section {section['section_num']}**  
- Pages: {'-'.join(map(str, section['pages_covered']))}  
- Chunks: {section['chunks_count']}  
- Mots générés: {section['actual_words']}/{section['target_words']}  
"""
                
                os.makedirs(output_path, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return filepath
                
            elif format.lower() == "json":
                filename = f"{result.regulation_code}_resume_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
                filepath = os.path.join(output_path, filename)
                
                # Convertir en dict sérialisable
                data = {
                    'regulation_code': result.regulation_code,
                    'original_pages': result.original_pages,
                    'summary_length': result.summary_length,
                    'summary_ratio': result.summary_ratio,
                    'sections_count': result.sections_count,
                    'summary_text': result.summary_text,
                    'sections_summaries': result.sections_summaries,
                    'processing_time': result.processing_time,
                    'metadata': result.metadata,
                    'generated_at': datetime.now().isoformat()
                }
                
                os.makedirs(output_path, exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return filepath
            
            else:
                raise ValueError(f"Format non supporté: {format}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            raise e
    
    def export_summary_to_pdf(self, result: SummaryResult, output_path: str, filename: str = None) -> str:
        """
        Exporte le résumé vers PDF via LaTeX (nouveau).
        
        Args:
            result: Résultat du résumé
            output_path: Chemin de sortie
            filename: Nom du fichier (optionnel)
            
        Returns:
            Chemin du fichier PDF créé
        """
        try:
            from .pdf_export_service import PDFExportService
            
            pdf_service = PDFExportService()
            return pdf_service.export_summary_to_pdf(result, output_path, filename)
            
        except ImportError as e:
            logger.error(f"Service PDF non disponible: {e}")
            raise e
        except Exception as e:
            logger.error(f"Erreur lors de l'export PDF: {e}")
            raise e

# Fonction utilitaire pour tests
def test_summary_service():
    """Teste le service de résumé"""
    service = IntelligentSummaryService(llm_provider="mistral", model_name="mistral-medium",max_workers=5)
    
    print("Test du service de résumé intelligent...")
    
    # Tester avec R107
    try:
        result = service.generate_regulation_summary("R107")
        print(f"Résumé généré: {result.summary_length} mots")
        print(f"Ratio: {result.summary_ratio:.1%}")
        print(f"Temps: {result.processing_time:.1f}s")
        print(f"Sections: {result.sections_count}")
        
        # Exporter
        output_path = "./summaries"
        file_path = service.export_summary_to_file(result, output_path, "markdown")
        print(f"Exporté vers: {file_path}")
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    test_summary_service()