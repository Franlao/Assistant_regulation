#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service d'Export PDF - Convertit les résumés JSON en PDF professionnel via LaTeX
Utilise Pandoc et LaTeX pour générer des documents de qualité publication.
"""

import os
import re
import json
import logging
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

try:
    import latexrestricted
    LATEXRESTRICTED_AVAILABLE = True
except ImportError:
    LATEXRESTRICTED_AVAILABLE = False
    logging.warning("latexrestricted non disponible, utilisation de subprocess standard")

# Configuration du logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class PDFExportService:
    """
    Service d'export PDF pour les résumés de réglementations.
    Convertit JSON → LaTeX → PDF avec template professionnel.
    """
    
    def __init__(self, template_dir: str = None):
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "templates"
        )
        self.template_path = os.path.join(self.template_dir, "regulation_summary_template.tex")
        
        # Vérifier la disponibilité des outils
        self._check_dependencies()
    
    def _run_latex_command(self, cmd_args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Exécute une commande LaTeX en utilisant latexrestricted si disponible,
        sinon utilise subprocess standard.
        """
        if LATEXRESTRICTED_AVAILABLE:
            try:
                # Adapter les paramètres pour latexrestricted.restricted_run
                restricted_kwargs = kwargs.copy()
                
                # latexrestricted utilise stdout/stderr au lieu de capture_output
                if 'capture_output' in restricted_kwargs:
                    if restricted_kwargs.pop('capture_output'):
                        restricted_kwargs['stdout'] = subprocess.PIPE
                        restricted_kwargs['stderr'] = subprocess.PIPE
                
                result = latexrestricted.restricted_run(cmd_args, **restricted_kwargs)
                logger.info("Commande LaTeX exécutée avec latexrestricted")
                return result
            except Exception as e:
                logger.warning(f"Échec avec latexrestricted: {e}, utilisation de subprocess standard")
                
        # Fallback vers subprocess standard
        return subprocess.run(cmd_args, **kwargs)
    
    def _check_dependencies(self):
        """Vérifie que Pandoc et LaTeX sont installés"""
        try:
            # Vérifier Pandoc
            self._run_latex_command(['pandoc', '--version'], capture_output=True, check=True)
            logger.info("Pandoc disponible")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Pandoc non trouvé. Installation requise pour l'export PDF")
        
        try:
            # Vérifier pdflatex
            self._run_latex_command(['pdflatex', '--version'], capture_output=True, check=True)
            logger.info("pdflatex disponible")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("pdflatex non trouvé. Installation LaTeX requise pour l'export PDF")
    
    def _escape_latex(self, text: str) -> str:
        """Échappe les caractères spéciaux LaTeX"""
        if not isinstance(text, str):
            text = str(text)
        
        # Caractères spéciaux LaTeX à échapper
        latex_special_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '^': r'\textasciicircum{}',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '\\': r'\textbackslash{}',
        }
        
        for char, replacement in latex_special_chars.items():
            text = text.replace(char, replacement)
        
        return text
    
    def _format_latex_text(self, text: str) -> str:
        """Formate le texte pour LaTeX avec mise en forme avancée"""
        text = self._escape_latex(text)
        
        # Remplacer les marqueurs Markdown par LaTeX
        # Gras **text** → \textbf{text}
        text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
        
        # Italique *text* → \textit{text}
        text = re.sub(r'\*(.*?)\*', r'\\textit{\1}', text)
        
        # Code `text` → \texttt{text}
        text = re.sub(r'`(.*?)`', r'\\texttt{\1}', text)
        
        # Liens [text](url) → \href{url}{text}
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\\href{\2}{\1}', text)
        
        return text
    
    def _convert_markdown_to_latex(self, markdown_text: str) -> str:
        """Convertit le contenu Markdown en LaTeX"""
        lines = markdown_text.split('\n')
        latex_lines = []
        in_list = False
        in_table = False
        list_depth = 0
        max_list_depth = 4  # Limite LaTeX pour éviter "too deeply nested"
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Ligne vide - fermer les listes ouvertes
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                latex_lines.append('')
                continue
            
            # Titres
            if line.startswith('# '):
                # Fermer les environnements avant un nouveau titre
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                title = self._format_latex_text(line[2:])
                latex_lines.append(f'\\regsection{{{title}}}')
            elif line.startswith('## '):
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                title = self._format_latex_text(line[3:])
                latex_lines.append(f'\\regsubsection{{{title}}}')
            elif line.startswith('### '):
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                title = self._format_latex_text(line[4:])
                latex_lines.append(f'\\subsubsection{{{title}}}')
            
            # Listes avec gestion de la profondeur
            elif line.startswith('- '):
                if not in_list and list_depth < max_list_depth:
                    latex_lines.append('\\begin{itemize}')
                    in_list = True
                    list_depth = 1
                elif in_list and list_depth < max_list_depth:
                    # Continuer la liste existante
                    pass
                else:
                    # Trop profond - convertir en paragraphe avec puce
                    item = self._format_latex_text(line)
                    latex_lines.append(f'{item}\\\\[0.2cm]')
                    continue
                
                item = self._format_latex_text(line[2:])
                latex_lines.append(f'\\item {item}')
            
            # Tableaux (détection simplifiée) 
            elif '|' in line and '---' not in line and len(line.split('|')) > 2:
                # Fermer les listes avant un tableau
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                
                if not in_table:
                    # Détecter le nombre de colonnes
                    cols = len([c for c in line.split('|') if c.strip()])
                    col_format = '|' + 'l|' * cols
                    latex_lines.append('\\begin{regtable}')
                    latex_lines.append(f'\\begin{{tabular}}{{{col_format}}}')
                    latex_lines.append('\\hline')
                    in_table = True
                
                # Convertir ligne de tableau
                cells = [self._format_latex_text(cell.strip()) for cell in line.split('|') if cell.strip()]
                if cells:  # S'assurer qu'il y a des cellules
                    latex_lines.append(' & '.join(cells) + ' \\\\')
                    latex_lines.append('\\hline')
            
            # Paragraphe normal
            else:
                # Fermer les environnements ouverts pour un nouveau paragraphe
                if in_list:
                    latex_lines.append('\\end{itemize}')
                    in_list = False
                    list_depth = 0
                
                if in_table:
                    latex_lines.extend(['\\end{tabular}', '\\end{regtable}'])
                    in_table = False
                
                if line:
                    formatted_line = self._format_latex_text(line)
                    latex_lines.append(formatted_line + '\\\\[0.3cm]')
        
        # Fermer les environnements ouverts à la fin
        if in_list:
            latex_lines.append('\\end{itemize}')
        
        if in_table:
            latex_lines.extend(['\\end{tabular}', '\\end{regtable}'])
        
        return '\n'.join(latex_lines)
    
    def _format_sections_details_table(self, sections_summaries: List[Dict]) -> str:
        """Génère le tableau des détails des sections en LaTeX"""
        table_rows = []
        
        for section in sections_summaries:
            section_num = section.get('section_num', '?')
            pages = section.get('pages_covered', [])
            pages_str = '-'.join(map(str, pages[:5]))  # Limiter l'affichage
            if len(pages) > 5:
                pages_str += f"... (+{len(pages)-5})"
            
            chunks = section.get('chunks_count', 0)
            words = section.get('actual_words', 0)
            target = section.get('target_words', 0)
            processing_time = section.get('processing_time', 0)
            
            table_rows.append(
                f"{section_num} & {pages_str} & {chunks} & {words}/{target} & {processing_time:.1f} \\\\"
            )
        
        return '\n'.join(table_rows)
    
    def export_summary_to_pdf(self, summary_result, output_path: str, filename: str = None) -> str:
        """
        Exporte un résumé vers PDF via LaTeX.
        
        Args:
            summary_result: SummaryResult ou dict JSON
            output_path: Dossier de sortie
            filename: Nom du fichier (optionnel)
            
        Returns:
            Chemin du fichier PDF généré
        """
        try:
            # Convertir en dict si nécessaire
            if hasattr(summary_result, '__dict__'):
                data = asdict(summary_result)
            elif isinstance(summary_result, dict):
                data = summary_result
            else:
                raise ValueError("Format de résumé non supporté")
            
            # Nom du fichier
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                filename = f"{data['regulation_code']}_resume_{timestamp}.pdf"
            
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # Chemins de sortie
            os.makedirs(output_path, exist_ok=True)
            pdf_path = os.path.join(output_path, filename)
            
            # Lire le template LaTeX
            if not os.path.exists(self.template_path):
                raise FileNotFoundError(f"Template LaTeX non trouvé : {self.template_path}")
            
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Préparer les données pour le template
            template_data = {
                'regulation_code': data.get('regulation_code', 'RXX'),
                'original_pages': data.get('original_pages', 0),
                'summary_words': data.get('summary_length', 0),
                'sections_count': data.get('sections_count', 0),
                'compression_ratio': f"{data.get('summary_ratio', 0):.1%}",
                'generated_date': datetime.now().strftime('%d/%m/%Y à %H:%M'),
                'processing_time': f"{data.get('processing_time', 0):.1f}",
                'llm_provider': data.get('metadata', {}).get('llm_provider', 'N/A'),
                'model_name': data.get('metadata', {}).get('model', 'N/A'),
                'total_chunks': data.get('metadata', {}).get('total_chunks', 0),
                'max_workers': '4',  # Par défaut
                'pages_covered': len(data.get('metadata', {}).get('pages_covered', [])),
            }
            
            # Convertir le contenu principal
            summary_text = data.get('summary_text', '')
            main_content = self._convert_markdown_to_latex(summary_text)
            template_data['main_content'] = main_content
            
            # Générer le tableau des détails des sections
            sections_summaries = data.get('sections_summaries', [])
            sections_details = self._format_sections_details_table(sections_summaries)
            template_data['sections_details'] = sections_details
            
            # Remplacer les variables dans le template
            latex_content = template
            for key, value in template_data.items():
                placeholder = '{{' + key + '}}'
                latex_content = latex_content.replace(placeholder, str(value))
            
            # Créer un fichier temporaire pour LaTeX
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as temp_tex:
                temp_tex.write(latex_content)
                temp_tex_path = temp_tex.name
            
            try:
                # Compiler avec pdflatex (2 passes pour les références)
                temp_dir = os.path.dirname(temp_tex_path)
                base_name = os.path.splitext(os.path.basename(temp_tex_path))[0]
                
                for i in range(2):  # 2 passes pour table des matières et références
                    # Set environment to avoid elevated privileges issue
                    env = os.environ.copy()
                    env['TEXMFHOME'] = temp_dir
                    env['TEXMFCACHE'] = temp_dir
                    
                    # Utiliser latexrestricted si disponible
                    result = self._run_latex_command([
                        'pdflatex',
                        '-interaction=nonstopmode',
                        '-output-directory', temp_dir,
                        '-no-shell-escape',
                        temp_tex_path
                    ], capture_output=True, text=True, cwd=temp_dir, env=env)
                    
                    # Vérifier si le PDF a été généré malgré les warnings
                    temp_pdf_check = os.path.join(temp_dir, base_name + '.pdf')
                    pdf_exists = os.path.exists(temp_pdf_check)
                    
                    if result.returncode != 0:
                        logger.warning(f"pdflatex a retourné un code d'erreur (passe {i+1}): {result.returncode}")
                        
                        # Vérifier si le PDF a été généré malgré l'erreur
                        if pdf_exists:
                            pdf_size = os.path.getsize(temp_pdf_check)
                            logger.info(f"PDF généré malgré les warnings: {pdf_size} bytes")
                            
                            # Analyser les types d'erreurs
                            if "security risk: running with elevated privileges" in str(result.stderr):
                                logger.warning("Warning: privilèges élevés détectés mais PDF généré")
                            elif "Output written" in str(result.stdout):
                                logger.info("PDF généré avec succès malgré les warnings LaTeX")
                        else:
                            # Vraiment une erreur critique
                            logger.error(f"Erreur pdflatex critique (passe {i+1}): {result.stderr}")
                            
                            if i == 0:  # Première passe échoue sans PDF
                                raise subprocess.CalledProcessError(result.returncode, 'pdflatex')
                    else:
                        logger.info(f"pdflatex réussi (passe {i+1})")
                
                # Déplacer le PDF final
                temp_pdf_path = os.path.join(temp_dir, base_name + '.pdf')
                if os.path.exists(temp_pdf_path):
                    import shutil
                    shutil.move(temp_pdf_path, pdf_path)
                    logger.info(f"PDF généré : {pdf_path}")
                else:
                    raise FileNotFoundError("PDF non généré par pdflatex")
            
            finally:
                # Nettoyer les fichiers temporaires
                import glob
                temp_base = os.path.splitext(temp_tex_path)[0]
                for ext in ['*.tex', '*.aux', '*.log', '*.out', '*.toc', '*.fdb_latexmk', '*.fls']:
                    for file in glob.glob(temp_base.replace(os.path.basename(temp_base), ext)):
                        try:
                            os.unlink(file)
                        except OSError:
                            pass
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export PDF : {e}")
            raise e
    
    def test_pdf_export(self):
        """Teste l'export PDF avec des données d'exemple"""
        # Données de test
        test_data = {
            'regulation_code': 'R107',
            'original_pages': 110,
            'summary_length': 1628,
            'summary_ratio': 0.111,
            'sections_count': 10,
            'summary_text': '''# RÉSUMÉ EXÉCUTIF - RÉGLEMENTATION R107

## 1. SOMMAIRE EXÉCUTIF
La **Réglementation R107** définit les **exigences techniques** pour les véhicules M2/M3.

### Objectifs principaux :
- **Sécurité des passagers**
- **Fiabilité des véhicules** 
- **Interopérabilité internationale**

## 2. EXIGENCES PRINCIPALES

### 2.1 Construction
- Stabilité latérale : **28° d'inclinaison**
- Portes de service : largeur **650 mm minimum**

### 2.2 Sécurité
- Système d'extinction automatique
- Issues d'urgence clairement signalées''',
            'sections_summaries': [
                {
                    'section_num': 1,
                    'pages_covered': [1, 2, 3, 4, 5],
                    'chunks_count': 18,
                    'actual_words': 328,
                    'target_words': 400,
                    'processing_time': 15.2
                },
                {
                    'section_num': 2,
                    'pages_covered': [6, 7, 8],
                    'chunks_count': 12,
                    'actual_words': 295,
                    'target_words': 400,
                    'processing_time': 12.8
                }
            ],
            'processing_time': 156.3,
            'metadata': {
                'total_chunks': 147,
                'llm_provider': 'mistral',
                'model': 'mistral-medium',
                'pages_covered': list(range(1, 111))
            }
        }
        
        try:
            output_path = './test_pdf'
            pdf_path = self.export_summary_to_pdf(test_data, output_path, 'test_R107.pdf')
            print(f"Test PDF généré avec succès : {pdf_path}")
            return pdf_path
        except Exception as e:
            print(f"Erreur test PDF : {e}")
            return None

# Fonction utilitaire
def test_pdf_service():
    """Teste le service d'export PDF"""
    service = PDFExportService()
    return service.test_pdf_export()

if __name__ == "__main__":
    test_pdf_service()