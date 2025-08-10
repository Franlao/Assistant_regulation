# src/Planning_pattern/cache.py
import hashlib
import pickle
import os
import time
from typing import Dict, Any, Optional

class ResultCache:
    """Cache pour stocker les résultats de recherche et de vérification"""
    
    def __init__(self, cache_dir: str = ".cache", ttl: int = 86400):
        """
        Initialise le cache avec un répertoire et une durée de vie.
        
        Args:
            cache_dir: Répertoire de stockage du cache
            ttl: Durée de vie en secondes (défaut: 24h)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_key(self, query: str, params: Dict[str, Any]) -> str:
        """Génère une clé de cache basée sur la requête et les paramètres"""
        key_str = query + str(sorted(params.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_file_path(self, key: str) -> str:
        """Obtient le chemin du fichier pour une clé donnée"""
        return os.path.join(self.cache_dir, f"{key}.pkl")
    
    def get(self, query: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Récupère un résultat depuis le cache"""
        key = self._get_key(query, params)
        file_path = self._get_file_path(key)
        
        if not os.path.exists(file_path):
            return None
        
        # Vérifier si le cache est expiré
        if os.path.getmtime(file_path) + self.ttl < time.time():
            os.remove(file_path)
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, query: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Stocke un résultat dans le cache"""
        key = self._get_key(query, params)
        file_path = self._get_file_path(key)
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(result, f)
        except Exception:
            # Erreur silencieuse lors de la mise en cache
            pass