"""
Service de gestion des citations et références dans les réponses
"""
import re
from typing import List, Dict, Tuple, Optional


class CitationService:
    """Service pour gérer les citations Vancouver et les références dans les réponses"""
    
    def __init__(self):
        self.citation_patterns = [
            # Patterns pour détecter les mentions de réglementations
            r'(?:regulation|réglementation|règlement)\s+([rR]\d+)',
            r'\b([rR]\d+)\b(?:\s+regulation)?',
            # Patterns pour détecter les mentions de documents
            r'(?:document|directive|norme)\s+([A-Z]\d+)',
            # Patterns pour détecter les références à des sections
            r'(?:section|article|paragraphe)\s+(\d+(?:\.\d+)*)',
        ]
    
    def add_vancouver_citations(self, response_text: str, sources: List[Dict]) -> str:
        """
        Ajoute des citations Vancouver dans le texte de réponse
        
        Args:
            response_text: Texte de la réponse originale
            sources: Liste des sources utilisées
            
        Returns:
            Texte avec citations intégrées + liste des références
        """
        if not sources:
            return response_text
        
        # Créer un mapping des sources
        citation_map = self._create_citation_map(sources)
        
        # Insérer les citations dans le texte
        modified_text = self._insert_citations(response_text, sources, citation_map)
        
        # Ajouter la liste des références
        modified_text = self._append_references(modified_text, citation_map)
        
        return modified_text
    
    def _create_citation_map(self, sources: List[Dict]) -> Dict[int, Dict]:
        """Crée un mapping des sources pour les citations"""
        citation_map = {}
        
        for i, source in enumerate(sources, 1):
            regulation_code = source.get('regulation_code', '')
            document_name = source.get('document_name', 'Document inconnu')
            pages = source.get('pages', [])
            source_link = source.get('source_link', '')
            
            # Format Vancouver pour réglementations automobiles
            if regulation_code and regulation_code.upper() != 'CODE INCONNU':
                # Format: "UN/ECE Regulation No. R046. Mirror systems. Series 06."
                if pages:
                    citation_text = f"UN/ECE Regulation No. {regulation_code}. {self._clean_document_title(document_name)}. p.{pages[0]}."
                else:
                    citation_text = f"UN/ECE Regulation No. {regulation_code}. {self._clean_document_title(document_name)}."
            else:
                # Format générique pour autres documents
                if pages:
                    citation_text = f"{self._clean_document_title(document_name)}. p.{pages[0]}."
                else:
                    citation_text = f"{self._clean_document_title(document_name)}."
            
            citation_map[i] = {
                'number': i,
                'text': citation_text,
                'source': source,
                'regulation_code': regulation_code,
                'source_link': source_link
            }
        
        return citation_map
    
    def _clean_document_title(self, title: str) -> str:
        """Nettoie le titre du document pour la citation"""
        # Enlever les extensions de fichier
        title = re.sub(r'\.(pdf|doc|docx)$', '', title, flags=re.IGNORECASE)
        
        # Nettoyer les patterns de série (ex: "- 06 series")
        title = re.sub(r'\s*-\s*\d+\s*series?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*\d+\s*suppl?\s*\d*', '', title, flags=re.IGNORECASE)
        
        # Nettoyer les codes de réglementation répétés au début
        title = re.sub(r'^[rR]\d+\s*-\s*', '', title)
        
        return title.strip()
    
    def _insert_citations(self, text: str, sources: List[Dict], citation_map: Dict[int, Dict]) -> str:
        """Insère les citations dans le texte"""
        modified_text = text
        
        # 1. Citer les réglementations spécifiques mentionnées
        for i, citation_info in citation_map.items():
            regulation_code = citation_info['regulation_code']
            source_link = citation_info['source_link']
            
            if regulation_code and regulation_code.upper() != 'CODE INCONNU':
                # Patterns pour trouver les mentions de la réglementation
                patterns = [
                    rf'\\b({re.escape(regulation_code)})\\b(?!\\s*\\[\\d+\\])',  # R046 (pas déjà cité)
                    rf'\\b(regulation\\s+{re.escape(regulation_code)})\\b(?!\\s*\\[\\d+\\])',  # regulation R046
                    rf'\\b(réglementation\\s+{re.escape(regulation_code)})\\b(?!\\s*\\[\\d+\\])',  # réglementation R046
                ]
                
                for pattern in patterns:
                    if source_link:
                        replacement = rf'\1 <a href="{source_link}" style="color: #0a6ebd; text-decoration: none;" onclick="window.open(this.href); return false;">[{i}]</a>'
                    else:
                        replacement = rf'\1 [{i}]'
                    
                    modified_text = re.sub(pattern, replacement, modified_text, count=1, flags=re.IGNORECASE)
        
        # 2. Ajouter des citations aux affirmations importantes
        # (logique plus sophistiquée peut être ajoutée ici)
        
        return modified_text
    
    def _append_references(self, text: str, citation_map: Dict[int, Dict]) -> str:
        """Ajoute la liste des références à la fin du texte"""
        if not citation_map:
            return text
        
        references_section = "\n\n---\n\n**Références :**\n\n"
        
        for i, citation_info in citation_map.items():
            source_link = citation_info['source_link']
            citation_text = citation_info['text']
            
            if source_link:
                references_section += f'{i}. <a href="{source_link}" style="color: #0a6ebd; text-decoration: none;" onclick="window.open(this.href); return false;">{citation_text}</a>\n\n'
            else:
                references_section += f"{i}. {citation_text}\n\n"
        
        return text + references_section
    
    def extract_regulation_mentions(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Extrait les mentions de réglementations du texte
        
        Returns:
            Liste de tuples (mention, start_pos, end_pos)
        """
        mentions = []
        
        for pattern in self.citation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                mentions.append((match.group(), match.start(), match.end()))
        
        return mentions
    
    def generate_citation_preview(self, sources: List[Dict]) -> str:
        """
        Génère un aperçu des citations qui seraient générées
        
        Args:
            sources: Liste des sources
            
        Returns:
            Aperçu des citations formatées
        """
        if not sources:
            return "Aucune source disponible pour les citations."
        
        citation_map = self._create_citation_map(sources)
        
        preview = "**Aperçu des citations :**\\n\\n"
        for i, citation_info in citation_map.items():
            preview += f"[{i}] {citation_info['text']}\\n"
        
        return preview
    
    def validate_sources_for_citations(self, sources: List[Dict]) -> Dict[str, any]:
        """
        Valide les sources pour la génération de citations
        
        Returns:
            Dictionnaire avec les statistiques de validation
        """
        stats = {
            'total_sources': len(sources),
            'sources_with_regulation': 0,
            'sources_with_pages': 0,
            'sources_with_links': 0,
            'valid_for_vancouver': 0,
            'issues': []
        }
        
        for source in sources:
            regulation_code = source.get('regulation_code', '')
            pages = source.get('pages', [])
            source_link = source.get('source_link', '')
            document_name = source.get('document_name', '')
            
            if regulation_code and regulation_code.upper() != 'CODE INCONNU':
                stats['sources_with_regulation'] += 1
            
            if pages:
                stats['sources_with_pages'] += 1
            
            if source_link:
                stats['sources_with_links'] += 1
            
            # Validation pour format Vancouver
            is_valid = True
            if not document_name or document_name == 'Document inconnu':
                stats['issues'].append(f"Source sans nom de document valide")
                is_valid = False
            
            if is_valid:
                stats['valid_for_vancouver'] += 1
        
        return stats


# Instance globale du service
citation_service = CitationService()