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
    directories = [
        "DB/vectorstores/text_chunks",
        "DB/vectorstores/image_chunks",
        "DB/vectorstores/table_chunks",
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
        client = chromadb.PersistentClient(path="DB/chroma_db")
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
    print("🚀 Initialisation de la base de données Railway - Version TEST PERSISTANCE 19/09/2025...")

    # Créer les répertoires
    ensure_directories()
