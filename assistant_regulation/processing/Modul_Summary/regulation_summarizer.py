"""
Service de génération de résumés réglementaires standardisés.
Étend le PromptingService et utilise le GenerationService existants.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from pathlib import Path

# Import des services existants
from assistant_regulation.planning.services.generation_service import GenerationService
from assistant_regulation.planning.services.prompting_service import PromptingService
from .pdf_text_extractor import PDFTextExtractor

# Types pour les modes de résumé
SummaryMode = Literal["concise", "normal", "detailed"]

class RegulationSummarizerPrompts(PromptingService):
    """
    Extension du PromptingService pour les résumés réglementaires.
    Réutilise l'architecture de prompting existante.
    """
    
    def __init__(self):
        super().__init__()
        # Ajouter le nouveau prompt aux builders existants
        self._builders["regulation_summary"] = self.build_regulation_summary_prompt
    
    def build_regulation_summary_prompt(
        self, 
        regulation_text: str, 
        mode: SummaryMode = "normal"
    ) -> str:
        """
        Construit le prompt pour la génération de résumé réglementaire.
        Utilise le sous-prompt fourni par l'utilisateur.
        """
        base_prompt = """INSTRUCTIONS STRICTES: Tu dois répondre UNIQUEMENT avec un JSON valide, sans aucun autre texte, commentaire ou explication.

RÔLE: Tu es un expert en réglementations automobiles. Analyse le texte de réglementation fourni et génère un résumé JSON standardisé avec exactement 15 sections.

FORMAT DE RÉPONSE OBLIGATOIRE (copie ce format exactement):
{
  "regulation_number": "<extrait du document>",
  "series": "<extrait du document>",
  "mode": "<mode_demandé>",
  "sections": [
    { "title": "Fiche d'identité", "content": "<résumé>", "details": [] },
    { "title": "Objet et champ d'application", "content": "<résumé>", "details": [] },
    { "title": "Définitions clés", "content": "<résumé>", "details": [] },
    { "title": "Classes / catégories", "content": "<résumé>", "details": [] },
    { "title": "Procédure d'homologation", "content": "<résumé>", "details": [] },
    { "title": "Marquages obligatoires", "content": "<résumé>", "details": [] },
    { "title": "Exigences techniques", "content": "<résumé>", "details": [] },
    { "title": "Essais et vérifications", "content": "<résumé>", "details": [] },
    { "title": "Conformité de la production", "content": "<résumé>", "details": [] },
    { "title": "Sanctions / Retrait", "content": "<résumé>", "details": [] },
    { "title": "Cessation de production", "content": "<résumé>", "details": [] },
    { "title": "Dispositions transitoires", "content": "<résumé>", "details": [] },
    { "title": "Services techniques / autorités", "content": "<résumé>", "details": [] },
    { "title": "Annexes – aperçu", "content": "<résumé>", "details": [] },
    { "title": "Références croisées / version", "content": "<résumé>", "details": [] }
  ],
  "generated_on": "2024-12-19"
}

RÈGLES DE CONTENU:
- Mode "concise": 3-5 phrases maximum par section
- Mode "normal": 5-10 phrases par section  
- Mode "detailed": paragraphe + liste dans "details"
- Si information manquante: "N/A"
- Langue: français uniquement

IMPORTANT: 
- Commence ta réponse directement par "{"
- Termine ta réponse par "}"
- Aucun texte avant ou après le JSON
- Aucun commentaire, explication ou markdown

TEXTE À ANALYSER:
"""
        
        return f"{base_prompt}\n\n{regulation_text}\n\nMode demandé: {mode}"


class RegulationSummarizer:
    """
    Service principal de génération de résumés réglementaires.
    
    Workflow:
    1. Extraction du texte PDF (PDFTextExtractor)
    2. Génération du résumé JSON (GenerationService + prompts étendus)
    3. Validation et nettoyage du JSON
    4. Sauvegarde optionnelle
    """
    
    def __init__(
        self,
        llm_provider: str = "mistral",
        model_name: str = "mistral-large-latest",
        output_dir: str = "temp"
    ):
        self.logger = logging.getLogger(__name__)
        
        # Services réutilisés de l'architecture existante
        self.prompting_service = RegulationSummarizerPrompts()
        self.generation_service = GenerationService(
            llm_provider=llm_provider,
            model_name=model_name,
            prompting_service=self.prompting_service
        )
        self.pdf_extractor = PDFTextExtractor()
        
        # Configuration
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"RegulationSummarizer initialisé avec {llm_provider}/{model_name}")
    
    def generate_summary_from_pdf(
        self,
        pdf_path: str,
        mode: SummaryMode = "normal",
        save_intermediate: bool = True
    ) -> Dict[str, Any]:
        """
        Génère un résumé standardisé à partir d'un PDF réglementaire.
        
        Args:
            pdf_path: Chemin vers le PDF
            mode: Mode de résumé (concise/normal/detailed)
            save_intermediate: Sauvegarder les fichiers intermédiaires
            
        Returns:
            Dict contenant le résumé JSON et les métadonnées
        """
        pdf_path = Path(pdf_path)
        self.logger.info(f"Génération du résumé pour {pdf_path.name} en mode {mode}")
        
        try:
            # 1. Extraction du texte PDF
            self.logger.info("Étape 1: Extraction du texte PDF...")
            pdf_data = self.pdf_extractor.extract_text_from_pdf(pdf_path)
            
            # 2. Génération du résumé via LLM
            self.logger.info("Étape 2: Génération du résumé via LLM...")
            summary_json = self._generate_summary_json(
                pdf_data["cleaned_text"], 
                mode
            )
            
            # 3. Validation et enrichissement du JSON
            self.logger.info("Étape 3: Validation du résumé...")
            validated_summary = self._validate_and_enrich_summary(
                summary_json, 
                pdf_data, 
                mode
            )
            
            # 4. Sauvegarde optionnelle
            if save_intermediate:
                self._save_intermediate_files(pdf_path, pdf_data, validated_summary)
            
            result = {
                "summary": validated_summary,
                "pdf_metadata": pdf_data["metadata"],
                "processing_info": {
                    "pdf_path": str(pdf_path),
                    "mode": mode,
                    "generated_at": datetime.now().isoformat(),
                    "text_length": len(pdf_data["cleaned_text"]),
                    "page_count": pdf_data["page_count"]
                }
            }
            
            self.logger.info("Génération du résumé terminée avec succès")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du résumé: {e}")
            raise
    
    def _generate_summary_json(self, text: str, mode: SummaryMode) -> Dict[str, Any]:
        """Génère le résumé JSON via le LLM"""
        # Réduction du texte si trop long (limite à ~100k caractères)
        if len(text) > 100000:
            self.logger.warning(f"Texte très long ({len(text)} chars), troncature à 100k")
            text = text[:100000] + "\n\n[... texte tronqué pour traitement LLM ...]"
        
        # Retry logic pour la génération
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Tentative {attempt + 1}/{max_retries} de génération JSON")
                
                # Construction du prompt spécialisé pour le résumé
                prompt = self.prompting_service.build_regulation_summary_prompt(text, mode)
                
                # Appel direct au client LLM pour éviter le formatting automatique du GenerationService
                raw_response = self._call_llm_directly(prompt, temperature=0.1, max_tokens=3000)
                
                # Nettoyage et parsing de la réponse
                cleaned_response = self._clean_llm_response(raw_response)
                
                if not cleaned_response.strip():
                    raise ValueError("Réponse vide du LLM")
                
                summary_json = json.loads(cleaned_response)
                self.logger.info("JSON généré avec succès")
                return summary_json
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Tentative {attempt + 1} - Erreur JSON: {e}")
                self.logger.error(f"Réponse brute: {raw_response[:500]}...")
                
                if attempt == max_retries - 1:
                    # Dernière tentative échouée, on essaie de créer un JSON de base
                    return self._create_fallback_summary(text, mode)
                
            except Exception as e:
                self.logger.error(f"Tentative {attempt + 1} - Erreur générale: {e}")
                if attempt == max_retries - 1:
                    return self._create_fallback_summary(text, mode)
    
    def _clean_llm_response(self, response: str) -> str:
        """Nettoie la réponse du LLM pour extraire le JSON"""
        # Suppression des marqueurs markdown
        response = response.strip()
        
        # Si la réponse contient ```json, extraire le contenu
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        elif "```" in response:
            # Cas où c'est juste ```
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                response = response[start:end].strip()
        
        return response
    
    def _call_llm_directly(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048) -> str:
        """Appelle directement le client LLM sans le formatting du GenerationService"""
        client_info = self.generation_service.raw_client
        
        if client_info["type"] == "mistral":
            response = client_info["client"].chat.complete(
                model=self.generation_service.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        else:  # ollama
            response = client_info["client"].chat(
                model=self.generation_service.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature},
            )
            return response["message"]["content"]
    
    def _create_fallback_summary(self, text: str, mode: SummaryMode) -> Dict[str, Any]:
        """Crée un résumé de fallback si le LLM échoue"""
        self.logger.warning("Création d'un résumé de fallback (LLM en échec)")
        
        # Extraction basique du numéro de règlement
        reg_number = self.pdf_extractor.get_regulation_number(text) or "Unknown"
        
        # Template de base
        fallback_content = "Informations non disponibles - échec de traitement LLM" if mode != "detailed" else "N/A"
        details = [] if mode != "detailed" else ["Traitement automatique en échec", "Révision manuelle nécessaire"]
        
        sections = []
        section_titles = [
            "Fiche d'identité", "Objet et champ d'application", "Définitions clés",
            "Classes / catégories", "Procédure d'homologation", "Marquages obligatoires", 
            "Exigences techniques", "Essais et vérifications", "Conformité de la production",
            "Sanctions / Retrait", "Cessation de production", "Dispositions transitoires",
            "Services techniques / autorités", "Annexes – aperçu", "Références croisées / version"
        ]
        
        for title in section_titles:
            sections.append({
                "title": title,
                "content": fallback_content,
                "details": details.copy() if mode == "detailed" else []
            })
        
        return {
            "regulation_number": reg_number,
            "series": "N/A",
            "mode": mode,
            "sections": sections,
            "generated_on": datetime.now().strftime("%Y-%m-%d"),
            "_fallback": True  # Marquer comme fallback
        }
    
    def _validate_and_enrich_summary(
        self, 
        summary: Dict[str, Any], 
        pdf_data: Dict[str, Any], 
        mode: SummaryMode
    ) -> Dict[str, Any]:
        """Valide et enrichit le résumé JSON"""
        
        # Validation de la structure
        required_fields = ["regulation_number", "series", "mode", "sections", "generated_on"]
        for field in required_fields:
            if field not in summary:
                self.logger.warning(f"Champ manquant: {field}")
                summary[field] = "N/A"
        
        # Enrichissement avec les données PDF
        if not summary.get("regulation_number") or summary["regulation_number"] == "N/A":
            reg_num = self.pdf_extractor.get_regulation_number(pdf_data["cleaned_text"])
            if reg_num:
                summary["regulation_number"] = reg_num
        
        # Validation des sections (doit y en avoir 15)
        if len(summary.get("sections", [])) != 15:
            self.logger.warning(f"Nombre de sections incorrect: {len(summary.get('sections', []))}")
        
        # Mise à jour de la date si nécessaire
        summary["generated_on"] = datetime.now().strftime("%Y-%m-%d")
        summary["mode"] = mode
        
        return summary
    
    def _save_intermediate_files(
        self, 
        pdf_path: Path, 
        pdf_data: Dict[str, Any], 
        summary: Dict[str, Any]
    ):
        """Sauvegarde les fichiers intermédiaires pour audit"""
        base_name = pdf_path.stem
        mode = summary.get("mode", "normal")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarde du JSON brut
        json_path = self.output_dir / f"{base_name}_{mode}_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"JSON sauvegardé: {json_path}") 