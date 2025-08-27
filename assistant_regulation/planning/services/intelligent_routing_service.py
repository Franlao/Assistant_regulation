#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service d'orchestration intelligent basé sur LLM pour la sélection automatique du type de recherche.
Utilise un LLM pour analyser la requête et déterminer le type de recherche optimal.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import ollama
from mistralai import Mistral,UserMessage

# Configuration du logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class SearchType(Enum):
    """Types de recherche disponibles"""
    CLASSIC = "classic"
    BY_REGULATION = "by_regulation"
    FULL_REGULATION = "full_regulation"
    COMPARATIVE = "comparative"
    SUMMARY_REQUEST = "summary_request"  # Nouveau : demande de résumé

@dataclass
class QueryAnalysis:
    """Résultat de l'analyse de requête par LLM"""
    search_type: SearchType
    regulation_code: Optional[str]
    regulations_mentioned: List[str]
    query_cleaned: str
    confidence_score: float
    reasoning: str
    intent_description: str
    is_summary_request: bool = False  # Nouveau champ pour les demandes de résumé

class IntelligentRoutingService:
    """
    Service intelligent pour l'orchestration automatique basé sur LLM.
    Analyse les requêtes avec un LLM pour déterminer le meilleur type de recherche.
    """
    
    def __init__(self, llm_provider: str = "mistral", model_name: str = "mistral-medium"):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.mistral_client = None
        
        if llm_provider == "mistral":
            # Initialiser le client Mistral si nécessaire
            try:
                import os
                api_key = os.getenv("MISTRAL_API_KEY")
                if api_key:
                    self.mistral_client = Mistral(api_key=api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Mistral: {e}")
                self.llm_provider = "ollama"  # Fallback vers Ollama
    
    def _get_analysis_prompt(self, query: str) -> str:
        """Construit le prompt d'analyse pour le LLM"""
        
        return f"""Tu es un expert en réglementations automobiles UN/ECE. Analyse cette requête utilisateur et détermine le type de recherche optimal.

REQUÊTE UTILISATEUR: "{query}"

TYPES DE RECHERCHE DISPONIBLES:
1. "classic" - Recherche générale dans toutes les réglementations
2. "by_regulation" - Recherche ciblée dans une réglementation spécifique
3. "full_regulation" - Récupération complète d'une réglementation pour résumé
4. "comparative" - Comparaison entre plusieurs réglementations
5. "summary_request" - Demande de RÉSUMÉ COMPLET d'une réglementation

RÉGLEMENTATIONS CONNUES:
- ECE R46 (rétroviseurs, vision indirecte)
- R107 (autobus, transport en commun)
- R127, R128 (autres réglementations)

INSTRUCTIONS:
1. Identifie si la requête mentionne une réglementation spécifique (R46, R107, ECE R46, etc.)
2. Détermine l'intention de l'utilisateur:
   - Veut-il un résumé complet d'une réglementation? (mots-clés: résumé, résume, synthèse, overview, complet)
   - Veut-il comparer plusieurs réglementations?
   - Cherche-t-il quelque chose de spécifique dans une réglementation?
   - Fait-il une recherche générale?
3. Nettoie la requête pour la recherche (supprime les références réglementaires explicites)
4. Évalue ta confiance dans ton analyse (0.0 à 1.0)

RÉPONDS UNIQUEMENT EN JSON avec cette structure exacte:
{{
    "search_type": "classic|by_regulation|full_regulation|comparative|summary_request",
    "regulation_code": "code exact ou null",
    "regulations_mentioned": ["liste des codes détectés"],
    "query_cleaned": "requête nettoyée pour la recherche",
    "confidence_score": 0.85,
    "reasoning": "explication de ton choix",
    "intent_description": "description de l'intention utilisateur"
}}

EXEMPLES:
- "Quelles sont les exigences de la R107?" → by_regulation, R107
- "Résumé complet de ECE R46" → summary_request, ECE R46
- "Résume-moi la réglementation R107" → summary_request, R107
- "Différence entre R107 et R46" → comparative, [R107, R46]
- "Comment tester la résistance?" → classic, null

ANALYSE:"""

    def _call_llm(self, prompt: str) -> str:
        """Appelle le LLM pour l'analyse"""
        
        try:
            if self.llm_provider == "mistral" and self.mistral_client:
                # Utiliser Mistral AI avec mode JSON pour garantir une sortie JSON valide
                messages = [UserMessage(content=prompt)]
                response = self.mistral_client.chat.complete(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=500,
                    response_format={"type": "json_object"}  # Force la sortie JSON
                )
                return response.choices[0].message.content
            
            else:
                # Utiliser Ollama
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                )
                return response['message']['content']
                
        except Exception as e:
            logger.error(f"Erreur lors de l'appel LLM: {e}")
            # Fallback vers une analyse simple
            return self._fallback_analysis(prompt)
    
    def _fallback_analysis(self, prompt: str) -> str:
        """Analyse de fallback en cas d'erreur LLM"""
        logger.warning("Utilisation du fallback d'analyse")
        
        # Extraire la requête du prompt
        query_start = prompt.find('REQUÊTE UTILISATEUR: "') + 22
        query_end = prompt.find('"', query_start)
        query = prompt[query_start:query_end] if query_start > 21 else ""
        
        # Analyse simple basée sur des mots-clés
        query_lower = query.lower()
        
        # Détecter les codes de réglementation
        import re
        reg_matches = re.findall(r'\b(r\d+|ece\s+r\d+|un\s+r\d+)\b', query_lower)
        regulations = [match.replace(' ', ' ').upper() for match in reg_matches if match and isinstance(match, str)]
        
        # Déterminer le type de recherche
        summary_keywords = ['résumé', 'résume', 'synthèse', 'overview']
        complete_keywords = ['complet']
        
        if any(word in query_lower for word in summary_keywords):
            search_type = "summary_request" if regulations else "classic"
        elif any(word in query_lower for word in complete_keywords) and regulations:
            search_type = "full_regulation"
        elif any(word in query_lower for word in ['différence', 'comparer', 'versus', 'par rapport']):
            search_type = "comparative"
        elif regulations:
            search_type = "by_regulation"
        else:
            search_type = "classic"
        
        # Nettoyer la requête
        query_cleaned = query
        for reg in regulations:
            query_cleaned = re.sub(rf'\b{re.escape(reg)}\b', '', query_cleaned, flags=re.IGNORECASE)
        query_cleaned = re.sub(r'\s+', ' ', query_cleaned).strip()
        
        return json.dumps({
            "search_type": search_type,
            "regulation_code": regulations[0] if regulations else None,
            "regulations_mentioned": regulations,
            "query_cleaned": query_cleaned,
            "confidence_score": 0.6,
            "reasoning": "Analyse de fallback basée sur mots-clés",
            "intent_description": "Analyse simplifiée"
        })
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse la réponse du LLM - optimisé pour le mode JSON de Mistral"""
        try:
            # Vérifier si la réponse est vide
            if not response or not response.strip():
                logger.warning("Réponse LLM vide")
                raise ValueError("Réponse LLM vide")
            
            response = response.strip()
            
            # Avec le mode JSON de Mistral, la réponse devrait être du JSON pur
            # Mais on garde un nettoyage minimal pour Ollama
            if self.llm_provider != "mistral":
                # Nettoyer les blocs markdown pour Ollama
                if response.startswith('```json'):
                    response = response[7:]
                elif response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
            
            # Pour Mistral avec mode JSON, on peut parser directement
            if self.llm_provider == "mistral":
                parsed_data = json.loads(response)
            else:
                # Pour Ollama, chercher le JSON dans la réponse
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    raise ValueError("Pas de JSON trouvé dans la réponse")
                    
                json_str = response[start_idx:end_idx]
                parsed_data = json.loads(json_str)
            
            # Valider la structure
            if not isinstance(parsed_data, dict) or "search_type" not in parsed_data:
                raise ValueError("Structure JSON invalide")
                
            return parsed_data
                
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {e}")
            logger.error(f"Réponse reçue: {response[:300] if response else 'None'}")
        except Exception as e:
            logger.error(f"Erreur parsing LLM response: {e}")
            
        # Fallback robuste
        return {
            "search_type": "classic",
            "regulation_code": None,
            "regulations_mentioned": [],
            "query_cleaned": "",
            "confidence_score": 0.3,
            "reasoning": "Erreur de parsing LLM - fallback utilisé",
            "intent_description": "Analyse par défaut"
        }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyse une requête avec un LLM pour déterminer le type de recherche optimal.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            QueryAnalysis avec le type de recherche recommandé
        """
        logger.info(f"Analyse LLM de la requête: {query}")
        
        # Construire le prompt
        prompt = self._get_analysis_prompt(query)
        
        # Appeler le LLM
        llm_response = self._call_llm(prompt)
        
        # Parser la réponse
        analysis_data = self._parse_llm_response(llm_response)
        
        # Valider et normaliser les données
        analysis_data = self._validate_analysis_data(analysis_data, query)
        
        # Créer l'objet QueryAnalysis
        result = QueryAnalysis(
            search_type=SearchType(analysis_data["search_type"]),
            regulation_code=analysis_data.get("regulation_code"),
            regulations_mentioned=analysis_data.get("regulations_mentioned", []),
            query_cleaned=analysis_data.get("query_cleaned", query),
            confidence_score=float(analysis_data.get("confidence_score", 0.5)),
            reasoning=analysis_data.get("reasoning", "Analyse LLM"),
            intent_description=analysis_data.get("intent_description", "")
        )
        
        logger.info(f"Résultat LLM: {result.search_type.value} - Confiance: {result.confidence_score:.2f}")
        return result
    
    def _validate_analysis_data(self, data: Dict, original_query: str) -> Dict:
        """Valide et normalise les données d'analyse"""
        
        # Valider le type de recherche
        if data.get("search_type") not in [t.value for t in SearchType]:
            data["search_type"] = "classic"
        
        # Valider le code de réglementation
        if data.get("regulation_code"):
            reg_code = data["regulation_code"]
            # Gérer le cas où c'est une liste (erreur LLM)
            if isinstance(reg_code, list):
                reg_code = reg_code[0] if reg_code else None
            
            if reg_code and isinstance(reg_code, str):
                reg_code = reg_code.upper()
                # Normaliser le format
                if not reg_code.startswith(('R', 'ECE', 'UN')):
                    reg_code = f"R{reg_code}"
                data["regulation_code"] = reg_code
            else:
                data["regulation_code"] = None
        
        # Valider les réglementations mentionnées
        if not isinstance(data.get("regulations_mentioned"), list):
            data["regulations_mentioned"] = []
        
        # Valider la requête nettoyée
        if not data.get("query_cleaned") or data["query_cleaned"].strip() == "":
            data["query_cleaned"] = original_query
        
        # Valider le score de confiance
        try:
            confidence = float(data.get("confidence_score", 0.5))
            data["confidence_score"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            data["confidence_score"] = 0.5
        
        return data
    
    def get_routing_decision(self, query: str) -> Dict:
        """
        Décision de routage complète pour l'orchestrateur.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Dictionnaire avec toutes les informations nécessaires pour le routage
        """
        analysis = self.analyze_query(query)
        
        # Préparer les paramètres selon le type de recherche
        routing_params = {
            'search_type': analysis.search_type.value,
            'query': analysis.query_cleaned,
            'confidence': analysis.confidence_score,
            'reasoning': analysis.reasoning,
            'intent': analysis.intent_description
        }
        
        # Paramètres spécifiques selon le type
        if analysis.search_type == SearchType.BY_REGULATION:
            routing_params['regulation_code'] = analysis.regulation_code
            routing_params['method'] = 'search_by_regulation'
            routing_params['params'] = {
                'regulation_code': analysis.regulation_code,
                'query': analysis.query_cleaned
            }
            
        elif analysis.search_type == SearchType.FULL_REGULATION:
            routing_params['regulation_code'] = analysis.regulation_code
            routing_params['method'] = 'get_all_chunks_for_regulation'
            routing_params['params'] = {
                'regulation_code': analysis.regulation_code
            }
            routing_params['query'] = f"Résumé complet de {analysis.regulation_code}"
            
        elif analysis.search_type == SearchType.COMPARATIVE:
            routing_params['regulations'] = analysis.regulations_mentioned
            routing_params['method'] = 'comparative_search'
            routing_params['params'] = {
                'regulations': analysis.regulations_mentioned,
                'query': analysis.query_cleaned
            }
            
        elif analysis.search_type == SearchType.SUMMARY_REQUEST:
            routing_params['regulation_code'] = analysis.regulation_code
            routing_params['method'] = 'intelligent_summary'
            routing_params['params'] = {
                'regulation_code': analysis.regulation_code
            }
            routing_params['query'] = f"Résumé intelligent de {analysis.regulation_code}"
            
        else:  # SearchType.CLASSIC
            routing_params['method'] = 'search'
            routing_params['params'] = {
                'query': query  # Requête originale pour la recherche classique
            }
        
        return routing_params
    
    def explain_decision(self, query: str) -> str:
        """
        Explique la décision de routage de manière lisible.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Explication textuelle de la décision
        """
        decision = self.get_routing_decision(query)
        
        explanation = f"Analyse de la requête: '{query}'\n\n"
        explanation += f"Type de recherche sélectionné: {decision['search_type']}\n"
        explanation += f"Confiance: {decision['confidence']:.0%}\n"
        explanation += f"Raisonnement: {decision['reasoning']}\n"
        explanation += f"Intention détectée: {decision['intent']}\n\n"
        
        if decision['search_type'] == 'by_regulation':
            explanation += f"Recherche ciblée dans la réglementation: {decision['regulation_code']}\n"
            explanation += f"Requête nettoyée: '{decision['query']}'\n"
            
        elif decision['search_type'] == 'full_regulation':
            explanation += f"Récupération complète de la réglementation: {decision['regulation_code']}\n"
            
        elif decision['search_type'] == 'comparative':
            explanation += f"Comparaison entre les réglementations: {', '.join(decision['regulations'])}\n"
            
        elif decision['search_type'] == 'summary_request':
            explanation += f"Génération de résumé intelligent pour la réglementation: {decision['regulation_code']}\n"
            
        else:
            explanation += "Recherche générale dans toutes les réglementations\n"
        
        return explanation

# Exemple d'utilisation et tests
if __name__ == "__main__":
    # Test du service
    service = IntelligentRoutingService(llm_provider="ollama", model_name="llama3.2")
    
    # Tests de différents types de requêtes
    test_queries = [
        "Quelles sont les exigences de la R107 pour les sorties de secours?",
        "Résumé complet de la réglementation ECE R46",
        "Résume-moi la réglementation R107",
        "Différence entre R107 et R46 pour les rétroviseurs",
        "Comment tester la résistance des matériaux?",
        "Selon la R107, quelles sont les dimensions minimales?",
        "Toutes les exigences de sécurité pour les autobus",
        "Peux-tu me faire un overview de la norme R107?",
        "Comparaison entre les exigences R46 et R107 pour la visibilité",
        "Synthèse de ECE R46",
        "Resume moi la reglementation R107"
    ]
    
    for query in test_queries:
        # Sortie console de test désactivée
        pass