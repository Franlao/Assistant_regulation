from typing import List, Dict, Optional
import requests
from mistralai import Mistral
from ollama import Client
import base64
import os
import logging

# Configure logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class ImageDisplayAgent:
    def __init__(self, vision_model: str = "pixtral-12b-2409"):
        self.vision_model = vision_model
        self.client = self._init_vision_client()
        logger.info(f"ImageDisplayAgent initialized with model: {vision_model}")
        
    def _init_vision_client(self):
        """Initialise le client de vision avec fallback"""
        try:
            from mistralai import Mistral
            logger.info("Using Mistral as vision client")
            return Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        except:
            try:
                from ollama import Client
                logger.info("Using Ollama as vision client")
                return Client()
            except:
                raise RuntimeError("Aucun modèle vision disponible")

    def validate_images(self, question: str, image_chunks: List[Dict]) -> List[Dict]:
        """Filtre les images pertinentes pour la question"""
        relevant_images = []
        
        logger.info(f"Validating {len(image_chunks)} images for relevance")
        
        for i, img in enumerate(image_chunks):
            # Vérifier d'abord que l'URL existe et n'est pas vide
            image_url = img.get("metadata", {}).get("image_url", "").strip()
            
            logger.info(f"Processing image {i}, URL format: {'data:...' if image_url.startswith('data:') else image_url[:30]+'...'}")
            
            if not image_url:
                logger.warning(f"Skipping image {i} with missing URL: {img}")
                continue
                
            logger.info(f"Checking relevance for image {i} with URL starting with: {image_url[:30]}...")
            
            try:
                if self._is_relevant(question, img):
                    # Ensure image_url is properly formatted and accessible
                    # Log the URL being added to the results
                    logger.info(f"Image {i} is relevant, adding to results list")
                    
                    # Make sure we have all required fields
                    formatted_image = {
                        'url': image_url,
                        'description': img.get('documents', ''),
                        'page': img.get("metadata", {}).get("page", "N/A")
                    }
                    
                    # Log the formatted image object
                    logger.info(f"Formatted image object: {formatted_image}")
                    
                    relevant_images.append(formatted_image)
                else:
                    logger.info(f"Image {i} is not relevant to the question")
            except Exception as e:
                logger.error(f"Error processing image {i} URL: {str(e)}")
                
        logger.info(f"Found {len(relevant_images)} relevant images")
        return relevant_images

    def _is_relevant(self, question: str, image: Dict) -> bool:
        """Décide de la pertinence avec le modèle vision"""
        # Vérifier que l'image a une URL valide
        image_url = image.get("metadata", {}).get("image_url", "").strip()
        if not image_url:
            logger.warning("Image URL is empty or missing")
            return False
            
        try:
            prompt = self._create_prompt(question, image)
            
            if isinstance(self.client, Mistral):
                logger.info("Using Mistral for relevance check")
                response = self.client.chat.complete(
                    model=self.vision_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10
                )
                content = response.choices[0].message.content
            else:
                logger.info("Using Ollama for relevance check")
                response = self.client.chat(
                    model="granite3.2-vision:latest",
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response['message']['content']
                
            result = self._parse_response(content)
            logger.info(f"Vision model response: '{content}', is relevant: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in image relevance check: {str(e)}")
            # En cas d'erreur, on considère l'image comme non pertinente
            return False

    def _create_prompt(self, question: str, image: Dict) -> List[Dict]:
        """Crée le prompt multimédia pour l'évaluation"""
        image_url = image.get("metadata", {}).get("image_url", "").strip()
        page = image.get("metadata", {}).get("page", "N/A")
        description = image.get('documents', 'Aucune description')
        
        logger.info(f"Creating prompt for image from page {page}")
        
        return [
            {
                "type": "text",
                "text": f"""Cette image est-elle essentielle pour répondre à : "{question}"?
Description de l'image : {description}
Page : {page}
Répondez uniquement par OUI ou NON."""
            },
            {
                "type": "image_url",
                "image_url": image_url
            }
        ]

    def _parse_response(self, response: str) -> bool:
        """Interprète la réponse du modèle"""
        clean_res = response.strip().lower()
        is_relevant = any(keyword in clean_res for keyword in ["oui", "yes"]) and "non" not in clean_res
        logger.info(f"Vision model response parsed: {clean_res} -> is relevant: {is_relevant}")
        return is_relevant