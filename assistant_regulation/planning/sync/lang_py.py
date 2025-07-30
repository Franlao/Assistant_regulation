import os
import requests
from langdetect import detect
from deep_translator import GoogleTranslator, MyMemoryTranslator
import urllib3
import ssl
from functools import lru_cache

class LanguageHandler:
    def __init__(self):
        """Initialize the language handler with SSL verification disabled"""
        # Désactiver les avertissements SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
    def handle_query_language(self, query: str) -> str:
        """
        Détecte la langue et traduit en anglais si nécessaire, avec gestion des erreurs SSL.
        
        Args:
            query (str): Question à traiter
            
        Returns:
            str: Question en anglais (traduite ou originale)
        """
        try:
            # Détection de la langue
            lang = detect(query)
            
            # Si déjà en anglais, retourner tel quel
            if lang == 'en':
                return query
            
            # Premier essai avec MyMemoryTranslator
            try:
                translator = MyMemoryTranslator(source=lang, target='en')
                return translator.translate(query)
            except:
                pass
            
            # Deuxième essai avec GoogleTranslator et SSL désactivé
            try:
                session = requests.Session()
                session.verify = False  # Désactive la vérification SSL
                
                translator = GoogleTranslator(
                    source=lang,
                    target='en',
                    proxies=None
                )
                translator.session = session
                return translator.translate(query)
            except:
                pass
            
            # Dernier essai avec méthode alternative
            try:
                # URL de l'API alternative
                url = f"https://translate.googleapis.com/translate_a/single"
                
                params = {
                    "client": "gtx",
                    "sl": lang,
                    "tl": "en",
                    "dt": "t",
                    "q": query
                }
                
                response = requests.get(
                    url,
                    params=params,
                    verify=False,  # Désactive la vérification SSL
                    timeout=5
                )
                
                if response.status_code == 200:
                    try:
                        return response.json()[0][0][0]
                    except:
                        pass
            except:
                pass
            
            # Si toutes les tentatives échouent, retourner la question originale
            print("Échec de la traduction - retour du texte original")
            return query
            
        except Exception as e:
            print(f"Erreur lors du traitement de la langue: {str(e)}")
            return query

# On applique un LRU cache (taille 512) pour mémoïser les traductions identiques
@lru_cache(maxsize=512)
def translate_query(query: str) -> str:
    """
    Fonction utilitaire pour traduire une question.
    
    Args:
        query (str): Question à traduire
        
    Returns:
        str: Question traduite ou originale si échec
    """
    handler = LanguageHandler()
    return handler.handle_query_language(query)