"""
Chunking d'images amélioré avec classification intelligente et descriptions optimisées.
"""

import fitz
import base64
from PIL import Image
import io
import os
import hashlib
import json
from typing import Dict, List, Optional, Tuple
import logging
import cv2
import numpy as np

# Configuration logging (moins verbeux par défaut)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class EnhancedImageChunker:
    """
    Chunker d'images amélioré avec classification et analyse intelligente.
    """
    
    def __init__(self, 
                 min_width: int = 50, 
                 min_height: int = 50,
                 max_images_per_page: int = 10,
                 quality_threshold: float = 0.3,
                 enable_ocr_detection: bool = True,
                 cache_dir: str = "image_cache"):
        """
        Initialise le chunker d'images amélioré.
        
        Args:
            min_width: Largeur minimale des images
            min_height: Hauteur minimale des images
            max_images_per_page: Nombre maximum d'images par page
            quality_threshold: Seuil de qualité pour filtrer les images
            enable_ocr_detection: Activer la détection de texte dans les images
            cache_dir: Répertoire pour le cache des descriptions
        """
        self.min_width = min_width
        self.min_height = min_height
        self.max_images_per_page = max_images_per_page
        self.quality_threshold = quality_threshold
        self.enable_ocr_detection = enable_ocr_detection
        self.cache_dir = cache_dir
        
        # Créer le répertoire de cache
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Extraction intelligente des images avec analyse de qualité.
        """
        try:
            doc = fitz.open(pdf_path)
            chunks = []
            document_name = os.path.basename(pdf_path)
            
            logger.info(f"Extraction images de {document_name}: {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Image de la page complète
                full_page_pix = page.get_pixmap(dpi=144)
                full_page_url = f"data:image/png;base64,{base64.b64encode(full_page_pix.tobytes('png')).decode()}"
                
                # Extraction des images individuelles
                images = page.get_images()
                page_images = []
                
                for img_index, img in enumerate(images):
                    if len(page_images) >= self.max_images_per_page:
                        break
                    
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        
                        if not base_image:
                            continue
                        
                        # Analyse de qualité
                        quality_analysis = self._analyze_image_quality(base_image)
                        
                        if quality_analysis['overall_quality'] < self.quality_threshold:
                            continue
                        
                        # Classification du type d'image
                        image_classification = self._classify_image_type(base_image)
                        
                        # Détection OCR si activée
                        ocr_info = {}
                        if self.enable_ocr_detection:
                            ocr_info = self._detect_text_in_image(base_image)
                        
                        # Construction du chunk enrichi
                        image_b64 = base64.b64encode(base_image["image"]).decode()
                        
                        chunk = {
                            # Informations de base
                            "page_number": page_num + 1,
                            "image_index": img_index,
                            "image_url": f"data:image/{base_image['ext']};base64,{image_b64}",
                            "full_page_url": full_page_url,
                            "dimensions": (base_image['width'], base_image['height']),
                            "type": "image",
                            
                            # Métadonnées du document
                            "document_source": pdf_path,
                            "document_name": document_name,
                            
                            # Analyse de qualité
                            "quality_analysis": quality_analysis,
                            
                            # Classification
                            "image_classification": image_classification,
                            
                            # OCR si activé
                            "ocr_info": ocr_info,
                            
                            # Identifiant unique pour cache
                            "image_hash": self._calculate_image_hash(base_image["image"]),
                            
                            # Métadonnées techniques
                            "format": base_image['ext'],
                            "size_bytes": len(base_image["image"]),
                            "colorspace": base_image.get('colorspace', 'unknown'),
                            
                            # Contexte dans la page
                            "page_context": self._extract_page_context(page, img)
                        }
                        
                        page_images.append(chunk)
                        
                    except Exception as e:
                        logger.warning(f"Erreur traitement image {img_index} page {page_num + 1}: {e}")
                        continue
                
                chunks.extend(page_images)
                logger.info(f"Page {page_num + 1}: {len(page_images)} images extraites")
            
            doc.close()
            
            logger.info(f"Extraction terminée: {len(chunks)} images de qualité")
            return chunks
            
        except Exception as e:
            logger.error(f"Erreur extraction images: {e}")
            return []
    
    def _analyze_image_quality(self, base_image: Dict) -> Dict:
        """
        Analyse la qualité d'une image.
        """
        try:
            # Conversion en PIL
            img_data = io.BytesIO(base_image["image"])
            pil_img = Image.open(img_data).convert("RGB")
            
            # Métriques de qualité
            width, height = pil_img.size
            pixel_count = width * height
            
            # Analyse des couleurs
            colors = pil_img.getcolors(maxcolors=256*256*256)
            unique_colors = len(colors) if colors else 0
            
            # Détection d'images noires/blanches
            extrema = pil_img.getextrema()
            is_black = bool(all(max(channel) == 0 for channel in extrema))
            is_white = bool(all(min(channel) == 255 for channel in extrema))
            
            # Contraste
            grayscale = pil_img.convert('L')
            histogram = grayscale.histogram()
            contrast_score = np.std(histogram) / 255.0
            
            # Score de qualité global
            size_score = min(1.0, pixel_count / 10000)  # Optimal ~100x100
            color_score = min(1.0, unique_colors / 1000)  # Diversité des couleurs
            contrast_score = min(1.0, contrast_score)
            
            # Pénalités
            penalty = 0.0
            if is_black or is_white:
                penalty = 0.8
            if width < 30 or height < 30:
                penalty = 0.5
            
            overall_quality = max(0.0, (size_score + color_score + contrast_score) / 3 - penalty)
            
            return {
                'overall_quality': round(overall_quality, 3),
                'size_score': round(size_score, 3),
                'color_score': round(color_score, 3),
                'contrast_score': round(contrast_score, 3),
                'unique_colors': unique_colors,
                'is_black': is_black,
                'is_white': is_white,
                'pixel_count': pixel_count
            }
            
        except Exception as e:
            logger.warning(f"Erreur analyse qualité: {e}")
            return {'overall_quality': 0.0, 'error': str(e)}
    
    def _classify_image_type(self, base_image: Dict) -> Dict:
        """
        Classifie le type d'image (diagramme, photo, graphique, etc.).
        """
        try:
            # Conversion en PIL
            img_data = io.BytesIO(base_image["image"])
            pil_img = Image.open(img_data).convert("RGB")
            
            # Conversion en OpenCV
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # Détection de contours
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyse des formes
            geometric_shapes = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Ignorer les petits contours
                    # Approximation polygonale
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    if len(approx) <= 8:  # Formes géométriques simples
                        geometric_shapes += 1
            
            # Classification basée sur les caractéristiques
            width, height = pil_img.size
            aspect_ratio = width / height
            
            # Détection de graphiques/diagrammes
            is_diagram = bool(geometric_shapes > 5)
            is_chart = bool(aspect_ratio > 1.5 and geometric_shapes > 2)
            is_technical = bool(len(contours) > 10 and geometric_shapes > 3)
            
            # Détection de photos
            colors = pil_img.getcolors(maxcolors=256*256*256)
            unique_colors = len(colors) if colors else 0
            is_photo = bool(unique_colors > 5000 and geometric_shapes < 5)
            
            # Classification finale
            if is_photo:
                image_type = "photo"
                confidence = 0.8
            elif is_chart:
                image_type = "chart"
                confidence = 0.7
            elif is_diagram:
                image_type = "diagram"
                confidence = 0.6
            elif is_technical:
                image_type = "technical"
                confidence = 0.5
            else:
                image_type = "unknown"
                confidence = 0.3
            
            return {
                'type': image_type,
                'confidence': confidence,
                'geometric_shapes': geometric_shapes,
                'contours_count': len(contours),
                'aspect_ratio': round(aspect_ratio, 2),
                'unique_colors': unique_colors,
                'is_diagram': is_diagram,
                'is_chart': is_chart,
                'is_technical': is_technical,
                'is_photo': is_photo
            }
            
        except Exception as e:
            logger.warning(f"Erreur classification: {e}")
            return {'type': 'unknown', 'confidence': 0.0, 'error': str(e)}
    
    def _detect_text_in_image(self, base_image: Dict) -> Dict:
        """
        Détecte la présence de texte dans une image.
        """
        try:
            # Conversion en PIL
            img_data = io.BytesIO(base_image["image"])
            pil_img = Image.open(img_data).convert("RGB")
            
            # Conversion en OpenCV
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            
            # Détection de régions de texte (basique)
            # Utilise des gradients pour détecter les zones de texte
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient = np.sqrt(grad_x**2 + grad_y**2)
            
            # Seuillage pour détecter les zones à fort gradient (texte)
            text_regions = gradient > np.mean(gradient) + 2 * np.std(gradient)
            text_density = np.sum(text_regions) / text_regions.size
            
            # Détection de lignes horizontales (indicateur de texte)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            horizontal_score = np.sum(horizontal_lines > 0) / horizontal_lines.size
            
            # Score de présence de texte
            text_score = (text_density + horizontal_score) / 2
            has_text = bool(text_score > 0.1)
            
            return {
                'has_text': has_text,
                'text_score': round(text_score, 3),
                'text_density': round(text_density, 3),
                'horizontal_score': round(horizontal_score, 3),
                'ocr_recommended': bool(has_text and text_score > 0.2)
            }
            
        except Exception as e:
            logger.warning(f"Erreur détection texte: {e}")
            return {'has_text': False, 'text_score': 0.0, 'error': str(e)}
    
    def _calculate_image_hash(self, image_data: bytes) -> str:
        """
        Calcule un hash unique pour l'image.
        """
        return hashlib.md5(image_data).hexdigest()
    
    def _extract_page_context(self, page, img_info) -> Dict:
        """
        Extrait le contexte de l'image dans la page.
        """
        try:
            # Obtenir les blocs de texte de la page
            text_blocks = page.get_text("dict")
            
            # Position de l'image (approximative)
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Analyse de la position relative
            context = {
                'page_width': page_width,
                'page_height': page_height,
                'text_blocks_count': len(text_blocks.get('blocks', [])),
                'surrounding_text': '',  # À implémenter si nécessaire
                'position_relative': 'unknown'
            }
            
            return context
            
        except Exception as e:
            logger.warning(f"Erreur extraction contexte: {e}")
            return {'error': str(e)}

# Fonction principale pour compatibilité
def pdf_to_image_chunks(pdf_path: str, 
                       min_width: int = 50, 
                       min_height: int = 50, 
                       filter_black: bool = True,
                       enhanced: bool = True) -> List[Dict]:
    """
    Fonction principale d'extraction d'images avec option d'amélioration.
    
    Args:
        pdf_path: Chemin vers le PDF
        min_width: Largeur minimale
        min_height: Hauteur minimale
        filter_black: Filtrer les images noires (mode compatibilité)
        enhanced: Utiliser l'extraction améliorée (par défaut)
    
    Returns:
        Liste des chunks d'images
    """
    
    if enhanced:
        # Nouvelle version améliorée
        chunker = EnhancedImageChunker(
            min_width=min_width,
            min_height=min_height,
            quality_threshold=0.3,
            enable_ocr_detection=True
        )
        
        return chunker.extract_images_from_pdf(pdf_path)
    
    else:
        # Version classique (compatibilité)
        doc = fitz.open(pdf_path)
        chunks = []
        document_name = os.path.basename(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            full_page_pix = page.get_pixmap(dpi=144)
            full_page_url = f"data:image/png;base64,{base64.b64encode(full_page_pix.tobytes('png')).decode()}"
            
            for img in page.get_images():
                xref = img[0]
                base_image = doc.extract_image(xref)
                
                if not base_image:
                    continue
                
                if base_image.get('mask'):
                    continue
                    
                if base_image['width'] < min_width or base_image['height'] < min_height:
                    continue
                
                if filter_black:
                    try:
                        img_data = io.BytesIO(base_image["image"])
                        pil_img = Image.open(img_data).convert("RGB")
                        if all(max(channel) == 0 for channel in pil_img.getextrema()):
                            continue
                    except:
                        continue
                
                image_b64 = base64.b64encode(base_image["image"]).decode()
                chunks.append({
                    "page_number": page_num + 1,
                    "image_url": f"data:image/{base_image['ext']};base64,{image_b64}",
                    "full_page_url": full_page_url,
                    "dimensions": (base_image['width'], base_image['height']),
                    "type": "image",
                    "document_source": pdf_path,
                    "document_name": document_name
                })
        
        doc.close()
        return chunks