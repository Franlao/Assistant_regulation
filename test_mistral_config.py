#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration de l'API Mistral
"""

import os
import sys
from dotenv import load_dotenv

def test_mistral_connection():
    """Teste la connexion à l'API Mistral"""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    print("🔍 Vérification de la configuration Mistral...")
    
    # Vérifier la clé API
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ MISTRAL_API_KEY non trouvée dans les variables d'environnement")
        print("💡 Ajoutez MISTRAL_API_KEY=votre_clé dans votre fichier .env")
        return False
    
    if not api_key.startswith("mistral-"):
        print(f"⚠️  Format de clé API suspect: {api_key[:10]}...")
        print("💡 Les clés Mistral commencent généralement par 'mistral-'")
    else:
        print(f"✅ Clé API trouvée: {api_key[:15]}...")
    
    # Tester l'import de la bibliothèque
    try:
        from mistralai import Mistral
        print("✅ Bibliothèque mistralai importée avec succès")
    except ImportError:
        print("❌ Bibliothèque mistralai non installée")
        print("💡 Installez avec: pip install mistralai")
        return False
    
    # Tester la connexion
    try:
        client = Mistral(api_key=api_key)
        print("✅ Client Mistral initialisé")
        
        # Test simple avec le modèle par défaut
        model_name = os.getenv("MISTRAL_MODEL", "mistral-small")
        print(f"🧪 Test avec le modèle: {model_name}")
        
        response = client.chat.complete(
            model=model_name,
            messages=[
                {"role": "user", "content": "Dis bonjour en français"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        if hasattr(response, 'choices') and response.choices:
            answer = response.choices[0].message.content.strip()
            print(f"✅ Réponse reçue: {answer}")
            print("🎉 Configuration Mistral opérationnelle!")
            return True
        else:
            print("❌ Réponse invalide de l'API")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("💡 Vérifiez votre clé API et votre connexion internet")
        return False

def test_app_integration():
    """Teste l'intégration avec l'application"""
    
    print("\n🔧 Test d'intégration avec l'application...")
    
    try:
        from assistant_regulation.planning.services.generation_service import GenerationService
        print("✅ Service de génération importé")
        
        # Test avec Mistral
        service = GenerationService(
            llm_provider="mistral",
            model_name=os.getenv("MISTRAL_MODEL", "mistral-small")
        )
        print("✅ Service initialisé avec Mistral")
        
        # Test de génération simple
        response = service.generate_answer(
            query="Qu'est-ce qu'une réglementation automobile ?",
            temperature=0.1,
            max_tokens=100
        )
        
        print(f"✅ Réponse générée: {response[:100]}...")
        print("🎉 Intégration application réussie!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'intégration: {e}")
        return False

def test_config_system():
    """Teste le système de configuration"""
    
    print("\n⚙️ Test du système de configuration...")
    
    try:
        from config import get_config
        
        config = get_config()
        print("✅ Configuration chargée")
        
        print(f"📋 Providers disponibles: {config.llm.available_providers}")
        print(f"📋 Provider par défaut: {config.llm.default_provider}")
        print(f"📋 Modèles Mistral: {config.llm.mistral_models}")
        
        # Forcer Mistral comme provider par défaut
        os.environ['LLM_DEFAULT_PROVIDER'] = 'mistral'
        config = get_config()
        
        if 'mistral' in config.llm.available_providers:
            print("✅ Mistral disponible dans la configuration")
            return True
        else:
            print("❌ Mistral non disponible")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

def main():
    """Fonction principale de test"""
    
    print("🚀 Test de Configuration Mistral pour l'Assistant Réglementaire")
    print("=" * 60)
    
    success = True
    
    # Test 1: Connexion Mistral
    if not test_mistral_connection():
        success = False
    
    # Test 2: Intégration app
    if not test_app_integration():
        success = False
    
    # Test 3: Système de config
    if not test_config_system():
        success = False
    
    print("\n" + "=" * 60)
    
    if success:
        print("🎉 TOUS LES TESTS RÉUSSIS !")
        print("💡 Votre configuration Mistral est opérationnelle")
        print("🚀 Vous pouvez déployer sur Railway")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("💡 Vérifiez la configuration avant le déploiement")
        sys.exit(1)

if __name__ == "__main__":
    main()