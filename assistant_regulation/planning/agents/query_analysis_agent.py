# src/Planning_pattern/query_analysis_agent.py

import logging
import re
from typing import Dict, Optional, Tuple, Union, List

class QueryAnalysisAgent:
    """
    Agent qui analyse la requête utilisateur pour déterminer si elle nécessite
    une recherche RAG ou si elle peut être répondue directement par le modèle.
    Détecte également les URLs et peut suggérer une recherche web au besoin.
    """

    def __init__(self, llm_provider: str = "ollama", model_name: str = "llama3.2"):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        self.llm_client = self._init_llm_client()

        self.regulation_keywords = [
            # French keywords
            "réglementation", "norme", "exigence", "spécification", "directive", 
            "dispositif", "véhicule", "automobile", "catégorie", "classe", 
            "champ de vision", "vision indirecte", "rétroviseur", "bus", "siège",
            "poids", "poids lourd", "pmr", "réreglementaires",
            # English keywords
            "regulation", "standard", "requirement", "specification", "directive",
            "device", "vehicle", "automotive", "category", "class", "field of vision",
            "indirect vision", "mirror", "mirrors", "seat", "weight", "heavy duty",
            "commercial vehicle", "passenger", "truck", "bus",
            # Regulation codes
            "ECE", "UN/ECE", "R046", "R107", "R003", "R013", "R014", "R016", 
            "R019", "R023", "R028", "R030", "R031", "R034", "R038", "R039",
            "R043", "R048", "R049", "R051", "R058", "R065", "R066", "R067",
            "R069", "R070", "R077", "R079", "R087", "R089", "R090", "R091",
            "R108", "R109", "R110", "R111", "R112", "R117", "R119", "R124",
            "R130", "R131", "R142", "R149", "R154", "R156", "R164"
        ]

        self.regulation_patterns = [
            r"r\d+",  # R046, R107, etc.
            r"classe\s+[ivx]+",  # Classe I, II, III, IV
            r"class\s+[ivx]+",   # Class I, II, III, IV (English)
            r"champ\s+de\s+vision",  # French
            r"field\s+of\s+vision",  # English
            r"dispositif.*vision",   # French
            r"device.*vision",       # English
            r"réglementation.*automobile",  # French
            r"automotive.*regulation",      # English
            r"vehicle.*regulation",         # English
            r"mirror.*requirement",         # English
            r"safety.*requirement"          # English
        ]

        # Capture toute l'URL (chemins, paramètres, ancres) jusqu'à un séparateur d'espace ou fin de chaîne
        self.url_pattern = r'https?://[^\s]+'

    def _init_llm_client(self):
        if self.llm_provider == "mistral":
            try:
                from mistralai import Mistral
                import os
                api_key = os.getenv("MISTRAL_API_KEY")
                if not api_key:
                    raise ValueError("MISTRAL_API_KEY environment variable not set")
                return {'type': 'mistral', 'client': Mistral(api_key=api_key)}
            except (ImportError, NameError):
                self.logger.error("Mistral AI package not installed or not found")
                return None
        else:
            try:
                import ollama
                return {'type': 'ollama', 'client': ollama}
            except ImportError:
                self.logger.error("Ollama package not installed")
                return None

    def analyse_query(self, query: str) -> Dict[str, Union[bool, str, float, List]]:
        initial_analysis = self._quick_keyword_analysis(query)
        urls = self.extract_urls(query)
        contains_url = len(urls) > 0

        if not initial_analysis["contains_regulation_terms"]:
            llm_analysis = self._llm_query_analysis(query)
            result = {
                "needs_rag": llm_analysis["needs_rag"],
                "query_type": llm_analysis["query_type"],
                "confidence": llm_analysis["confidence"],
                "context_hint": llm_analysis["context_hint"]
            }
        else:
            result = {
                "needs_rag": True,
                "query_type": "regulation",
                "confidence": 0.85,
                "context_hint": "Question identifiée comme relevant des réglementations automobiles"
            }

        result.update({
            "contains_url": contains_url,
            "urls": urls,
        })

        self.logger.info(f"Query analysis result: {result}")
        return result

    def extract_urls(self, text: str) -> List[str]:
        return re.findall(self.url_pattern, text)

    def should_use_web_search(self, question: str, context: Optional[List[str]] = None) -> Dict[str, Union[bool, str]]:
        urls = self.extract_urls(question)
        contains_url = len(urls) > 0
        web_keywords = ["chercher", "rechercher", "trouver", "internet", "web", "site", "en ligne", "google"]
        has_web_keywords = any(keyword in question.lower() for keyword in web_keywords)
        context_sufficient = True
        if context:
            context_sufficient = len(''.join(context)) > 100

        recommend_web_search = contains_url or (has_web_keywords and not context_sufficient)
        reason = ""
        if contains_url:
            reason = "La question contient une URL spécifique à consulter"
        elif has_web_keywords and not context_sufficient:
            reason = "La question suggère une recherche web et le contexte est insuffisant"

        return {
            "recommend_web_search": recommend_web_search,
            "reason": reason,
            "urls": urls
        }

    def _quick_keyword_analysis(self, query: str) -> Dict[str, Union[bool, str]]:
        query_lower = query.lower()
        contains_keywords = any(keyword in query_lower for keyword in self.regulation_keywords)

        matched_patterns = []
        for pattern in self.regulation_patterns:
            if re.search(pattern, query_lower):
                matched_patterns.append(pattern)

        return {
            "contains_regulation_terms": contains_keywords or bool(matched_patterns),
            "matched_keywords": [kw for kw in self.regulation_keywords if kw in query_lower],
            "matched_patterns": matched_patterns
        }

    def _llm_query_analysis(self, query: str) -> Dict[str, Union[bool, str, float]]:
        prompt = f"""
Vous êtes un assistant chargé de classifier les questions d'un utilisateur.

Objectif : dire s'il faut interroger la base RAG de réglementations automobiles
ou si une réponse directe suffit.

INSTRUCTIONS IMPÉRATIVES
────────────────────────────────
1. Répondez STRICTEMENT par un objet JSON valide – sans commentaire,
   sans balises Markdown, sans texte supplémentaire.
2. Ne changez pas les noms de clés.
3. Les valeurs booléennes doivent être true/false (sans guillemets).
4. Les scores sont des nombres entre 0 et 1 (float).

CHAMPS À RENSEIGNER
────────────────────────────────
- needs_rag        : true si la question exige de consulter la base
                     des réglementations, false sinon.
- query_type       : "regulation" | "general" | "other"
- confidence       : niveau de confiance (0-1).
- context_hint     : courte explication (≤ 20 mots).
- contains_url     : true si la question contient au moins une URL.
- urls             : liste des URL détectées (peut être vide).

EXEMPLES
────────────────────────────────
Input : "Quel est le niveau sonore maximal autorisé selon la R51 ?"
Output :
{{
  "needs_rag": true,
  "query_type": "regulation",
  "confidence": 0.92,
  "context_hint": "Question sur limite sonore R51",
  "contains_url": false,
  "urls": [],
  "recommend_web_search": false,
  "requires_user_consent": false
}}

Input : "Bonjour, comment allez-vous ?"
Output :
{{
  "needs_rag": false,
  "query_type": "general",
  "confidence": 0.97,
  "context_hint": "Salutation",
  "contains_url": false,
  "urls": [],
  "recommend_web_search": false,
  "requires_user_consent": false
}}

Input : "Voici un lien vers la directive : https://une-url.eu"
Output :
{{
  "needs_rag": true,
  "query_type": "regulation",
  "confidence": 0.80,
  "context_hint": "Lien vers directive",
  "contains_url": true,
  "urls": ["https://une-url.eu"],
  "recommend_web_search": true,
  "requires_user_consent": false
}}

QUESTION À ANALYSER
────────────────────────────────
{query}
"""

        try:
            if self.llm_client and self.llm_client['type'] == 'mistral':
                response = self.llm_client['client'].chat.complete(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=200
                )
                response_text = response.choices[0].message.content
            elif self.llm_client and self.llm_client['type'] == 'ollama':
                response = self.llm_client['client'].chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={'temperature': 0.1}
                )
                response_text = response['message']['content']
            else:
                return {
                    "needs_rag": False,
                    "query_type": "general",
                    "confidence": 0.5,
                    "context_hint": "Impossible d'analyser - client LLM indisponible"
                }

            import json, re
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Tentative de récupération du JSON entre accolades
                match = re.search(r"\{.*\}", response_text, re.S)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                    except Exception:
                        parsed = None
                else:
                    parsed = None

            if parsed:
                allowed = {"needs_rag", "query_type", "confidence", "context_hint", "contains_url", "urls"}
                result = {k: v for k, v in parsed.items() if k in allowed}
                return result

            # Fallback heuristique
            self.logger.error(f"Erreur parsing JSON: {response_text}")
            needs_rag = "regulation" in response_text.lower() or "oui" in response_text.lower()
            return {
                "needs_rag": needs_rag,
                "query_type": "general" if not needs_rag else "regulation",
                "confidence": 0.7,
                "context_hint": "Analyse basée sur la réponse textuelle"
            }

        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse LLM: {str(e)}")
            return {
                "needs_rag": False,
                "query_type": "general",
                "confidence": 0.5,
                "context_hint": f"Erreur d'analyse: {str(e)}"
            }
