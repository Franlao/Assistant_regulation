#!/usr/bin/env python3
"""
Script d'initialisation de la base de données pour Railway.
S'assure que les répertoires existent et retraite les documents si nécessaire.
"""

import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def ensure_directories():
    """Créer les répertoires nécessaires s'ils n'existent pas"""
    try:
        # Utiliser la configuration centralisée
        from config.config import get_config
        config = get_config()

        directories = [
            config.database.chroma_db_path,
            "logs",
            config.rag.cache_dir,
            config.memory.memory_dir,
            config.temp_dir
        ]
    except ImportError:
        # Fallback si la config n'est pas disponible
        directories = [
            "DB/chroma_db",
            "logs",
            "joblib_cache",
            ".conversation_memory",
            "temp"
        ]

    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"Créé le répertoire: {directory}")
        else:
            print(f"Répertoire existe: {directory}")

def check_database_status():
    """Vérifier l'état de la base de données ChromaDB"""
    try:
        import chromadb
        # Utiliser la configuration centralisée
        from config.config import get_config
        config = get_config()
        chroma_path = config.database.chroma_db_path
        client = chromadb.PersistentClient(path=chroma_path)
        collections = client.list_collections()

        if not collections:
            print("Aucune collection ChromaDB trouvée - base de données vide")
            return False
        else:
            print(f"{len(collections)} collection(s) ChromaDB trouvée(s):")
            for collection in collections:
                count = collection.count()
                print(f"  - {collection.name}: {count} documents")
            return True

    except Exception as e:
        print(f"Erreur lors de la vérification de ChromaDB: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🚀 Initialisation de la base de données Railway - Version UNIFIED CONFIG 19/09/2025...")

    # Créer les répertoires
    ensure_directories()

    # Vérifier l'état de la base de données
    db_healthy = check_database_status()

    if not db_healthy:
        print("⚠️  Base de données vide - il faudra la repeupler")
        print("💡 Astuce: Copiez vos fichiers PDF dans le dossier Data/ et relancez le traitement")
    else:
        print("✅ Base de données prête - persistance OK")
