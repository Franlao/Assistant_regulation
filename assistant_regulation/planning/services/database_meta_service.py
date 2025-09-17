#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service de détection et traitement des questions méta sur la base de données.
Détecte automatiquement les questions sur les métadonnées et appelle les bons outils.
"""

import json
import logging
import re
from typing import Dict, Optional, List, Any, Union
from dataclasses import dataclass
from enum import Enum
import ollama
from mistralai import Mistral, UserMessage
from pydantic import BaseModel, Field, field_validator, ValidationError
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Configuration du logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class MetaQueryType(Enum):
    """Types de questions méta identifiables"""
    REGULATIONS_COUNT = "regulations_count"        # Combien de réglementations
    REGULATIONS_LIST = "regulations_list"          # Liste des réglementations
    DATABASE_SUMMARY = "database_summary"          # Résumé général de la base
    LARGEST_REGULATION = "largest_regulation"      # Plus grande réglementation
    SMALLEST_REGULATION = "smallest_regulation"    # Plus petite réglementation
    DOCUMENTS_COUNT = "documents_count"            # Nombre de documents
    CHUNKS_COUNT = "chunks_count"                 # Nombre total de chunks
    REGULATION_DETAILS = "regulation_details"      # Détails d'une réglementation spécifique
    STORAGE_INFO = "storage_info"                 # Informations de stockage
    NOT_META = "not_meta"                         # Pas une question méta

class RobustMetaDetectionModel(BaseModel):
    """Modèle Pydantic robuste pour les réponses LLM malformées"""
    is_meta: bool = Field(default=False, description="Si c'est une question méta")
    query_type: str = Field(default="not_meta", description="Type de question méta")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Score de confiance")
    reasoning: str = Field(default="Analyse par défaut", description="Raisonnement")
    extracted_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Paramètres extraits")
    
    @field_validator('query_type')
    @classmethod
    def validate_query_type(cls, v):
        """Valide que query_type est un type valide"""
        valid_types = [t.value for t in MetaQueryType]
        if v not in valid_types:
            logger.warning(f"Type de requête invalide '{v}', utilisation de 'not_meta'")
            return "not_meta"
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Assure que la confiance est entre 0 et 1"""
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return 0.5
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v):
        """Assure qu'il y a toujours un raisonnement"""
        if not v or not isinstance(v, str):
            return "Raisonnement par défaut"
        return str(v)[:500]  # Limiter la taille
    
    @field_validator('extracted_params')
    @classmethod
    def validate_params(cls, v):
        """Assure que extracted_params est un dict"""
        if not isinstance(v, dict):
            return {}
        return v

@dataclass
class MetaDetectionResult:
    """Résultat de la détection de question méta"""
    is_meta: bool
    query_type: MetaQueryType
    confidence: float
    extracted_params: Dict[str, Any]
    reasoning: str

class DatabaseMetaService:
    """
    Service de détection et traitement des questions méta sur la base de données.
    Intègre DatabaseSummaryManager et autres outils d'analyse.
    """
    
    def __init__(self, llm_provider: str = "mistral", model_name: str = "mistral-medium"):
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.mistral_client = None
        self.openai_client = None
        
        # Initialiser les outils d'analyse
        self._init_analysis_tools()
        
        # Initialiser le client LLM
        if llm_provider == "mistral":
            try:
                import os
                api_key = os.getenv("MISTRAL_API_KEY")
                if api_key:
                    self.mistral_client = Mistral(api_key=api_key)
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Mistral: {e}")
                self.llm_provider = "ollama"
        elif llm_provider == "openai":
            try:
                if OpenAI is None:
                    raise ImportError("openai package not installed")
                import os
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.openai_client = OpenAI(api_key=api_key)
                else:
                    raise EnvironmentError("OPENAI_API_KEY not set")
            except Exception as e:
                logger.warning(f"Impossible d'initialiser OpenAI: {e}")
                self.llm_provider = "ollama"
    
    def _init_analysis_tools(self):
        """Initialise les outils d'analyse de la base de données"""
        try:
            from assistant_regulation.planning.Database.database_summary import DatabaseSummaryManager
            from assistant_regulation.planning.services.intelligent_summary_service import IntelligentSummaryService
            
            self.db_summary_manager = DatabaseSummaryManager()
            self.summary_service = IntelligentSummaryService(self.llm_provider, self.model_name)
            
        except Exception as e:
            logger.error(f"Erreur initialisation outils d'analyse: {e}")
            self.db_summary_manager = None
            self.summary_service = None
    
    def _get_meta_detection_prompt(self, query: str) -> str:
        """Construit le prompt pour détecter les questions méta"""
        
        return f"""Tu es un expert en analyse de questions pour détecter les questions sur les métadonnées d'une base de données de réglementations automobiles.

QUESTION UTILISATEUR: "{query}"

Détermine si cette question porte sur les MÉTADONNÉES de la base de données (informations SOBRE la base elle-même, pas sur le contenu des réglementations).

TYPES DE QUESTIONS MÉTA (nécessitent des outils spéciaux):
1. REGULATIONS_COUNT: "Combien de réglementations?", "Nombre de réglementation", "Il y a combien de règlement?", "Quantité"
2. REGULATIONS_LIST: "Liste des réglementations", "Quelles réglementations?", "Montrez les codes", "Voir la liste"
3. DATABASE_SUMMARY: "Résumé de la base", "Statistiques", "Vue d'ensemble", "Infos base", "Détails base"
4. LARGEST_REGULATION: "Plus grande réglementation", "Réglementation volumineuse", "Plus gros règlement"
5. SMALLEST_REGULATION: "Plus petite réglementation", "Réglementation courte", "Plus petit règlement"
6. DOCUMENTS_COUNT: "Combien de documents?", "Nombre de document"
7. CHUNKS_COUNT: "Combien de chunks?", "Nombre de segments"
8. REGULATION_DETAILS: "Détails sur R107", "Infos sur réglementation X" (avec code spécifique)
9. STORAGE_INFO: "Taille de la base", "Espace", "Stockage"

QUESTIONS NON-MÉTA (contenu réglementaire normal):
- "Que dit la R107 sur les freins?" → Contenu spécifique
- "Exigences de sécurité selon R46" → Contenu réglementaire
- "Comment tester les feux?" → Procédures techniques
- "Définition d'un rétroviseur" → Concept général

ANALYSE REQUISE:
1. La question porte-t-elle sur la BASE elle-même ou sur son CONTENU?
2. Demande-t-elle des statistiques/métadonnées?
3. Quel type de métadonnée est recherché?
4. Y a-t-il des paramètres spécifiques (codes de réglementation)?

RÉPONDS UNIQUEMENT EN JSON VALIDE:
{{
    "is_meta": true,
    "query_type": "regulations_count",
    "confidence": 0.95,
    "extracted_params": {{"regulation_code": null}},
    "reasoning": "Question directe sur le nombre de réglementations"
}}

EXEMPLES:
- "Combien de réglementations dans la base?" → {{"is_meta": true, "query_type": "regulations_count", "confidence": 0.98}}
- "Liste des réglementations disponibles" → {{"is_meta": true, "query_type": "regulations_list", "confidence": 0.95}}
- "Que dit la R107?" → {{"is_meta": false, "query_type": "not_meta", "confidence": 0.90}}
- "Détails sur R46" (sans contenu spécifique) → {{"is_meta": true, "query_type": "regulation_details", "extracted_params": {{"regulation_code": "R46"}}}}

ANALYSE:"""
    
    def _call_llm(self, prompt: str) -> str:
        """Appelle le LLM pour l'analyse méta"""
        
        try:
            if self.llm_provider == "mistral" and self.mistral_client:
                messages = [UserMessage(content=prompt)]
                response = self.mistral_client.chat.complete(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=300
                )
                return response.choices[0].message.content
            elif self.llm_provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=300
                )
                return response.choices[0].message.content
            else:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.1,
                        "num_predict": 250
                    }
                )
                return response.get('message', {}).get('content', '')
                
        except Exception as e:
            logger.error(f"Erreur lors de l'appel LLM: {e}")
            # Retourner un JSON d'erreur simple
            return json.dumps({
                "is_meta": False,
                "query_type": "not_meta",
                "confidence": 0.3,
                "extracted_params": {},
                "reasoning": f"Erreur LLM: {e}"
            })
    
    
    def _parse_meta_response_robust(self, response: str) -> Dict:
        """Parse robuste avec Pydantic pour gérer les réponses LLM malformées"""
        try:
            response = response.strip()
            logger.debug(f"Parsing LLM response: {response[:200]}...")
            
            # Nettoyer markdown
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # Tentative 1: Parser JSON complet
            try:
                raw_data = json.loads(response)
                validated = RobustMetaDetectionModel(**raw_data)
                logger.info("Pydantic validation successful - JSON complet")
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError) as e:
                logger.debug(f"JSON complet failed: {e}")
            
            # Tentative 2: Extraire JSON du texte
            import re
            json_match = re.search(r'\{[^}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    raw_data = json.loads(json_match.group())
                    validated = RobustMetaDetectionModel(**raw_data)
                    logger.info("Pydantic validation successful - JSON extrait")
                    return validated.model_dump()
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.debug(f"JSON extrait failed: {e}")
            
            # Tentative 3: Parser JSON partiel avec correction automatique
            try:
                # Essayer de corriger les erreurs JSON communes
                corrected = self._fix_common_json_errors(response)
                raw_data = json.loads(corrected)
                validated = RobustMetaDetectionModel(**raw_data)
                logger.info("Pydantic validation successful - JSON corrigé")
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError) as e:
                logger.debug(f"JSON corrigé failed: {e}")
            
            # Tentative 4: Extraction de valeurs spécifiques avec regex
            extracted_data = self._extract_values_with_regex(response)
            validated = RobustMetaDetectionModel(**extracted_data)
            logger.info("Pydantic validation successful - extraction regex")
            return validated.model_dump()
            
        except Exception as e:
            logger.error(f"Erreur complète parsing meta response: {e}")
            # Fallback ultime avec Pydantic (utilise les valeurs par défaut)
            validated = RobustMetaDetectionModel()
            validated.reasoning = f"Erreur parsing: {e}"
            return validated.model_dump()
    
    def _fix_common_json_errors(self, text: str) -> str:
        """Corrige les erreurs JSON communes des LLM"""
        # Supprimer les virgules en fin d'objet/array
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Ajouter des guillemets manquants pour les clés
        text = re.sub(r'(\w+)(:)', r'"\1"\2', text)
        
        # Corriger true/false en lowercase
        text = text.replace('True', 'true').replace('False', 'false')
        
        return text
    
    def _extract_values_with_regex(self, text: str) -> Dict:
        """Extrait les valeurs avec des regex en cas d'échec JSON"""
        result = {}
        
        # Extraire is_meta
        is_meta_match = re.search(r'"is_meta":\s*(true|false)', text, re.IGNORECASE)
        result['is_meta'] = is_meta_match.group(1).lower() == 'true' if is_meta_match else False
        
        # Extraire query_type
        type_match = re.search(r'"query_type":\s*"([^"]*)"', text)
        result['query_type'] = type_match.group(1) if type_match else "not_meta"
        
        # Extraire confidence
        conf_match = re.search(r'"confidence[^"]*":\s*([0-9.]+)', text)
        result['confidence'] = float(conf_match.group(1)) if conf_match else 0.5
        
        # Extraire reasoning
        reason_match = re.search(r'"reasoning":\s*"([^"]*)"', text)
        result['reasoning'] = reason_match.group(1) if reason_match else "Extraction regex"
        
        result['extracted_params'] = {}
        
        return result
    
    def detect_meta_query(self, query: str) -> MetaDetectionResult:
        """
        Détecte si une requête est une question méta sur la base de données.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            MetaDetectionResult avec l'analyse
        """
        logger.info(f"Détection méta pour: {query}")
        
        # Essayer d'abord le LLM
        try:
            # Construire le prompt
            prompt = self._get_meta_detection_prompt(query)
            
            # Appeler le LLM
            llm_response = self._call_llm(prompt)
            
            # Parser la réponse avec Pydantic robuste
            analysis_data = self._parse_meta_response_robust(llm_response)
            
            # Si le LLM a donné une bonne réponse, l'utiliser
            if analysis_data.get("is_meta") is not None and analysis_data.get("confidence", 0) >= 0.5:
                result = MetaDetectionResult(
                    is_meta=analysis_data.get("is_meta", False),
                    query_type=MetaQueryType(analysis_data.get("query_type", "not_meta")),
                    confidence=analysis_data.get("confidence", 0.5),
                    extracted_params=analysis_data.get("extracted_params", {}),
                    reasoning=f"LLM: {analysis_data.get('reasoning', 'Analyse LLM')}"
                )
                
                logger.info(f"Détection LLM: {result.is_meta} - Type: {result.query_type.value} - Confiance: {result.confidence:.2f}")
                return result
        
        except Exception as e:
            logger.warning(f"Erreur LLM, utilisation du fallback: {e}")
        
        # Fallback simple par mots-clés (sans regex complexe)
        result = self._simple_keyword_detection(query)
        logger.info(f"Détection fallback: {result.is_meta} - Type: {result.query_type.value} - Confiance: {result.confidence:.2f}")
        return result
    
    def _simple_keyword_detection(self, query: str) -> MetaDetectionResult:
        """Détection simple par mots-clés sans regex complexe"""
        
        # Normaliser la query (minuscules, sans accents)
        import unicodedata
        query_clean = unicodedata.normalize('NFD', query.lower()).encode('ascii', 'ignore').decode('ascii')
        
        # Mots-clés pour chaque type (approche simple)
        keywords = {
            "regulations_count": ["combien", "nombre", "quantite"] + ["reglement", "reglementation"],
            "regulations_list": ["liste", "quelles", "montrez", "voir"] + ["reglement", "reglementation"],
            "database_summary": ["resume", "statistique", "vue", "ensemble", "synthese", "info", "details"] + ["base"],
            "largest_regulation": ["plus", "grande", "gros", "volumineuse"] + ["reglement"],
            "smallest_regulation": ["plus", "petite", "petit", "courte"] + ["reglement"],
            "documents_count": ["combien", "nombre"] + ["document"],
            "chunks_count": ["combien", "nombre"] + ["chunk", "segment"]
        }
        
        # Compter les matches pour chaque type
        best_match = ("not_meta", 0)
        
        for query_type, words in keywords.items():
            score = sum(1 for word in words if word in query_clean)
            
            # Bonus si combinaison logique (ex: "combien" + "reglement")
            if query_type == "regulations_count":
                if ("combien" in query_clean or "nombre" in query_clean) and ("reglement" in query_clean):
                    score += 2
            elif query_type == "regulations_list":
                if ("liste" in query_clean or "quelles" in query_clean) and ("reglement" in query_clean):
                    score += 2
            elif query_type == "database_summary":
                if ("resume" in query_clean or "statistique" in query_clean) and ("base" in query_clean):
                    score += 2
            
            if score > best_match[1]:
                best_match = (query_type, score)
        
        # Déterminer le résultat
        if best_match[1] >= 2:  # Au moins 2 mots-clés
            return MetaDetectionResult(
                is_meta=True,
                query_type=MetaQueryType(best_match[0]),
                confidence=min(0.9, 0.6 + (best_match[1] * 0.1)),
                extracted_params={},
                reasoning=f"Mots-clés détectés: score {best_match[1]}"
            )
        else:
            return MetaDetectionResult(
                is_meta=False,
                query_type=MetaQueryType.NOT_META,
                confidence=0.8,
                extracted_params={},
                reasoning="Pas assez de mots-clés méta"
            )
    
    def execute_meta_query(self, detection_result: MetaDetectionResult, original_query: str) -> Dict[str, Any]:
        """
        Exécute une requête méta détectée en appelant les bons outils.
        
        Args:
            detection_result: Résultat de la détection
            original_query: Requête originale
            
        Returns:
            Résultat formaté de la requête méta
        """
        if not detection_result.is_meta or not self.db_summary_manager:
            return {
                "type": "error",
                "message": "Question non-méta ou outils indisponibles",
                "answer": "Je ne peux pas traiter cette question comme une requête méta."
            }
        
        try:
            # Récupérer le résumé complet une seule fois
            summary_data = self.db_summary_manager.get_complete_summary()
            
            query_type = detection_result.query_type
            
            if query_type == MetaQueryType.REGULATIONS_COUNT:
                count = summary_data.get("regulations", {}).get("total_regulations", 0)
                return {
                    "type": "meta_answer",
                    "answer": f"La base contient {count} réglementations.",
                    "details": {
                        "count": count,
                        "source": "database_summary"
                    }
                }
            
            elif query_type == MetaQueryType.REGULATIONS_LIST:
                regs_list = summary_data.get("regulations", {}).get("regulations_list", [])
                formatted_list = ", ".join(sorted(regs_list)[:15])  # Top 15
                count = len(regs_list)
                
                if count > 15:
                    formatted_list += f" ... (+{count-15} autres)"
                
                return {
                    "type": "meta_answer",
                    "answer": f"Réglementations disponibles ({count}):\n{formatted_list}",
                    "details": {
                        "regulations": regs_list,
                        "count": count
                    }
                }
            
            elif query_type == MetaQueryType.DATABASE_SUMMARY:
                stats = summary_data.get("statistics", {})
                collections = summary_data.get("collections", {})
                
                text_count = collections.get("text", {}).get("count", 0)
                images_count = collections.get("images", {}).get("count", 0)
                tables_count = collections.get("tables", {}).get("count", 0)
                
                summary_text = f"""Résumé de la base de données:

Collections:
- Texte: {text_count:,} chunks
- Images: {images_count:,} éléments  
- Tables: {tables_count:,} éléments

Statistiques:
- {stats.get('total_regulations', 0)} réglementations
- {stats.get('total_unique_documents', 0)} documents uniques
- {stats.get('total_chunks', 0):,} chunks total
- Moyenne: {stats.get('average_chunks_per_regulation', 0):.1f} chunks/réglementation"""
                
                return {
                    "type": "meta_answer",
                    "answer": summary_text,
                    "details": summary_data
                }
            
            elif query_type == MetaQueryType.LARGEST_REGULATION:
                largest = summary_data.get("statistics", {}).get("largest_regulation")
                if largest:
                    return {
                        "type": "meta_answer",
                        "answer": f"Plus grande réglementation: {largest['code']} ({largest['chunks_count']:,} chunks)",
                        "details": largest
                    }
            
            elif query_type == MetaQueryType.SMALLEST_REGULATION:
                smallest = summary_data.get("statistics", {}).get("smallest_regulation")
                if smallest:
                    return {
                        "type": "meta_answer",
                        "answer": f"Plus petite réglementation: {smallest['code']} ({smallest['chunks_count']} chunks)",
                        "details": smallest
                    }
            
            elif query_type == MetaQueryType.DOCUMENTS_COUNT:
                count = summary_data.get("statistics", {}).get("total_unique_documents", 0)
                return {
                    "type": "meta_answer",
                    "answer": f"La base contient {count} documents uniques.",
                    "details": {"documents_count": count}
                }
            
            elif query_type == MetaQueryType.CHUNKS_COUNT:
                count = summary_data.get("statistics", {}).get("total_chunks", 0)
                return {
                    "type": "meta_answer",
                    "answer": f"La base contient {count:,} chunks au total.",
                    "details": {"chunks_count": count}
                }
            
            elif query_type == MetaQueryType.REGULATION_DETAILS:
                reg_code = detection_result.extracted_params.get("regulation_code")
                if reg_code:
                    regs_details = summary_data.get("regulations", {}).get("regulations_details", {})
                    if reg_code in regs_details:
                        details = regs_details[reg_code]
                        return {
                            "type": "meta_answer", 
                            "answer": f"{reg_code}: {details['documents_count']} documents, {details['chunks_count']} chunks, pages {details['pages_range']}",
                            "details": details
                        }
            
            elif query_type == MetaQueryType.STORAGE_INFO:
                storage = summary_data.get("statistics", {}).get("storage_info", {})
                return {
                    "type": "meta_answer",
                    "answer": f"Stockage: {storage.get('estimated_size_mb', 0):.1f} MB dans {storage.get('database_path', 'N/A')}",
                    "details": storage
                }
            
            # Type non géré
            return {
                "type": "error",
                "answer": f"Type de question méta non géré: {query_type.value}",
                "message": f"Le type {query_type.value} n'est pas encore implémenté."
            }
            
        except Exception as e:
            logger.error(f"Erreur exécution meta query: {e}")
            return {
                "type": "error",
                "answer": "Erreur lors de l'exécution de la requête méta.",
                "message": str(e)
            }
    
    def process_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Point d'entrée principal: détecte et traite les questions méta.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Dict avec la réponse si c'est une question méta, None sinon
        """
        # Détecter si c'est une question méta
        detection = self.detect_meta_query(query)
        
        if not detection.is_meta or detection.confidence < 0.6:
            return None  # Pas une question méta ou confiance trop faible
        
        # Exécuter la requête méta
        result = self.execute_meta_query(detection, query)
        
        # Ajouter les métadonnées de détection
        result["meta_detection"] = {
            "query_type": detection.query_type.value,
            "confidence": detection.confidence,
            "reasoning": detection.reasoning,
            "extracted_params": detection.extracted_params
        }
        
        return result

# Fonction utilitaire pour tests
def test_meta_service():
    """Teste le service de métadonnées"""
    service = DatabaseMetaService(llm_provider="ollama", model_name="llama3.2")
    
    test_queries = [
        "Combien de réglementations dans la base?",
        "Liste des réglementations disponibles",
        "Résumé de la base de données", 
        "Quelle est la plus grande réglementation?",
        "Nombre de documents",
        "Que dit la R107 sur les freins?",  # Non-méta
        "Détails sur R46"
    ]
    
    for query in test_queries:
        print(f"\n=== Test: {query} ===")
        result = service.process_query(query)
        if result:
            print(f"Type: {result['type']}")
            print(f"Réponse: {result['answer']}")
            print(f"Confiance: {result['meta_detection']['confidence']:.2f}")
        else:
            print("Non-méta")

if __name__ == "__main__":
    test_meta_service()