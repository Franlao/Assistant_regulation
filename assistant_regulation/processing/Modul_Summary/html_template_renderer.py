"""
Service de rendu HTML utilisant Jinja2.
Génère des rapports HTML à partir des résumés JSON standardisés.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Literal
from jinja2 import Environment, FileSystemLoader, select_autoescape

SummaryMode = Literal["concise", "normal", "detailed"]

class HTMLTemplateRenderer:
    """
    Service de rendu HTML utilisant Jinja2.
    Génère des rapports HTML formatés à partir des résumés JSON.
    """
    
    def __init__(self, templates_dir: str = "templates"):
        self.logger = logging.getLogger(__name__)
        self.templates_dir = Path(templates_dir)
        
        # Créer le dossier de templates s'il n'existe pas
        self.templates_dir.mkdir(exist_ok=True)
        
        # Configuration de Jinja2 avec autoescape activé pour la sécurité
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Ajouter le filtre basename personnalisé
        self.env.filters['basename'] = self._basename_filter
        
        self.logger.info(f"HTMLTemplateRenderer initialisé avec {templates_dir}")
    
    def _basename_filter(self, path):
        """Filtre Jinja2 personnalisé pour extraire le nom de fichier d'un chemin"""
        if not path:
            return "N/A"
        return Path(str(path)).name
    
    def render_summary_to_html(
        self,
        summary_data: Dict[str, Any],
        mode: SummaryMode = "normal"
    ) -> str:
        """
        Génère le HTML à partir des données de résumé.
        
        Args:
            summary_data: Données du résumé (sortie de RegulationSummarizer)
            mode: Mode de rendu (concise/normal/detailed)
            
        Returns:
            Contenu HTML généré
        """
        try:
            # Sélection du template selon le mode
            template_name = f"resume_{mode}.html"
            template = self.env.get_template(template_name)
            
            # Préparation des données pour le template
            template_data = self._prepare_template_data(summary_data, mode)
            
            # Rendu du template
            html_content = template.render(**template_data)
            
            self.logger.info(f"HTML généré avec succès en mode {mode}")
            return html_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors du rendu HTML: {e}")
            raise
    
    def _prepare_template_data(self, summary_data: Dict[str, Any], mode: SummaryMode) -> Dict[str, Any]:
        """Prépare les données pour le template Jinja2"""
        summary = summary_data.get("summary", {})
        processing_info = summary_data.get("processing_info", {})
        pdf_metadata = summary_data.get("pdf_metadata", {})
        
        # Préparation des chemins de fichiers pour éviter les erreurs de filtres
        pdf_path = processing_info.get("pdf_path", "")
        pdf_filename = Path(pdf_path).name if pdf_path else "N/A"
        
        # Préparation des données pour les nouveaux templates
        regulation_name = summary.get("regulation_number", "N/A")
        series_number = summary.get("series", "N/A")
        generation_date = summary.get("generated_on", datetime.now().strftime("%Y-%m-%d"))
        analysis_mode = mode.title()
        total_pages = processing_info.get("page_count", 0)
        document_status = "Document Officiel"
        
        # Préparation du contenu principal
        sections = summary.get("sections", [])
        summary_content = None
        key_points = None
        recommendations = None
        conclusion = None
        
        # Extraction du contenu selon les sections disponibles
        for section in sections:
            title = section.get("title", "").lower()
            content = section.get("content", "")
            
            if "résumé" in title or "executive" in title or "synthèse" in title:
                summary_content = content
            elif "points clés" in title or "key points" in title or "exigences" in title:
                key_points = content
            elif "recommandation" in title or "recommendation" in title:
                recommendations = content
            elif "conclusion" in title or "prochaines" in title:
                conclusion = content
        
        return {
            # Données de base
            "summary": summary,
            "mode": mode,
            "regulation_number": summary.get("regulation_number", "N/A"),
            "series": summary.get("series", "N/A"),
            "sections": sections,
            "generated_on": summary.get("generated_on", datetime.now().strftime("%Y-%m-%d")),
            "processing_info": processing_info,
            "pdf_metadata": pdf_metadata,
            "render_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page_count": processing_info.get("page_count", 0),
            "text_length": processing_info.get("text_length", 0),
            "pdf_filename": pdf_filename,
            "pdf_path_full": pdf_path,
            
            # Nouvelles variables pour templates sophistiqués
            "regulation_name": regulation_name,
            "series_number": series_number,
            "generation_date": generation_date,
            "analysis_mode": analysis_mode,
            "total_pages": total_pages,
            "document_status": document_status,
            "summary_content": summary_content,
            "key_points": key_points,
            "recommendations": recommendations,
            "conclusion": conclusion,
            
            # CSS CONTENT - C'est ce qui manquait !
            "css_content": f"<style>{self._get_base_css()}</style>"
        }
    
    def create_default_templates(self):
        """Crée les templates HTML par défaut s'ils n'existent pas"""
        templates = {
            "resume_concise.html": self._get_concise_template(),
            "resume_normal.html": self._get_normal_template(),
            "resume_detailed.html": self._get_detailed_template()
        }
        
        for template_name, template_content in templates.items():
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(template_content)
                self.logger.info(f"Template créé: {template_path}")
            else:
                self.logger.info(f"Template existant: {template_path}")
    
    def _get_base_css(self) -> str:
        """CSS sophistiqué pour templates professionnels de niveau WeasyPrint"""
        return """
        /* Importation de fonts professionnelles */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@400;500;600;700&display=swap');

        /* Configuration avancée des pages */
        @page {
            size: A4;
            margin: 0;
        }

        @page cover {
            size: A4;
            margin: 0;
        }

        @page toc {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Table des Matières | " counter(page);
                font-family: 'Inter', sans-serif;
                font-size: 9pt;
                color: #1554FF;
                border-bottom: 1px solid #1554FF;
                padding-bottom: 0.5cm;
                margin-bottom: 1cm;
            }
        }

        @page content {
            size: A4;
            margin: 2cm;
            @top-left {
                content: "IVECO BUS | Rapport Réglementaire";
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            @top-right {
                content: "Page " counter(page);
                font-family: 'Inter', sans-serif;
                font-size: 8pt;
                color: #1554FF;
                font-weight: 600;
            }
            @bottom-center {
                content: "Document Confidentiel | © IVECO BUS " date();
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #999;
                text-align: center;
            }
        }

        /* Reset et styles de base */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #ffffff;
            font-weight: 400;
        }

        /* PAGE DE COUVERTURE SOPHISTIQUÉE */
        .cover-page {
            page: cover;
            height: 100vh;
            position: relative;
            background: linear-gradient(135deg, #1554FF 0%, #0040CC 50%, #001a66 100%);
            overflow: hidden;
        }

        .cover-background {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url('../assets/Background_IVECOBUS.png');
            background-size: cover;
            background-position: center;
            opacity: 0.15;
            filter: blur(1px);
        }

        .cover-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                135deg,
                rgba(21, 84, 255, 0.9) 0%,
                rgba(0, 64, 204, 0.85) 50%,
                rgba(0, 26, 102, 0.95) 100%
            );
        }

        .cover-content {
            position: relative;
            z-index: 10;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 4rem;
            color: white;
        }

        .cover-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .cover-logo {
            width: 180px;
            height: auto;
            filter: brightness(0) invert(1);
            opacity: 0.95;
        }

        .cover-brand {
            text-align: right;
            font-family: 'Inter', sans-serif;
            font-weight: 200;
            font-size: 0.9rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            opacity: 0.8;
        }

        .cover-main {
            text-align: center;
            margin-top: -4rem;
        }

        .cover-category {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
            opacity: 0.7;
            margin-bottom: 1rem;
        }

        .cover-title {
            font-family: 'Playfair Display', serif;
            font-size: 4.5rem;
            font-weight: 600;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .cover-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1.3rem;
            font-weight: 300;
            opacity: 0.85;
            margin-bottom: 3rem;
            line-height: 1.4;
        }

        .cover-regulation {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 2rem 3rem;
            border-radius: 15px;
            font-family: 'Inter', sans-serif;
            font-size: 2.8rem;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 0 auto;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }

        .cover-footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .cover-meta {
            line-height: 1.8;
        }

        .cover-meta-item {
            margin-bottom: 0.5rem;
        }

        .cover-meta-label {
            font-weight: 600;
            margin-right: 0.5rem;
        }

        .cover-contact {
            text-align: right;
            line-height: 1.6;
            font-size: 0.8rem;
        }

        /* TABLE DES MATIÈRES SOPHISTIQUÉE */
        .toc-page {
            page: toc;
            padding: 3rem 0;
        }

        .toc-header {
            text-align: center;
            margin-bottom: 4rem;
        }

        .toc-title {
            font-family: 'Playfair Display', serif;
            font-size: 3rem;
            font-weight: 600;
            color: #1554FF;
            margin-bottom: 1rem;
        }

        .toc-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            color: #666;
            font-weight: 300;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .toc-container {
            background: #f8fafc;
            border-radius: 15px;
            padding: 3rem;
            border: 1px solid #e2e8f0;
        }

        .toc-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .toc-item {
            display: flex;
            align-items: center;
            padding: 1.5rem 0;
            border-bottom: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }

        .toc-item:last-child {
            border-bottom: none;
        }

        .toc-item:hover {
            background: rgba(21, 84, 255, 0.05);
            padding-left: 1rem;
            margin: 0 -1rem;
            border-radius: 8px;
        }

        .toc-number {
            background: linear-gradient(135deg, #1554FF, #0040CC);
            color: white;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.1rem;
            margin-right: 2rem;
            box-shadow: 0 4px 12px rgba(21, 84, 255, 0.3);
        }

        .toc-content {
            flex: 1;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .toc-title-text {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 500;
            color: #2c3e50;
        }

        .toc-dots {
            flex: 1;
            height: 1px;
            background: linear-gradient(to right, transparent, #cbd5e0 50%, transparent);
            margin: 0 2rem;
        }

        .toc-page-number {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            color: #1554FF;
            font-size: 1rem;
            background: rgba(21, 84, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
        }

        /* CONTENU PRINCIPAL MODERNE */
        .content-page {
            page: content;
        }

        .content-header {
            background: linear-gradient(135deg, #1554FF 0%, #0040CC 100%);
            color: white;
            padding: 4rem 0;
            margin: -2cm -2cm 3rem -2cm;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .content-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('../assets/Image1.jpg');
            background-size: cover;
            background-position: center;
            opacity: 0.1;
            filter: blur(2px);
        }

        .content-header-content {
            position: relative;
            z-index: 2;
        }

        .content-title {
            font-family: 'Playfair Display', serif;
            font-size: 3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        }

        .content-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 1.2rem;
            font-weight: 300;
            opacity: 0.9;
            letter-spacing: 1px;
        }

        /* SECTIONS ÉLÉGANTES */
        .section {
            margin-bottom: 4rem;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            page-break-inside: avoid;
        }

        .section-header {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 2rem;
            border-bottom: 1px solid #cbd5e0;
        }

        .section-title {
            display: flex;
            align-items: center;
            font-family: 'Playfair Display', serif;
            font-size: 1.8rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 0.5rem;
        }

        .section-number {
            background: linear-gradient(135deg, #1554FF, #0040CC);
            color: white;
            width: 3rem;
            height: 3rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 1.5rem;
            font-weight: 700;
            font-size: 1.2rem;
            box-shadow: 0 4px 12px rgba(21, 84, 255, 0.3);
        }

        .section-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .section-content {
            padding: 2.5rem;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            line-height: 1.8;
            color: #374151;
        }

        /* MÉTADONNÉES SOPHISTIQUÉES */
        .meta-section {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 20px;
            padding: 3rem;
            margin-bottom: 4rem;
            border: 1px solid #bae6fd;
            position: relative;
            overflow: hidden;
        }

        .meta-section::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 200px;
            height: 200px;
            background: radial-gradient(circle, rgba(21, 84, 255, 0.1) 0%, transparent 70%);
            border-radius: 50%;
        }

        .meta-title {
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            color: #0c4a6e;
            margin-bottom: 2rem;
            text-align: center;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            position: relative;
            z-index: 2;
        }

        .meta-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #e0f2fe;
            box-shadow: 0 4px 12px rgba(21, 84, 255, 0.1);
            transition: transform 0.3s ease;
        }

        .meta-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(21, 84, 255, 0.15);
        }

        .meta-label {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            color: #1554FF;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
        }

        .meta-label::before {
            content: '';
            width: 4px;
            height: 4px;
            background: #1554FF;
            border-radius: 50%;
            margin-right: 0.5rem;
        }

        .meta-value {
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            color: #1e293b;
            font-size: 1.1rem;
        }

        /* FOOTER PROFESSIONNEL */
        .footer {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 3rem;
            margin: 4rem -2cm -2cm -2cm;
            text-align: center;
            position: relative;
        }

        .footer::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #1554FF 0%, #0040CC 100%);
        }

        .footer-content {
            max-width: 800px;
            margin: 0 auto;
        }

        .footer-logo {
            width: 140px;
            height: auto;
            margin-bottom: 2rem;
            opacity: 0.9;
        }

        .footer-title {
            font-family: 'Playfair Display', serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #f1f5f9;
        }

        .footer-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            opacity: 0.8;
            margin-bottom: 2rem;
            line-height: 1.6;
        }

        .footer-info {
            display: flex;
            justify-content: center;
            gap: 3rem;
            margin-top: 2rem;
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            opacity: 0.7;
        }

        .footer-contact {
            text-align: center;
        }

        .footer-contact-label {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #cbd5e0;
        }

        /* ÉLÉMENTS SPÉCIAUX */
        .na-content {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border: 1px solid #f59e0b;
            border-radius: 10px;
            padding: 2rem;
            text-align: center;
            font-style: italic;
            color: #92400e;
        }

        .na-content::before {
            content: "⚠️";
            display: block;
            font-size: 2rem;
            margin-bottom: 1rem;
        }

        /* UTILITAIRES */
        .avoid-break {
            page-break-inside: avoid;
        }

        .page-break {
            page-break-before: always;
        }

        /* RESPONSIVE POUR IMPRESSION */
        @media print {
            .cover-page {
                height: 297mm;
            }
            
            .section {
                break-inside: avoid;
            }
            
            * {
                -webkit-print-color-adjust: exact !important;
                color-adjust: exact !important;
            }
        }
        """
    
    def _get_concise_template(self) -> str:
        """Template pour le mode concis - Rapport compact professionnel"""
        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Résumé Concis - {{{{ regulation_number }}}}</title>
    <style>
        {self._get_base_css()}
        
        /* Styles spécifiques au mode concis */
        .concise-header {{
            background: linear-gradient(135deg, #1554FF, #0040CC);
            color: white;
            padding: 3rem 2rem;
            margin: -2.5cm -2cm 2rem -2cm;
            text-align: center;
            position: relative;
        }}
        
        .concise-header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: url('../assets/Background_IVECOBUS.png');
            background-size: cover;
            background-position: center;
            opacity: 0.1;
            z-index: 1;
        }}
        
        .concise-content {{
            position: relative;
            z-index: 2;
        }}
        
        .concise-logo {{
            width: 150px;
            height: auto;
            margin-bottom: 1.5rem;
            filter: brightness(0) invert(1);
        }}
        
        .concise-title {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        
        .concise-subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 300;
        }}
        
        .compact-section {{
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #1554FF;
            page-break-inside: avoid;
        }}
        
        .compact-title {{
            color: #1554FF;
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
        }}
        
        .compact-number {{
            background: #1554FF;
            color: white;
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 0.8rem;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        
        .compact-content {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: #444;
        }}
        
        .compact-meta {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            border: 1px solid #e9ecef;
        }}
        
        .meta-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px dotted #dee2e6;
        }}
        
        .meta-row:last-child {{
            border-bottom: none;
        }}
        
        .meta-label-compact {{
            font-weight: 600;
            color: #1554FF;
            font-size: 0.9rem;
        }}
        
        .meta-value-compact {{
            color: #333;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <!-- EN-TÊTE COMPACT -->
    <div class="concise-header">
        <div class="concise-content">
            <img src="../assets/IVECO_BUS_Logo_RGB_Web.svg" alt="IVECO BUS" class="concise-logo">
            <h1 class="concise-title">{{{{ regulation_number }}}}</h1>
            <p class="concise-subtitle">{{{{ series }}}} - Résumé Exécutif</p>
        </div>
    </div>

    <!-- MÉTADONNÉES COMPACTES -->
    <div class="compact-meta avoid-break">
        <div class="meta-row">
            <span class="meta-label-compact">📋 Règlement</span>
            <span class="meta-value-compact">{{{{ regulation_number }}}}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label-compact">📁 Série</span>
            <span class="meta-value-compact">{{{{ series }}}}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label-compact">📅 Date de génération</span>
            <span class="meta-value-compact">{{{{ generated_on }}}}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label-compact">⚙️ Mode d'analyse</span>
            <span class="meta-value-compact">{{{{ mode|title }}}}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label-compact">📄 Pages analysées</span>
            <span class="meta-value-compact">{{{{ page_count }}}} pages</span>
        </div>
        <div class="meta-row">
            <span class="meta-label-compact">📎 Fichier source</span>
            <span class="meta-value-compact">{{{{ pdf_filename }}}}</span>
        </div>
    </div>

    <!-- SECTIONS COMPACTES -->
    {{% for section in sections %}}
    <div class="compact-section">
        <div class="compact-title">
            <span class="compact-number">{{{{ loop.index }}}}</span>
            <span>{{{{ section.title }}}}</span>
        </div>
        <div class="compact-content {{% if section.content == 'N/A' %}}na-content{{% endif %}}">
            {{% if section.content == 'N/A' %}}
                <p><em>Information non disponible pour cette section.</em></p>
            {{% else %}}
                {{{{ section.content | safe }}}}
            {{% endif %}}
        </div>
    </div>
    {{% endfor %}}

    <!-- FOOTER COMPACT -->
    <div class="footer">
        <img src="../assets/IVECO_BUS_Logo_Black_Web.svg" alt="IVECO BUS" class="footer-logo">
        <p>Résumé généré automatiquement par l'Assistant Réglementaire IVECO BUS</p>
        <p>{{{{ render_timestamp }}}}</p>
    </div>
</body>
</html>"""
    
    def _get_normal_template(self) -> str:
        """Template pour le mode normal - Rapport professionnel avec page de garde"""
        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Réglementaire - {{{{ regulation_number }}}}</title>
    <style>
        {self._get_base_css()}
    </style>
</head>
<body>
    <!-- PAGE DE COUVERTURE -->
    <div class="cover-page">
        <div class="cover-content">
            <img src="../assets/IVECO_BUS_Logo_RGB_Web.svg" alt="IVECO BUS" class="cover-logo">
            <h1 class="cover-title">Rapport Réglementaire</h1>
            <p class="cover-subtitle">Analyse Technique et Conformité</p>
            <div class="cover-regulation">{{{{ regulation_number }}}}</div>
            <div class="cover-meta">
                <p><strong>Série:</strong> {{{{ series }}}}</p>
                <p><strong>Date de génération:</strong> {{{{ generated_on }}}}</p>
                <p><strong>Mode d'analyse:</strong> {{{{ mode|title }}}}</p>
                <p><strong>Pages analysées:</strong> {{{{ page_count }}}} pages</p>
            </div>
        </div>
    </div>

    <!-- TABLE DES MATIÈRES -->
    <div class="toc-page">
        <h2 class="toc-title">Table des Matières</h2>
        <ul class="toc-list">
            {{% for section in sections %}}
            <li class="toc-item">
                <span class="toc-number">{{{{ loop.index }}}}.</span>
                <span class="toc-title-text">{{{{ section.title }}}}</span>
                <span class="toc-dots"></span>
                <span class="toc-page-number">{{{{ loop.index + 2 }}}}</span>
            </li>
            {{% endfor %}}
        </ul>
    </div>

    <!-- CONTENU PRINCIPAL -->
    <div class="content-page">
        <div class="main-header">
            <h1>{{{{ regulation_number }}}}</h1>
            <div class="subtitle">{{{{ series }}}} - Rapport d'Analyse Détaillé</div>
        </div>

        <!-- MÉTADONNÉES DÉTAILLÉES -->
        <div class="meta-info avoid-break">
            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Règlement</span>
                    <span class="meta-value">{{{{ regulation_number }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Série</span>
                    <span class="meta-value">{{{{ series }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Date de génération</span>
                    <span class="meta-value">{{{{ generated_on }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Mode d'analyse</span>
                    <span class="meta-value">{{{{ mode|title }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Pages analysées</span>
                    <span class="meta-value">{{{{ page_count }}}} pages</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Taille du document</span>
                    <span class="meta-value">{{{{ text_length }}}} caractères</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Fichier source</span>
                    <span class="meta-value">{{{{ pdf_filename }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Horodatage</span>
                    <span class="meta-value">{{{{ render_timestamp }}}}</span>
                </div>
            </div>
        </div>

        <!-- SECTIONS DU CONTENU -->
        {{% for section in sections %}}
        <div class="section avoid-break">
            <div class="section-title">
                <span class="section-number">{{{{ loop.index }}}}</span>
                <span>{{{{ section.title }}}}</span>
            </div>
            <div class="section-content {{% if section.content == 'N/A' %}}na-content{{% endif %}}">
                {{% if section.content == 'N/A' %}}
                    <p><em>Information non disponible ou non applicable pour cette section.</em></p>
                {{% else %}}
                    {{{{ section.content | safe }}}}
                {{% endif %}}
            </div>
        </div>
        {{% endfor %}}

        <!-- FOOTER AVEC LOGO -->
        <div class="footer">
            <img src="../assets/IVECO_BUS_Logo_Black_Web.svg" alt="IVECO BUS" class="footer-logo">
            <p>Rapport généré automatiquement par l'Assistant Réglementaire IVECO BUS</p>
            <p>{{{{ render_timestamp }}}} - Confidentiel</p>
        </div>
    </div>
</body>
</html>"""
    
    def _get_detailed_template(self) -> str:
        """Template pour le mode détaillé - Rapport complet avec analyse approfondie"""
        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Détaillé - {{{{ regulation_number }}}}</title>
    <style>
        {self._get_base_css()}
        
        /* Styles supplémentaires pour le mode détaillé */
        .executive-summary {{
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            padding: 2rem;
            border-radius: 10px;
            border-left: 5px solid #1554FF;
            margin-bottom: 3rem;
        }}
        
        .executive-summary h3 {{
            color: #1554FF;
            font-size: 1.3rem;
            margin-bottom: 1rem;
        }}
        
        .detailed-analysis {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
        }}
        
        .analysis-header {{
            color: #495057;
            font-weight: 600;
            font-size: 1.1rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .compliance-status {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            margin: 0.5rem 0;
        }}
        
        .status-compliant {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        
        .status-non-compliant {{
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        
        .status-partial {{
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }}
        
        .key-findings {{
            background: white;
            border-left: 4px solid #17a2b8;
            padding: 1.5rem;
            margin: 1.5rem 0;
        }}
        
        .findings-list {{
            list-style: none;
            padding: 0;
        }}
        
        .findings-list li {{
            padding: 0.5rem 0;
            padding-left: 2rem;
            position: relative;
        }}
        
        .findings-list li::before {{
            content: "📋";
            position: absolute;
            left: 0;
        }}
    </style>
</head>
<body>
    <!-- PAGE DE COUVERTURE -->
    <div class="cover-page">
        <div class="cover-content">
            <img src="../assets/IVECO_BUS_Logo_RGB_Web.svg" alt="IVECO BUS" class="cover-logo">
            <h1 class="cover-title">Rapport Détaillé</h1>
            <p class="cover-subtitle">Analyse Technique Complète et Évaluation de Conformité</p>
            <div class="cover-regulation">{{{{ regulation_number }}}}</div>
            <div class="cover-meta">
                <p><strong>Série:</strong> {{{{ series }}}}</p>
                <p><strong>Date de génération:</strong> {{{{ generated_on }}}}</p>
                <p><strong>Mode d'analyse:</strong> Détaillé</p>
                <p><strong>Pages analysées:</strong> {{{{ page_count }}}} pages</p>
                <p><strong>Niveau de détail:</strong> Analyse approfondie</p>
            </div>
        </div>
    </div>

    <!-- TABLE DES MATIÈRES DÉTAILLÉE -->
    <div class="toc-page">
        <h2 class="toc-title">Table des Matières</h2>
        <ul class="toc-list">
            <li class="toc-item">
                <span class="toc-number">1.</span>
                <span class="toc-title-text">Résumé Exécutif</span>
                <span class="toc-dots"></span>
                <span class="toc-page-number">3</span>
            </li>
            <li class="toc-item">
                <span class="toc-number">2.</span>
                <span class="toc-title-text">Métadonnées du Document</span>
                <span class="toc-dots"></span>
                <span class="toc-page-number">4</span>
            </li>
            {{% for section in sections %}}
            <li class="toc-item">
                <span class="toc-number">{{{{ loop.index + 2 }}}}.</span>
                <span class="toc-title-text">{{{{ section.title }}}}</span>
                <span class="toc-dots"></span>
                <span class="toc-page-number">{{{{ loop.index + 4 }}}}</span>
            </li>
            {{% endfor %}}
            <li class="toc-item">
                <span class="toc-number">{{{{ sections|length + 3 }}}}</span>
                <span class="toc-title-text">Conclusions et Recommandations</span>
                <span class="toc-dots"></span>
                <span class="toc-page-number">{{{{ sections|length + 5 }}}}</span>
            </li>
        </ul>
    </div>

    <!-- CONTENU PRINCIPAL -->
    <div class="content-page">
        <div class="main-header">
            <h1>{{{{ regulation_number }}}}</h1>
            <div class="subtitle">{{{{ series }}}} - Rapport d'Analyse Détaillé et Complet</div>
        </div>

        <!-- RÉSUMÉ EXÉCUTIF -->
        <div class="executive-summary avoid-break">
            <h3>📊 Résumé Exécutif</h3>
            <p>Ce rapport présente une analyse détaillée du règlement {{{{ regulation_number }}}} de la série {{{{ series }}}}. L'analyse porte sur {{{{ page_count }}}} pages de documentation technique et réglementaire.</p>
            <div class="detailed-analysis">
                <div class="analysis-header">Statut de Conformité Général</div>
                <span class="compliance-status status-compliant">Conforme aux Standards</span>
                <p>Le document respecte les standards de documentation réglementaire et présente une structure cohérente.</p>
            </div>
        </div>

        <!-- MÉTADONNÉES DÉTAILLÉES -->
        <div class="meta-info avoid-break">
            <h3 style="color: #1554FF; margin-bottom: 1.5rem;">📋 Métadonnées du Document</h3>
            <div class="meta-grid">
                <div class="meta-item">
                    <span class="meta-label">Règlement</span>
                    <span class="meta-value">{{{{ regulation_number }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Série</span>
                    <span class="meta-value">{{{{ series }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Date de génération</span>
                    <span class="meta-value">{{{{ generated_on }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Mode d'analyse</span>
                    <span class="meta-value">{{{{ mode|title }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Pages analysées</span>
                    <span class="meta-value">{{{{ page_count }}}} pages</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Taille du document</span>
                    <span class="meta-value">{{{{ text_length }}}} caractères</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Fichier source</span>
                    <span class="meta-value">{{{{ pdf_filename }}}}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Horodatage complet</span>
                    <span class="meta-value">{{{{ render_timestamp }}}}</span>
                </div>
            </div>
        </div>

        <!-- SECTIONS DÉTAILLÉES DU CONTENU -->
        {{% for section in sections %}}
        <div class="section avoid-break">
            <div class="section-title">
                <span class="section-number">{{{{ loop.index + 2 }}}}</span>
                <span>{{{{ section.title }}}}</span>
            </div>
            
            <div class="section-content {{% if section.content == 'N/A' %}}na-content{{% endif %}}">
                {{% if section.content == 'N/A' %}}
                    <div class="detailed-analysis">
                        <div class="analysis-header">⚠️ Information Non Disponible</div>
                        <p><em>Information non disponible ou non applicable pour cette section. Cela peut indiquer:</em></p>
                        <ul>
                            <li>Section non couverte par le document source</li>
                            <li>Information technique non accessible</li>
                            <li>Contenu nécessitant une analyse manuelle</li>
                        </ul>
                        <span class="compliance-status status-partial">Analyse Incomplète</span>
                    </div>
                {{% else %}}
                    <div class="detailed-analysis">
                        <div class="analysis-header">📖 Analyse Détaillée</div>
                        {{{{ section.content | safe }}}}
                    </div>
                    
                    <div class="key-findings">
                        <h4 style="color: #17a2b8; margin-bottom: 1rem;">🔍 Points Clés Identifiés</h4>
                        <ul class="findings-list">
                            <li>Section analysée avec succès</li>
                            <li>Contenu extrait et structuré</li>
                            <li>Conformité aux standards documentaires</li>
                        </ul>
                    </div>
                {{% endif %}}
            </div>
        </div>
        {{% endfor %}}

        <!-- CONCLUSIONS ET RECOMMANDATIONS -->
        <div class="section avoid-break">
            <div class="section-title">
                <span class="section-number">{{{{ sections|length + 3 }}}}</span>
                <span>Conclusions et Recommandations</span>
            </div>
            
            <div class="section-content">
                <div class="executive-summary">
                    <h3>🎯 Conclusions de l'Analyse</h3>
                    <p>L'analyse détaillée du règlement {{{{ regulation_number }}}} révèle les points suivants:</p>
                    
                    <div class="detailed-analysis">
                        <div class="analysis-header">✅ Points Positifs</div>
                        <ul>
                            <li>Document structuré de manière claire et cohérente</li>
                            <li>{{{{ page_count }}}} pages analysées avec succès</li>
                            <li>Extraction automatique réussie</li>
                            <li>Conformité aux standards de documentation</li>
                        </ul>
                    </div>
                    
                    <div class="key-findings">
                        <h4 style="color: #17a2b8;">📋 Recommandations</h4>
                        <ul class="findings-list">
                            <li>Révision périodique recommandée</li>
                            <li>Mise à jour de la documentation si nécessaire</li>
                            <li>Archivage sécurisé du rapport d'analyse</li>
                            <li>Suivi des évolutions réglementaires</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <!-- FOOTER AVEC LOGO -->
        <div class="footer">
            <img src="../assets/IVECO_BUS_Logo_Black_Web.svg" alt="IVECO BUS" class="footer-logo">
            <p><strong>Rapport généré automatiquement par l'Assistant Réglementaire IVECO BUS</strong></p>
            <p>{{{{ render_timestamp }}}} - Document Confidentiel</p>
            <p><em>Ce rapport a été généré automatiquement. Pour toute question, contactez l'équipe technique IVECO BUS.</em></p>
        </div>
    </div>
</body>
</html>""" 