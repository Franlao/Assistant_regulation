#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de routage maître - combine le pré-filtrage des connaissances 
et le routage intelligent des recherches.
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .knowledge_routing_service import KnowledgeRoutingService, KnowledgeSource
from .intelligent_routing_service import IntelligentRoutingService

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseStrategy(Enum):
    """Stratégies de réponse disponibles"""
    DIRECT_LLM = "direct_llm"           # Réponse directe du LLM
    VECTOR_SEARCH = "vector_search"     # Recherche vectorielle
    HYBRID_RESPONSE = "hybrid_response" # Combinaison des deux

@dataclass
class MasterRoutingDecision:
    """Décision de routage maître"""
    response_strategy: ResponseStrategy
    knowledge_source: str
    search_config: Optional[Dict]
    confidence_score: float
    reasoning: str
    next_actions: Dict

class MasterRoutingService:
    """
    Service de routage maître qui combine :
    1. Pré-filtrage des connaissances (base vectorielle vs connaissances générales)
    2. Routage intelligent des recherches (si base vectorielle nécessaire)
    """
    
    def __init__(self, llm_provider: str = "ollama", model_name: str = "llama3.2"):
        # Initialiser les services sous-jacents
        self.knowledge_router = KnowledgeRoutingService(llm_provider, model_name)
        self.intelligent_router = IntelligentRoutingService(llm_provider, model_name)
    
    def route_query(self, query: str) -> MasterRoutingDecision:
        """
        Route une requête utilisateur vers la stratégie optimale.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            MasterRoutingDecision avec la stratégie complète
        """
        logger.info(f"Routage maître pour: {query}")
        
        # Étape 1: Analyser les besoins de connaissances
        knowledge_decision = self.knowledge_router.analyze_knowledge_needs(query)
        
        logger.info(f"Pré-filtrage: {knowledge_decision.knowledge_source.value} "
                   f"(confiance: {knowledge_decision.confidence_score:.2f})")
        
        # Étape 2: Déterminer la stratégie selon le pré-filtrage
        if knowledge_decision.knowledge_source == KnowledgeSource.LLM_GENERAL:
            # Réponse directe du LLM
            return self._create_direct_llm_decision(query, knowledge_decision)
            
        elif knowledge_decision.knowledge_source == KnowledgeSource.VECTOR_DB:
            # Routage intelligent pour la recherche vectorielle
            return self._create_vector_search_decision(query, knowledge_decision)
            
        else:  # HYBRID
            # Approche hybride
            return self._create_hybrid_decision(query, knowledge_decision)
    
    def _create_direct_llm_decision(self, query: str, knowledge_decision) -> MasterRoutingDecision:
        """Créer une décision de réponse directe du LLM"""
        
        return MasterRoutingDecision(
            response_strategy=ResponseStrategy.DIRECT_LLM,
            knowledge_source="llm_general",
            search_config=None,
            confidence_score=knowledge_decision.confidence_score,
            reasoning=f"Question générale détectée: {knowledge_decision.reasoning}",
            next_actions={
                'action': 'respond_directly',
                'method': 'llm_chat',
                'params': {
                    'query': query,
                    'context': 'general_knowledge'
                },
                'prompt_type': 'general_assistant'
            }
        )
    
    def _create_vector_search_decision(self, query: str, knowledge_decision) -> MasterRoutingDecision:
        """Créer une décision de recherche vectorielle"""
        
        # Utiliser le routage intelligent pour déterminer le type de recherche
        search_decision = self.intelligent_router.get_routing_decision(query)
        
        return MasterRoutingDecision(
            response_strategy=ResponseStrategy.VECTOR_SEARCH,
            knowledge_source="vector_db",
            search_config=search_decision,
            confidence_score=min(knowledge_decision.confidence_score, search_decision['confidence']),
            reasoning=f"Réglementation détectée: {knowledge_decision.reasoning}. "
                     f"Type de recherche: {search_decision['reasoning']}",
            next_actions={
                'action': 'vector_search',
                'method': search_decision['method'],
                'params': search_decision['params'],
                'search_type': search_decision['search_type']
            }
        )
    
    def _create_hybrid_decision(self, query: str, knowledge_decision) -> MasterRoutingDecision:
        """Créer une décision hybride"""
        
        # Analyser aussi avec le routage intelligent
        search_decision = self.intelligent_router.get_routing_decision(query)
        
        return MasterRoutingDecision(
            response_strategy=ResponseStrategy.HYBRID_RESPONSE,
            knowledge_source="hybrid",
            search_config=search_decision,
            confidence_score=knowledge_decision.confidence_score,
            reasoning=f"Question mixte: {knowledge_decision.reasoning}",
            next_actions={
                'action': 'hybrid_approach',
                'vector_search': {
                    'method': search_decision['method'],
                    'params': search_decision['params']
                },
                'llm_response': {
                    'method': 'llm_chat',
                    'params': {'query': query, 'context': 'general_knowledge'}
                },
                'combination_strategy': 'enrich_llm_with_vector_results'
            }
        )
    
    def explain_routing_decision(self, query: str) -> str:
        """
        Explique la décision de routage maître de manière détaillée.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Explication complète de la décision
        """
        decision = self.route_query(query)
        
        explanation = f"=== DÉCISION DE ROUTAGE MAÎTRE ===\n\n"
        explanation += f"Requête: '{query}'\n\n"
        
        explanation += f"ÉTAPE 1 - PRÉ-FILTRAGE DES CONNAISSANCES:\n"
        explanation += f"Source recommandée: {decision.knowledge_source}\n"
        explanation += f"Confiance globale: {decision.confidence_score:.0%}\n"
        explanation += f"Raisonnement: {decision.reasoning}\n\n"
        
        explanation += f"ÉTAPE 2 - STRATÉGIE DE RÉPONSE:\n"
        explanation += f"Stratégie sélectionnée: {decision.response_strategy.value}\n\n"
        
        if decision.response_strategy == ResponseStrategy.DIRECT_LLM:
            explanation += f"ACTION: Réponse directe du LLM\n"
            explanation += f"Méthode: {decision.next_actions['method']}\n"
            explanation += f"Type de prompt: {decision.next_actions['prompt_type']}\n"
            
        elif decision.response_strategy == ResponseStrategy.VECTOR_SEARCH:
            explanation += f"ACTION: Recherche vectorielle\n"
            explanation += f"Type de recherche: {decision.next_actions['search_type']}\n"
            explanation += f"Méthode: {decision.next_actions['method']}\n"
            explanation += f"Paramètres: {decision.next_actions['params']}\n"
            
        else:  # HYBRID
            explanation += f"ACTION: Approche hybride\n"
            explanation += f"Recherche vectorielle: {decision.next_actions['vector_search']['method']}\n"
            explanation += f"Réponse LLM: {decision.next_actions['llm_response']['method']}\n"
            explanation += f"Stratégie de combinaison: {decision.next_actions['combination_strategy']}\n"
        
        return explanation
    
    def get_execution_plan(self, query: str) -> Dict:
        """
        Retourne un plan d'exécution détaillé pour la requête.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Plan d'exécution structuré
        """
        decision = self.route_query(query)
        
        execution_plan = {
            'query': query,
            'strategy': decision.response_strategy.value,
            'confidence': decision.confidence_score,
            'steps': []
        }
        
        if decision.response_strategy == ResponseStrategy.DIRECT_LLM:
            execution_plan['steps'] = [
                {
                    'step': 1,
                    'action': 'llm_response',
                    'description': 'Générer une réponse directe avec les connaissances générales',
                    'method': decision.next_actions['method'],
                    'params': decision.next_actions['params']
                }
            ]
            
        elif decision.response_strategy == ResponseStrategy.VECTOR_SEARCH:
            execution_plan['steps'] = [
                {
                    'step': 1,
                    'action': 'vector_search',
                    'description': f"Recherche vectorielle de type {decision.next_actions['search_type']}",
                    'method': decision.next_actions['method'],
                    'params': decision.next_actions['params']
                },
                {
                    'step': 2,
                    'action': 'generate_response',
                    'description': 'Générer une réponse basée sur les résultats de recherche',
                    'method': 'llm_chat_with_context',
                    'params': {'query': query, 'context': 'vector_search_results'}
                }
            ]
            
        else:  # HYBRID
            execution_plan['steps'] = [
                {
                    'step': 1,
                    'action': 'parallel_processing',
                    'description': 'Recherche vectorielle et analyse LLM en parallèle',
                    'vector_search': decision.next_actions['vector_search'],
                    'llm_analysis': decision.next_actions['llm_response']
                },
                {
                    'step': 2,
                    'action': 'combine_results',
                    'description': 'Combiner les résultats vectoriels et les connaissances générales',
                    'method': 'hybrid_response_generation',
                    'strategy': decision.next_actions['combination_strategy']
                }
            ]
        
        return execution_plan

# Exemple d'utilisation et tests
if __name__ == "__main__":
    # Test du service maître
    master_router = MasterRoutingService(llm_provider="ollama", model_name="llama3.2")
    
    # Tests de différents types de questions
    test_queries = [
        # Questions pour base vectorielle
        "Quelles sont les exigences de la R107 pour les sorties de secours?",
        "Différence entre R107 et R46 pour les rétroviseurs?",
        "Résumé complet de la réglementation ECE R46",
        
        # Questions pour connaissances générales
        "Comment fonctionne un moteur à combustion?",
        "Qu'est-ce qu'un rétroviseur?",
        "Bonjour, comment allez-vous?",
        
        # Questions potentiellement mixtes
        "Pourquoi les rétroviseurs sont-ils obligatoires?",
        "Comment tester la sécurité d'un véhicule?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*100}")
        print(master_router.explain_routing_decision(query))
        print(f"{'='*100}")
        
        # Afficher aussi le plan d'exécution
        plan = master_router.get_execution_plan(query)
        print(f"\nPLAN D'EXÉCUTION:")
        print(f"Stratégie: {plan['strategy']} (confiance: {plan['confidence']:.0%})")
        for step in plan['steps']:
            print(f"  Étape {step.get('step', '?')}: {step.get('description', step.get('action', 'Action inconnue'))}")
        print(f"\n{'='*100}")