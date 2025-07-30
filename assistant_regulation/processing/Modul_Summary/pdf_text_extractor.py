"""
Extracteur de texte PDF utilisant pdfplumber
Réutilise les outils déjà présents dans l'architecture
"""

import pdfplumber
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from weasyprint import HTML, CSS

class PDFTextExtractor:
    """
    Extracteur de texte PDF utilisant pdfplumber.
    Réutilise la même technologie que les autres modules de traitement.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrait tout le texte brut d'un PDF.
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Le fichier PDF {pdf_path} n'existe pas")
        
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"Le fichier {pdf_path} n'est pas un PDF")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extraction de toutes les pages
                full_text = ""
                page_count = len(pdf.pages)
                
                self.logger.info(f"Extraction du texte de {page_count} pages...")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- Page {page_num} ---\n"
                        full_text += page_text + "\n"
                
                # Extraction des métadonnées
                metadata = self._extract_metadata(pdf)
                
                # Nettoyage du texte
                cleaned_text = self._clean_text(full_text)
                
                result = {
                    "raw_text": full_text,
                    "cleaned_text": cleaned_text,
                    "page_count": page_count,
                    "metadata": metadata,
                    "file_name": pdf_path.name,
                    "file_path": str(pdf_path)
                }
                
                self.logger.info(f"Extraction terminée: {len(cleaned_text)} caractères")
                return result
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction PDF: {e}")
            raise
    
    def _extract_metadata(self, pdf) -> Dict[str, Any]:
        """Extrait les métadonnées du PDF"""
        try:
            metadata = pdf.metadata or {}
            return {
                "title": metadata.get("Title", ""),
                "author": metadata.get("Author", ""),
                "subject": metadata.get("Subject", ""),
                "creator": metadata.get("Creator", ""),
                "producer": metadata.get("Producer", ""),
                "creation_date": str(metadata.get("CreationDate", "")),
                "modification_date": str(metadata.get("ModDate", ""))
            }
        except Exception as e:
            self.logger.warning(f"Impossible d'extraire les métadonnées: {e}")
            return {}
    
    def _clean_text(self, text: str) -> str:
        """
        Nettoie le texte extrait.
        Réutilise la logique similaire à celle des autres modules de traitement.
        """
        if not text:
            return ""
        
        # Suppression des caractères de contrôle
        cleaned = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        # Normalisation des espaces
        lines = cleaned.split('\n')
        normalized_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Ignorer les lignes vides
                normalized_lines.append(line)
        
        # Rejoindre avec des espaces simples pour les paragraphes
        result = '\n'.join(normalized_lines)
        
        # Suppression des espaces multiples
        import re
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def get_regulation_number(self, text: str) -> Optional[str]:
        """
        Tente d'extraire le numéro de règlement du texte.
        Utilise des patterns typiques des réglementations.
        """
        import re
        
        # Patterns courants pour les réglementations
        patterns = [
            r'R(\d+)',  # R107, R108, etc.
            r'Règlement\s+(\d+)',
            r'REGULATION\s+(\d+)',
            r'R-(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"R{match.group(1)}"
        
        return None 
