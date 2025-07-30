"""
Générateur principal de résumés réglementaires.
Orchestration complète: PDF → Texte → LLM → JSON → HTML → PDF final.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Literal

try:
    import weasyprint
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("Attention: WeasyPrint n'est pas installé. La conversion PDF ne sera pas disponible.")

from .regulation_summarizer import RegulationSummarizer, SummaryMode
from .html_template_renderer import HTMLTemplateRenderer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("regulation_summary.log", encoding='utf-8')
    ]
)

class RegulationResumeGenerator:
    """
    Générateur complet de résumés réglementaires.
    
    Workflow complet:
    1. PDF → Extraction texte (PDFTextExtractor)
    2. Texte → Résumé JSON (RegulationSummarizer + LLM)
    3. JSON → HTML (HTMLTemplateRenderer + Jinja2)
    4. HTML → PDF final (WeasyPrint)
    """
    
    def __init__(
        self,
        llm_provider: str = "mistral",
        model_name: str = "mistral-large-latest",
        templates_dir: str = "templates",
        output_dir: str = "output"
    ):
        self.logger = logging.getLogger(__name__)
        
        # Initialisation des services
        self.summarizer = RegulationSummarizer(
            llm_provider=llm_provider,
            model_name=model_name,
            output_dir=output_dir
        )
        
        self.html_renderer = HTMLTemplateRenderer(templates_dir=templates_dir)
        
        # Configuration des dossiers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Créer les templates par défaut
        self.html_renderer.create_default_templates()
        
        self.logger.info(f"RegulationResumeGenerator initialisé")
        self.logger.info(f"LLM: {llm_provider}/{model_name}")
        self.logger.info(f"WeasyPrint disponible: {WEASYPRINT_AVAILABLE}")
    
    def generate_complete_resume(
        self,
        pdf_path: str,
        mode: SummaryMode = "normal",
        output_formats: list = None,
        regulation_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère un résumé complet avec tous les formats demandés.
        
        Args:
            pdf_path: Chemin vers le PDF source
            mode: Mode de résumé (concise/normal/detailed)
            output_formats: Liste des formats de sortie ['json', 'html', 'pdf']
            regulation_number: Numéro de règlement (détecté automatiquement si None)
            
        Returns:
            Dict avec les chemins des fichiers générés et les métadonnées
        """
        if output_formats is None:
            output_formats = ['json', 'html', 'pdf']
        
        pdf_path = Path(pdf_path)
        self.logger.info(f"=== Génération complète pour {pdf_path.name} ===")
        
        try:
            # 1. Génération du résumé JSON
            self.logger.info("Étape 1: Génération du résumé JSON...")
            summary_data = self.summarizer.generate_summary_from_pdf(
                str(pdf_path),
                mode=mode,
                save_intermediate=True
            )
            
            # 2. Détermination du numéro de règlement
            if not regulation_number:
                regulation_number = summary_data["summary"].get("regulation_number", "Unknown")
            
            # 3. Génération des fichiers de sortie
            output_files = {}
            base_filename = f"resume_{regulation_number}_{mode}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # JSON brut
            if 'json' in output_formats:
                json_path = self._save_json(summary_data, base_filename, timestamp)
                output_files['json'] = str(json_path)
            
            # HTML
            html_content = None
            if 'html' in output_formats or 'pdf' in output_formats:
                self.logger.info("Étape 2: Génération HTML...")
                html_content = self.html_renderer.render_summary_to_html(
                    summary_data, mode=mode
                )
                
                if 'html' in output_formats:
                    html_path = self._save_html(html_content, base_filename, timestamp)
                    output_files['html'] = str(html_path)
            
            # PDF final
            if 'pdf' in output_formats and WEASYPRINT_AVAILABLE:
                self.logger.info("Étape 3: Conversion HTML vers PDF...")
                pdf_path = self._convert_html_to_pdf(
                    html_content, base_filename, timestamp
                )
                output_files['pdf'] = str(pdf_path)
            elif 'pdf' in output_formats:
                self.logger.warning("WeasyPrint non disponible, PDF ignoré")
            
            # Résultat final
            result = {
                "success": True,
                "regulation_number": regulation_number,
                "mode": mode,
                "output_files": output_files,
                "summary_data": summary_data,
                "generated_at": datetime.now().isoformat(),
                "processing_time": self._calculate_processing_time()
            }
            
            self.logger.info("=== Génération terminée avec succès ===")
            for format_type, file_path in output_files.items():
                self.logger.info(f"{format_type.upper()}: {file_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération complète: {e}")
            return {
                "success": False,
                "error": str(e),
                "regulation_number": regulation_number,
                "mode": mode,
                "generated_at": datetime.now().isoformat()
            }
    
    def _save_json(self, summary_data: Dict[str, Any], base_filename: str, timestamp: str) -> Path:
        """Sauvegarde le JSON"""
        json_path = self.output_dir / f"{base_filename}_{timestamp}.json"
        
        import json
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON sauvegardé: {json_path}")
        return json_path
    
    def _save_html(self, html_content: str, base_filename: str, timestamp: str) -> Path:
        """Sauvegarde le HTML"""
        html_path = self.output_dir / f"{base_filename}_{timestamp}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML sauvegardé: {html_path}")
        return html_path
    
    def _convert_html_to_pdf(self, html_content: str, base_filename: str, timestamp: str) -> Path:
        """Convertit HTML en PDF avec WeasyPrint"""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint n'est pas disponible")
        
        pdf_path = self.output_dir / f"{base_filename}_{timestamp}.pdf"
        
        try:
            # Configuration WeasyPrint
            html_doc = HTML(string=html_content)
            
            # CSS additionnel pour l'impression
            print_css = CSS(string="""
                @page {
                    margin: 2cm;
                    size: A4;
                }
                body {
                    font-size: 10pt;
                }
                .header h1 {
                    font-size: 14pt;
                }
                .section-title {
                    font-size: 11pt;
                }
            """)
            
            # Génération du PDF
            html_doc.write_pdf(str(pdf_path), stylesheets=[print_css])
            
            self.logger.info(f"PDF généré: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            self.logger.error(f"Erreur conversion PDF: {e}")
            raise
    
    def _calculate_processing_time(self) -> float:
        """Calcule le temps de traitement (placeholder)"""
        # TODO: Implémenter le tracking du temps réel
        return 0.0

def main():
    """Fonction principale pour utilisation en ligne de commande"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Générateur de résumés réglementaires")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF")
    parser.add_argument("--mode", choices=["concise", "normal", "detailed"], 
                       default="normal", help="Mode de résumé")
    parser.add_argument("--formats", nargs="+", choices=["json", "html", "pdf"],
                       default=["json", "html", "pdf"], help="Formats de sortie")
    parser.add_argument("--llm", default="mistral", help="Fournisseur LLM")
    parser.add_argument("--model", default="mistral-large-latest", help="Modèle LLM")
    parser.add_argument("--output-dir", default="output", help="Dossier de sortie")
    
    args = parser.parse_args()
    
    # Initialisation du générateur
    generator = RegulationResumeGenerator(
        llm_provider=args.llm,
        model_name=args.model,
        output_dir=args.output_dir
    )
    
    # Génération
    result = generator.generate_complete_resume(
        pdf_path=args.pdf_path,
        mode=args.mode,
        output_formats=args.formats
    )
    
    if result["success"]:
        print(f"✅ Génération réussie pour {result['regulation_number']}")
        for format_type, file_path in result["output_files"].items():
            print(f"  {format_type.upper()}: {file_path}")
    else:
        print(f"❌ Erreur: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main() 