"""
Exemple de Migration vers LangGraph
===================================

Exemple complet montrant comment migrer du ModularOrchestrator
vers LangGraphOrchestrator avec compatibilité totale.
"""

import os
import sys
import time

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des orchestrateurs
from assistant_regulation.planning.langgraph.orchestrator import LangGraphOrchestrator
from assistant_regulation.planning.langgraph.compatibility_adapter import LangGraphCompatibilityAdapter


def example_migration_progressive():
    """
    Exemple de migration progressive utilisant l'adaptateur de compatibilité.
    """
    print("=== Exemple de Migration Progressive ===\\n")
    
    # 1. Utilisation de l'adaptateur de compatibilité
    print("1. Initialisation avec adaptateur de compatibilité...")
    
    # L'adaptateur permet d'utiliser LangGraph avec fallback vers ModularOrchestrator
    orchestrator = LangGraphCompatibilityAdapter(
        llm_provider="ollama",
        model_name="llama3.2",
        enable_verification=True,
        workflow_type="full",  # LangGraph workflow
        fallback_to_modular=True  # Fallback si LangGraph échoue
    )
    
    # Vérifier le statut des orchestrateurs
    status = orchestrator.get_orchestrator_status()
    print(f"Statut: {status}\\n")
    
    # 2. Test de requête - Interface identique au ModularOrchestrator
    print("2. Test de requête avec interface compatible...")
    
    query = "Quels sont les exigences pour les systèmes de freinage d'urgence ?"
    
    try:
        result = orchestrator.process_query(
            query=query,
            use_images=True,
            use_tables=True,
            top_k=5,
            use_conversation_context=True,
            use_advanced_routing=True
        )
        
        print(f"Réponse générée par: {result['metadata'].get('orchestrator', 'unknown')}")
        print(f"Succès: {result['success']}")
        print(f"Longueur réponse: {len(result['answer'])} caractères")
        print(f"Nombre de sources: {len(result['sources'])}")
        print(f"Temps de traitement: {result['metadata'].get('processing_time', 0):.2f}s\\n")
        
    except Exception as e:
        print(f"Erreur: {e}\\n")


def example_direct_langgraph():
    """
    Exemple d'utilisation directe de LangGraphOrchestrator.
    """
    print("=== Exemple d'Utilisation Directe de LangGraph ===\\n")
    
    # 1. Initialisation directe de LangGraph
    print("1. Initialisation de LangGraphOrchestrator...")
    
    try:
        orchestrator = LangGraphOrchestrator(
            llm_provider="ollama",
            model_name="llama3.2",
            enable_verification=True,
            workflow_type="full",  # Workflow complet
            enable_debug=False
        )
        
        print("LangGraphOrchestrator initialisé avec succès\\n")
        
        # 2. Informations sur l'architecture
        print("2. Informations sur l'architecture...")
        stats = orchestrator.get_agent_statistics()
        print(f"Type de workflow: {stats['workflow_type']}")
        print(f"Agents initialisés: {stats['agents_initialized']}")
        print(f"Services actifs: {stats['services_status']}\\n")
        
        # 3. Test de routage
        print("3. Test d'analyse de routage...")
        query = "Comment tester la résistance des matériaux selon R046 ?"
        
        routing_info = orchestrator.get_routing_info(query)
        print(f"Plan d'exécution: {routing_info}")
        
        explanation = orchestrator.explain_routing_decision(query)
        print(f"Explication: {explanation}\\n")
        
        # 4. Traitement de requête complète
        print("4. Traitement de requête complète...")
        
        result = orchestrator.process_query(
            query=query,
            use_images=True,
            use_tables=True,
            top_k=3
        )
        
        print(f"Réponse: {result['answer'][:200]}...")
        print(f"Sources trouvées: {len(result['sources'])}")
        print(f"Images trouvées: {len(result['images'])}")
        print(f"Tableaux trouvés: {len(result['tables'])}")
        
        # Métadonnées de traitement
        metadata = result['metadata']
        print(f"\\nMétadonnées de traitement:")
        print(f"- Temps total: {metadata.get('processing_time', 0):.2f}s")
        print(f"- Trace d'agents: {metadata.get('agent_trace', [])}")
        print(f"- Analyse de requête: {metadata.get('query_analysis', {})}")
        
    except ImportError as e:
        print(f"LangGraph non disponible: {e}")
        print("Assurez-vous d'installer: pip install langgraph langchain")
    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")


def example_streaming():
    """
    Exemple de traitement en streaming avec LangGraph.
    """
    print("\\n=== Exemple de Streaming avec LangGraph ===\\n")
    
    try:
        # Utiliser l'adaptateur avec préférence pour LangGraph
        orchestrator = LangGraphCompatibilityAdapter(
            llm_provider="ollama",
            model_name="llama3.2",
            workflow_type="streaming",  # Workflow optimisé pour streaming
            fallback_to_modular=True
        )
        
        query = "Expliquez les procédures de test de sécurité pour les véhicules électriques"
        
        print(f"Streaming pour: {query}\\n")
        
        for event in orchestrator.process_query_stream(query=query, top_k=3):
            print(f"[{event.get('type', 'unknown')}] {event.get('message', event.get('content', str(event)))}")
            
            # Simuler un délai pour voir le streaming
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Erreur streaming: {e}")


def example_comparison():
    """
    Exemple de comparaison entre ModularOrchestrator et LangGraphOrchestrator.
    """
    print("\\n=== Comparaison des Orchestrateurs ===\\n")
    
    # Utiliser l'adaptateur pour faciliter la comparaison
    adapter = LangGraphCompatibilityAdapter(
        llm_provider="ollama",
        model_name="llama3.2",
        fallback_to_modular=True
    )
    
    # Test de comparaison sur une requête
    query = "Quelles sont les normes de sécurité pour les systèmes d'éclairage ?"
    
    print(f"Test comparatif pour: {query}\\n")
    
    try:
        comparison_results = adapter.run_comparison_test(query)
        
        print("Résultats comparatifs:")
        for orchestrator_name, results in comparison_results["results"].items():
            print(f"\\n{orchestrator_name.upper()}:")
            if results.get("success"):
                print(f"  ✓ Succès")
                print(f"  ⏱️  Temps: {results['processing_time']:.2f}s")
                print(f"  📝 Longueur réponse: {results['answer_length']} caractères")
                print(f"  📚 Sources: {results['sources_count']}")
            else:
                print(f"  ❌ Échec: {results.get('error')}")
        
    except Exception as e:
        print(f"Erreur lors de la comparaison: {e}")


def example_workflow_switching():
    """
    Exemple de changement dynamique de workflow.
    """
    print("\\n=== Changement Dynamique de Workflow ===\\n")
    
    try:
        orchestrator = LangGraphOrchestrator(
            llm_provider="ollama",
            model_name="llama3.2",
            workflow_type="full"
        )
        
        query = "Test de workflow switching"
        
        # Test avec workflow full
        print("1. Workflow 'full':")
        stats1 = orchestrator.get_agent_statistics()
        print(f"   Type actuel: {stats1['workflow_type']}")
        
        # Changer vers workflow simple
        print("\\n2. Changement vers workflow 'simple':")
        orchestrator.switch_workflow("simple")
        stats2 = orchestrator.get_agent_statistics()
        print(f"   Nouveau type: {stats2['workflow_type']}")
        
        # Changer vers workflow debug
        print("\\n3. Changement vers workflow 'debug':")
        orchestrator.switch_workflow("debug")
        stats3 = orchestrator.get_agent_statistics()
        print(f"   Type debug: {stats3['workflow_type']}")
        
        print("\\nChangements de workflow réussis !")
        
    except Exception as e:
        print(f"Erreur lors du changement de workflow: {e}")


def main():
    """
    Fonction principale exécutant tous les exemples.
    """
    print("🚀 Exemples de Migration vers LangGraph\\n")
    print("=" * 60)
    
    # 1. Migration progressive
    example_migration_progressive()
    
    # 2. Utilisation directe
    example_direct_langgraph()
    
    # 3. Streaming
    example_streaming()
    
    # 4. Comparaison
    example_comparison()
    
    # 5. Changement de workflow
    example_workflow_switching()
    
    print("\\n" + "=" * 60)
    print("✅ Tous les exemples terminés!")


if __name__ == "__main__":
    main()