"""
Module de validation des images pour l'affichage
"""
from typing import List, Dict, Any, Optional


class ImageValidator:
    """Classe pour valider et filtrer les images avant affichage"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Vérifie si une URL d'image est valide
        
        Args:
            url: URL à vérifier
            
        Returns:
            True si l'URL est valide, False sinon
        """
        if not isinstance(url, str) or not url.strip():
            return False
        
        url = url.strip()
        valid_prefixes = ('http://', 'https://', 'data:image/')
        
        return any(url.startswith(prefix) for prefix in valid_prefixes)
    
    @staticmethod
    def extract_image_url(img: Dict[str, Any]) -> Optional[str]:
        """
        Extrait l'URL d'une image depuis différents formats possibles
        
        Args:
            img: Dictionnaire contenant les données de l'image
            
        Returns:
            URL de l'image si trouvée, None sinon
        """
        # Essayer d'abord le champ 'url' direct
        url = img.get("url", "")
        
        # Si pas d'URL directe, chercher dans les métadonnées
        if not url and isinstance(img.get("metadata"), dict):
            url = img.get("metadata", {}).get("image_url", "")
        
        return url.strip() if isinstance(url, str) and url.strip() else None
    
    @staticmethod
    def validate_and_filter_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valide et filtre une liste d'images
        
        Args:
            images: Liste des images à valider
            
        Returns:
            Liste des images valides avec URLs normalisées
        """
        valid_images = []
        
        for img in images:
            try:
                # Extraire l'URL
                image_url = ImageValidator.extract_image_url(img)
                
                if not image_url:
                    continue
                
                # Valider l'URL
                if not ImageValidator.is_valid_url(image_url):
                    continue
                
                # Créer une copie normalisée de l'image
                normalized_img = {
                    "url": image_url,
                    "description": img.get("description", img.get("documents", "Aucune description")),
                    "page": img.get("page", img.get("metadata", {}).get("page", "N/A"))
                }
                
                valid_images.append(normalized_img)
                
            except Exception:
                # Ignorer silencieusement les images avec erreur
                continue
        
        return valid_images
    
    @staticmethod
    def get_size_settings(config=None) -> tuple:
        """
        Récupère les paramètres de taille depuis la configuration
        
        Args:
            config: Configuration de l'application
            
        Returns:
            Tuple (size_options, size_labels, size_map)
        """
        if config and hasattr(config.ui, 'image_sizes'):
            size_options = list(config.ui.image_sizes.keys())
            size_labels = size_options  # Utiliser les clés directement
            size_map = config.ui.image_sizes
        else:
            size_options = ["small", "medium", "large"]
            size_labels = ["Small", "Medium", "Large"]  # Anglais simple pour éviter les problèmes
            size_map = {"Small": 200, "Medium": 400, "Large": 600}
        
        return size_options, size_labels, size_map