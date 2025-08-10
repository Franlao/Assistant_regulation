#!/usr/bin/env python3
"""
Script de validation des requirements.txt
Vérifie que toutes les dépendances sont correctement installées
"""

import sys
import importlib
import subprocess

def test_import(module_name, import_alias=None):
    """Teste l'import d'un module"""
    try:
        if import_alias:
            importlib.import_module(import_alias)
        else:
            importlib.import_module(module_name.replace('-', '_'))
        return True, ""
    except ImportError as e:
        return False, str(e)

def main():
    print("=== Validation des Requirements ===")
    print()
    
    # Modules essentiels avec leurs alias d'import si nécessaire
    essential_modules = {
        'streamlit': None,
        'chromadb': None,
        'sentence-transformers': 'sentence_transformers',
        'chonkie': None,
        'mistralai': None,
        'ollama': None,
        'PyMuPDF': 'fitz',
        'pdfplumber': None,
        'pandas': None,
        'numpy': None,
        'scikit-learn': 'sklearn',
        'joblib': None,
        'pydantic': None,
        'python-dotenv': 'dotenv',
        'aiofiles': None,
        'bcrypt': None,
        'requests': None,
        'httpx': None,
        'torch': None,
        'transformers': None,
        'langchain-core': 'langchain_core',
        'rich': None,
        'typer': None
    }
    
    failed_imports = []
    successful_imports = []
    
    print("Test des imports essentiels:")
    print("-" * 40)
    
    for module, alias in essential_modules.items():
        success, error = test_import(module, alias)
        if success:
            print(f"[OK]  {module}")
            successful_imports.append(module)
        else:
            print(f"[FAIL] {module}: {error}")
            failed_imports.append(module)
    
    print()
    print(f"Résultat: {len(successful_imports)}/{len(essential_modules)} modules OK")
    
    if failed_imports:
        print()
        print("Modules manquants ou en erreur:")
        for module in failed_imports:
            print(f"  - {module}")
        
        print()
        print("Pour installer les modules manquants:")
        print("pip install " + " ".join(failed_imports))
        
        return False
    else:
        print()
        print("Tous les modules essentiels sont disponibles!")
        
        # Test rapide des fonctionnalités clés
        print()
        print("Test des fonctionnalités clés:")
        print("-" * 40)
        
        try:
            from assistant_regulation.planning.services.generation_service import GenerationService
            print("[OK]  Service de génération")
        except Exception as e:
            print(f"[WARN] Service de génération: {e}")
        
        try:
            from config import get_config
            config = get_config()
            print("[OK]  Système de configuration")
        except Exception as e:
            print(f"[WARN] Configuration: {e}")
        
        try:
            import chromadb
            print("[OK]  ChromaDB")
        except Exception as e:
            print(f"[FAIL] ChromaDB: {e}")
        
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)