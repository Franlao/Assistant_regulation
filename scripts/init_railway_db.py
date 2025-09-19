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

        # Debug paths
        abs_chroma_path = os.path.abspath(chroma_path)
        print(f"🔍 DEBUG: Chemin ChromaDB relatif: {chroma_path}")
        print(f"🔍 DEBUG: Chemin ChromaDB absolu: {abs_chroma_path}")
        print(f"🔍 DEBUG: Working directory: {os.getcwd()}")
        print(f"🔍 DEBUG: Contenu du répertoire DB: {os.listdir('DB') if os.path.exists('DB') else 'N/A'}")

        client = chromadb.PersistentClient(path=chroma_path)
        collections = client.list_collections()

        if not collections:
            print("Aucune collection ChromaDB trouvée - base de données vide")

            # Test avec chemin absolu au cas où
            print("🔍 DEBUG: Test avec chemin absolu...")
            try:
                abs_client = chromadb.PersistentClient(path=abs_chroma_path)
                abs_collections = abs_client.list_collections()
                if abs_collections:
                    print(f"✅ Collections trouvées avec chemin absolu: {len(abs_collections)}")
                    return True
                else:
                    print("❌ Aucune collection même avec chemin absolu")
            except Exception as e:
                print(f"❌ Erreur avec chemin absolu: {e}")

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
    print("🚀 Initialisation de la base de données Railway - Version PERSISTENCE TEST 19/09/2025...")
    print("🔍 Test de persistance en cours - vérification des données existantes...")

    # Créer les répertoires
    ensure_directories()

    # Vérifier l'état de la base de données
    db_healthy = check_database_status()

    if not db_healthy:
        print("❌ PERSISTENCE TEST: Base de données vide après redéploiement")
        print("💡 Astuce: Copiez vos fichiers PDF dans le dossier Data/ et relancez le traitement")
    else:
        print("✅ PERSISTENCE TEST: Données trouvées - persistance fonctionnelle !")
        print("🎉 Les volumes Railway fonctionnent correctement avec la config unifiée")
