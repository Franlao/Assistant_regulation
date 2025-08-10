#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de routage des connaissances - détermine si une question nécessite 
la base vectorielle ou peut être répondue par les connaissances générales du LLM.
"""

import json
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
import ollama
from mistralai import Mistral, UserMessage

# Configuration du logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class KnowledgeSource(Enum):
    """Sources de connaissances disponibles"""
    VECTOR_DB = "vector_db"      # Base vectorielle (réglementations)
    LLM_GENERAL = "llm_general"  # Connaissances générales du LLM
    HYBRID = "hybrid"            # Combinaison des deux

@dataclass
class KnowledgeDecision:
    """Résultat de la décision de routage des connaissances"""
    knowledge_source: KnowledgeSource
    confidence_score: float
    reasoning: str
    domain_detected: str
    requires_regulations: bool
    suggested_approach: str

class KnowledgeRoutingService:
    """
    Service de routage intelligent des connaissances.
    Détermine si une question nécessite la base vectorielle ou les connaissances générales.
    """
    
    def __init__(self, llm_provider: str = "mistral", model_name: str = "mistral-medium"):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.mistral_client = None
        
        if llm_provider == "mistral":
            try:
                import os
                api_key = os.getenv("MISTRAL_API_KEY")
                if api_key:
                    self.mistral_client = Mistral(api_key=api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Mistral: {e}")
                self.llm_provider = "ollama"
    
    def _get_knowledge_routing_prompt(self, query: str) -> str:
        """Construit le prompt pour déterminer la source de connaissances"""
        
        return f"""Tu es un expert en analyse de questions pour un assistant spécialisé dans les réglementations automobiles UN/ECE.

QUESTION UTILISATEUR: "{query}"

Ta mission est de déterminer si cette question nécessite d'accéder à la base de données vectorielle des réglementations automobiles, ou si elle peut être répondue avec tes connaissances générales.

DOMAINES NÉCESSITANT LA BASE VECTORIELLE:
- Réglementations automobiles UN/ECE (R46, R107, R127, etc.)
- Normes de transport spécifiques
- Exigences techniques précises des véhicules
- Procédures de test et certification automobile
- Dimensions, tolérances, spécifications exactes
- Citations de documents réglementaires
- Comparaisons entre réglementations spécifiques
- Questions sur l'OBLIGATION d'équipements (feux, rétroviseurs, etc.)
- Spécifications techniques de POSITION, HAUTEUR, DISTANCE
- Normes de SÉCURITÉ spécifiques aux véhicules
- Exigences pour PMR (personnes à mobilité réduite)
- Calculs réglementaires (nombre de passagers, issues de secours)
- Dispositions réglementaires spécifiques
- Questions techniques avec des valeurs NUMÉRIQUES précises

DOMAINES POUR CONNAISSANCES GÉNÉRALES:
- Questions très générales sur l'automobile
- Concepts de base en ingénierie
- Histoire de l'automobile
- Questions de culture générale
- Mathématiques, physique générale
- Explications de concepts (non spécifiques aux réglementations)
- Questions personnelles ou hors sujet

ANALYSE REQUISE:
1. Identifie le domaine de la question
2. Détermine si des informations spécifiques des réglementations sont nécessaires
3. Évalue si tes connaissances générales suffisent
4. Choisis la meilleure source de connaissances

RÉPONDS UNIQUEMENT EN JSON:
{{
    "knowledge_source": "vector_db|llm_general|hybrid",
    "confidence_score": 0.85,
    "reasoning": "explication de ton choix",
    "domain_detected": "domaine identifié",
    "requires_regulations": true/false,
    "suggested_approach": "approche recommandée"
}}

EXEMPLES:
- "Quelles sont les exigences R107 pour les sorties de secours?" → vector_db (réglementation spécifique)
- "Les faux anti-brouillard sont-ils obligatoires?" → vector_db (question d'obligation)
- "A quelle hauteur doit-on placer un rétroviseur?" → vector_db (spécification technique)
- "Distance entre deux sièges passagers?" → vector_db (dimension réglementaire)
- "Nombre d'issues de secours pour 116 passagers?" → vector_db (calcul réglementaire)
- "Dispositions réglementaires pour fauteuils roulants?" → vector_db (PMR)
- "Comment fonctionne un moteur?" → llm_general (concept général)
- "Qu'est-ce qu'un rétroviseur?" → llm_general (concept de base)
- "Histoire de l'automobile" → llm_general (culture générale)

ANALYSE:"""

    def _call_llm(self, prompt: str) -> str:
        """Appelle le LLM pour l'analyse des connaissances"""
        
        try:
            if self.llm_provider == "mistral" and self.mistral_client:
                messages = [UserMessage(content=prompt)]
                response = self.mistral_client.chat.complete(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=300
                )
                return response.choices[0].message.content
            else:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.1,
                        "num_predict": 300
                    }
                )
                return response['message']['content']
                
        except Exception as e:
            logger.error(f"Erreur lors de l'appel LLM: {e}")
            return self._fallback_knowledge_analysis(prompt)
    
    def _fallback_knowledge_analysis(self, prompt: str) -> str:
        """Analyse de fallback en cas d'erreur LLM"""
        logger.warning("Utilisation du fallback d'analyse des connaissances")
        
        # Extraire la requête du prompt
        query_start = prompt.find('QUESTION UTILISATEUR: "') + 23
        query_end = prompt.find('"', query_start)
        query = prompt[query_start:query_end] if query_start > 22 else ""
        
        query_lower = query.lower()
        
        # Mots-clés nécessitant la base vectorielle
        regulation_keywords = [
            # Codes réglementaires
            'r107', 'r46', 'r127', 'r128', 'ece', 'un/ece',
            # Termes réglementaires
            'réglementation', 'norme', 'exigence', 'spécification',
            'dimension', 'test', 'certification', 'procédure',
            'selon', 'conformément', 'directive',
            # Questions d'obligation
            'obligatoire', 'obligation', 'exigé', 'requis', 'doit',
            'interdit', 'autorisé', 'permis', 'conforme',
            # Spécifications techniques
            'hauteur', 'distance', 'position', 'taille', 'nombre',
            'minimum', 'maximum', 'au moins', 'au plus',
            # Éléments techniques spécifiques
            'anti-brouillard', 'rétroviseur', 'siège', 'passager',
            'issue de secours', 'feu stop', 'fauteuil roulant',
            'pmr', 'mobilité réduite', 'sécurité',
            # Calculs réglementaires
            'calculer', 'combien', 'quel nombre', 'quelle quantité'
        ]
        
        # Mots-clés pour connaissances générales
        general_keywords = [
            'comment', 'pourquoi', 'qu\'est-ce', 'définition',
            'histoire', 'principe', 'fonctionnement', 'concept'
        ]
        
        # Analyser la présence de mots-clés
        has_regulation_keywords = any(keyword in query_lower for keyword in regulation_keywords)
        has_general_keywords = any(keyword in query_lower for keyword in general_keywords)
        
        # Décision
        if has_regulation_keywords and not has_general_keywords:
            knowledge_source = "vector_db"
            confidence = 0.8
        elif has_general_keywords and not has_regulation_keywords:
            knowledge_source = "llm_general"
            confidence = 0.7
        elif has_regulation_keywords and has_general_keywords:
            knowledge_source = "hybrid"
            confidence = 0.6
        else:
            knowledge_source = "llm_general"
            confidence = 0.5
        
        return json.dumps({
            "knowledge_source": knowledge_source,
            "confidence_score": confidence,
            "reasoning": "Analyse de fallback basée sur mots-clés",
            "domain_detected": "Détection automatique",
            "requires_regulations": has_regulation_keywords,
            "suggested_approach": "Approche par défaut"
        })
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse la réponse du LLM pour l'analyse des connaissances avec robustesse améliorée"""
        try:
            response = response.strip()
            
            # Tentative 1: Chercher le JSON dans la réponse
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                logger.info("JSON parsé avec succès")
                return parsed_data
                
            # Tentative 2: Essayer de parser la réponse complète comme JSON
            try:
                parsed_data = json.loads(response)
                logger.info("Réponse complète parsée comme JSON")
                return parsed_data
            except:
                pass
                
            # Tentative 3: Utiliser le fallback d'analyse par mots-clés
            logger.warning("Pas de JSON trouvé, utilisation du fallback")
            fallback_json = self._fallback_knowledge_analysis(f'QUESTION UTILISATEUR: "{response}"')
            return json.loads(fallback_json)
                
        except Exception as e:
            logger.error(f"Erreur parsing LLM response: {e}")
            logger.debug(f"Réponse LLM problématique: {response[:200]}...")
            
            # Fallback final vers une structure par défaut
            return {
                "knowledge_source": "llm_general",
                "confidence_score": 0.3,
                "reasoning": f"Erreur de parsing LLM: {str(e)}",
                "domain_detected": "Indéterminé", 
                "requires_regulations": False,
                "suggested_approach": "Réponse générale par défaut"
            }
    
    def _validate_knowledge_data(self, data: Dict, query: str) -> Dict:
        """Valide et normalise les données d'analyse des connaissances"""
        
        # Valider knowledge_source
        valid_sources = [source.value for source in KnowledgeSource]
        if data.get("knowledge_source") not in valid_sources:
            data["knowledge_source"] = "llm_general"
        
        # Valider confidence_score
        try:
            confidence = float(data.get("confidence_score", 0.5))
            data["confidence_score"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            data["confidence_score"] = 0.5
        
        # Valider requires_regulations
        if not isinstance(data.get("requires_regulations"), bool):
            data["requires_regulations"] = data["knowledge_source"] == "vector_db"
        
        # Valeurs par défaut pour les champs manquants
        data.setdefault("reasoning", "Analyse automatique")
        data.setdefault("domain_detected", "Général")
        data.setdefault("suggested_approach", "Approche standard")
        
        return data
    
    def analyze_knowledge_needs(self, query: str) -> KnowledgeDecision:
        """
        Analyse une question pour déterminer la source de connaissances optimale.
        
        Args:
            query: La question utilisateur
            
        Returns:
            KnowledgeDecision avec la source recommandée
        """
        logger.info(f"Analyse des besoins de connaissances pour: {query}")
        
        # Construire le prompt
        prompt = self._get_knowledge_routing_prompt(query)
        
        # Appeler le LLM
        llm_response = self._call_llm(prompt)
        
        # Parser la réponse
        analysis_data = self._parse_llm_response(llm_response)
        
        # Valider et normaliser
        analysis_data = self._validate_knowledge_data(analysis_data, query)
        
        # Créer l'objet KnowledgeDecision
        decision = KnowledgeDecision(
            knowledge_source=KnowledgeSource(analysis_data["knowledge_source"]),
            confidence_score=analysis_data["confidence_score"],
            reasoning=analysis_data["reasoning"],
            domain_detected=analysis_data["domain_detected"],
            requires_regulations=analysis_data["requires_regulations"],
            suggested_approach=analysis_data["suggested_approach"]
        )
        
        logger.info(f"Décision: {decision.knowledge_source.value} - Confiance: {decision.confidence_score:.2f}")
        return decision
    
    def get_routing_recommendation(self, query: str) -> Dict:
        """
        Recommandation complète de routage des connaissances.
        
        Args:
            query: La question utilisateur
            
        Returns:
            Dictionnaire avec toutes les informations de routage
        """
        decision = self.analyze_knowledge_needs(query)
        
        recommendation = {
            'query': query,
            'knowledge_source': decision.knowledge_source.value,
            'confidence': decision.confidence_score,
            'reasoning': decision.reasoning,
            'domain': decision.domain_detected,
            'requires_vector_db': decision.requires_regulations,
            'suggested_approach': decision.suggested_approach
        }
        
        # Ajouter des conseils spécifiques
        if decision.knowledge_source == KnowledgeSource.VECTOR_DB:
            recommendation['action'] = 'use_vector_search'
            recommendation['next_step'] = 'Utiliser le service de routage intelligent pour déterminer le type de recherche'
            
        elif decision.knowledge_source == KnowledgeSource.LLM_GENERAL:
            recommendation['action'] = 'use_llm_directly'
            recommendation['next_step'] = 'Répondre directement avec les connaissances générales du LLM'
            
        else:  # HYBRID
            recommendation['action'] = 'use_hybrid_approach'
            recommendation['next_step'] = 'Combiner recherche vectorielle et connaissances générales'
        
        return recommendation
    
    def explain_decision(self, query: str) -> str:
        """
        Explique la décision de routage des connaissances.
        
        Args:
            query: La question utilisateur
            
        Returns:
            Explication textuelle de la décision
        """
        recommendation = self.get_routing_recommendation(query)
        
        explanation = f"Analyse de la question: '{query}'\n\n"
        explanation += f"Source de connaissances recommandée: {recommendation['knowledge_source']}\n"
        explanation += f"Confiance: {recommendation['confidence']:.0%}\n"
        explanation += f"Domaine détecté: {recommendation['domain']}\n"
        explanation += f"Nécessite base vectorielle: {'Oui' if recommendation['requires_vector_db'] else 'Non'}\n"
        explanation += f"Raisonnement: {recommendation['reasoning']}\n\n"
        explanation += f"Action recommandée: {recommendation['action']}\n"
        explanation += f"Prochaine étape: {recommendation['next_step']}\n"
        
        return explanation

# Exemple d'utilisation et tests
if __name__ == "__main__":
    # Test du service
    service = KnowledgeRoutingService(llm_provider="ollama", model_name="llama3.2")
    
    # Tests de différents types de questions
    test_queries = [
        # Questions nécessitant la base vectorielle
        "Quelles sont les exigences de la R107 pour les sorties de secours?",
        "Dimensions exactes selon la réglementation R46?",
        "Différence entre R107 et R46 pour les rétroviseurs?",
        "Procédure de test selon ECE R46",
        
        # Questions pour connaissances générales
        "Comment fonctionne un moteur à combustion?",
        "Qu'est-ce qu'un rétroviseur?",
        "Histoire de l'automobile",
        "Principe de fonctionnement des freins",
        "Bonjour, comment allez-vous?",
        
        # Questions mixtes/ambiguës
        "Qu'est-ce qu'une réglementation automobile?",
        "Pourquoi les rétroviseurs sont-ils obligatoires?",
        "Comment tester la sécurité d'un véhicule?"
    ]
    
    for query in test_queries:
        # Sortie console de test désactivée
        pass