"""
Module Database - Gestion de la base de données ChromaDB pour l'Assistant Réglementaire

Ce module fournit des outils complets pour la gestion de la base de données vectorielle
ChromaDB utilisée par l'Assistant Réglementaire Automotive.

Fonctionnalités disponibles:
- Ingestion de documents PDF depuis un dossier
- Résumé et statistiques de la base de données  
- Recherche spécifique par code de réglementation
- Nettoyage et vidage de la base de données
- Listage des réglementations disponibles
- Upload de nouveaux PDFs dans une base existante

Usage:
    from assistant_regulation.planning.Database import (
        PDFIngestionManager,
        DatabaseSummaryManager,
        RegulationSearchManager,
        DatabaseCleanupManager,
        RegulationListManager,
        PDFUploadManager
    )
"""

# Import des classes principales
from .pdf_ingestion import PDFIngestionManager
from .database_summary import DatabaseSummaryManager
from .regulation_search import RegulationSearchManager
from .database_cleanup import DatabaseCleanupManager
from .list_regulations import RegulationListManager
from .pdf_upload import PDFUploadManager

# Version du module
__version__ = "1.0.0"

# Exportation des classes principales
__all__ = [
    "PDFIngestionManager",
    "DatabaseSummaryManager", 
    "RegulationSearchManager",
    "DatabaseCleanupManager",
    "RegulationListManager",
    "PDFUploadManager",
    "check_database_health"
]


def get_database_manager(manager_type: str):
    """
    Factory function pour obtenir un gestionnaire de base de données
    
    Args:
        manager_type: Type de gestionnaire ('ingestion', 'summary', 'search', 
                     'cleanup', 'list', 'upload')
    
    Returns:
        Instance du gestionnaire demandé
        
    Raises:
        ValueError: Si le type de gestionnaire est invalide
    """
    managers = {
        'ingestion': PDFIngestionManager,
        'summary': DatabaseSummaryManager,
        'search': RegulationSearchManager,
        'cleanup': DatabaseCleanupManager,
        'list': RegulationListManager,
        'upload': PDFUploadManager
    }
    
    if manager_type not in managers:
        raise ValueError(f"Type de gestionnaire invalide: {manager_type}. "
                        f"Types disponibles: {list(managers.keys())}")
    
    return managers[manager_type]()


def get_available_operations():
    """
    Retourne la liste des opérations disponibles
    
    Returns:
        Dict avec les opérations et leurs descriptions
    """
    return {
        "ingestion": {
            "description": "Ingestion initiale de documents PDF dans ChromaDB",
            "script": "pdf_ingestion.py",
            "class": "PDFIngestionManager",
            "operations": [
                "Traitement d'un dossier complet de PDFs",
                "Traitement d'un seul PDF",
                "Traitement parallèle ou séquentiel",
                "Vérification post-ingestion"
            ]
        },
        "summary": {
            "description": "Résumé et statistiques de la base de données",
            "script": "database_summary.py", 
            "class": "DatabaseSummaryManager",
            "operations": [
                "Statistiques des collections",
                "Analyse des documents et réglementations",
                "Export du résumé en JSON",
                "Affichage détaillé ou compact"
            ]
        },
        "search": {
            "description": "Recherche spécifique par code de réglementation",
            "script": "regulation_search.py",
            "class": "RegulationSearchManager", 
            "operations": [
                "Recherche complète d'une réglementation",
                "Résumé rapide d'une réglementation",
                "Export des données en JSON/CSV/TXT",
                "Analyse du contenu (exigences, définitions, etc.)"
            ]
        },
        "cleanup": {
            "description": "Nettoyage et vidage de la base de données",
            "script": "database_cleanup.py",
            "class": "DatabaseCleanupManager",
            "operations": [
                "Vidage d'une collection spécifique",
                "Vidage de toutes les collections", 
                "Suppression physique des fichiers DB",
                "Nettoyage sélectif par réglementation",
                "Nettoyage des fichiers cache"
            ]
        },
        "list": {
            "description": "Listage des réglementations disponibles",
            "script": "list_regulations.py",
            "class": "RegulationListManager",
            "operations": [
                "Liste complète des réglementations",
                "Affichage détaillé avec statistiques",
                "Filtrage par critères (chunks, images, tables)",
                "Export en JSON/CSV/TXT"
            ]
        },
        "upload": {
            "description": "Upload de nouveaux PDFs dans base existante",
            "script": "pdf_upload.py", 
            "class": "PDFUploadManager",
            "operations": [
                "Upload d'un seul PDF",
                "Upload multiple depuis dossier",
                "Copie automatique dans dossier Data",
                "Vérification de l'état de la base existante"
            ]
        }
    }


def print_module_info():
    """Affiche les informations sur le module Database"""
    print("=" * 70)
    print("    MODULE DATABASE - ASSISTANT RÉGLEMENTAIRE")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("\nGestionnaires disponibles:")
    
    operations = get_available_operations()
    
    for op_type, info in operations.items():
        print(f"\n🔧 {op_type.upper()}:")
        print(f"   Description: {info['description']}")
        print(f"   Script: {info['script']}")
        print(f"   Classe: {info['class']}")
        print("   Opérations:")
        for operation in info['operations']:
            print(f"     • {operation}")
    
    print("\n" + "=" * 70)
    print("Usage:")
    print("  python -m assistant_regulation.planning.Database.<script_name> --help")
    print("  ou")
    print("  from assistant_regulation.planning.Database import <ManagerClass>")
    print("=" * 70)


# Fonction utilitaire pour vérifier l'état général de la base
def check_database_health():
    """
    Vérifie l'état général de la base de données
    
    Returns:
        Dict avec les informations de santé de la DB
    """
    try:
        summary_manager = DatabaseSummaryManager()
        summary = summary_manager.get_complete_summary()
        
        health_status = {
            "healthy": True,
            "collections_status": {},
            "total_documents": 0,
            "total_regulations": 0,
            "issues": []
        }
        
        # Vérifier les collections
        collections = summary.get("collections", {})
        for col_type, col_info in collections.items():
            if isinstance(col_info, dict):
                exists = col_info.get("exists", False)
                count = col_info.get("count", 0)
                
                health_status["collections_status"][col_type] = {
                    "exists": exists,
                    "count": count,
                    "healthy": exists and count > 0
                }
                
                if not exists:
                    health_status["issues"].append(f"Collection {col_type} n'existe pas")
                elif count == 0:
                    health_status["issues"].append(f"Collection {col_type} est vide")
                else:
                    health_status["total_documents"] += count
        
        # Vérifier les réglementations
        regulations = summary.get("regulations", {})
        health_status["total_regulations"] = regulations.get("total_regulations", 0)
        
        if health_status["total_regulations"] == 0:
            health_status["issues"].append("Aucune réglementation trouvée")
        
        # Déterminer la santé générale
        if health_status["total_documents"] == 0:
            health_status["healthy"] = False
            health_status["issues"].append("Base de données vide")
        
        return health_status
        
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "issues": [f"Erreur lors de la vérification: {e}"]
        }