"""
Simple Orchestrator Module

Coordonne une recherche multimodale dans les bases texte, image et table,
avec option de vérification des chunks et génération de réponse.
"""

import os
import time
import logging
import concurrent.futures
from functools import partial
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
# Ajout de joblib pour l'optimisation des performances
from joblib import Parallel, delayed, Memory
import random
load_dotenv()
# Import des retrievers et de l'agent de vérification
from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever
from assistant_regulation.processing.Modul_verif.verif_agent import VerifAgent
# Imports avec gestion relative/absolue
try:
    from assistant_regulation.planning.agents.query_analysis_agent import QueryAnalysisAgent
    from .cache import ResultCache
    from assistant_regulation.planning.agents.agent_image import ImageDisplayAgent
    from .lang_py import translate_query
    from .conversation_memory import ConversationMemory
except ImportError:
    # Import absolu si les imports relatifs échouent
    from assistant_regulation.planning.agents.query_analysis_agent import QueryAnalysisAgent
    from cache import ResultCache
    from assistant_regulation.planning.agents.agent_image import ImageDisplayAgent
    from lang_py import translate_query
    from conversation_memory import ConversationMemory
class SimpleOrchestrator:
    """
    Orchestrateur simplifié pour combiner texte, images et tables dans une réponse.
    """
    
    def __init__(self, 
                 llm_provider: str = "ollama", 
                 model_name: str = "llama3.2", 
                 enable_verification: bool = True,
                 use_joblib_cache: bool = True,
                 cache_dir: str = "./joblib_cache",
                 session_id: str = None,
                 enable_conversation_memory: bool = True):
        """
        Initialise l'orchestrateur avec les composants essentiels.
        
        Args:
            llm_provider: Fournisseur LLM ("ollama" ou "mistral")
            model_name: Nom du modèle à utiliser
            enable_verification: Activer ou non la vérification des chunks
            use_joblib_cache: Activer le cache joblib pour les opérations coûteuses
            cache_dir: Répertoire pour le cache joblib
            session_id: Identifiant unique de session pour la gestion de mémoire
            enable_conversation_memory: Activer la gestion de mémoire conversationnelle
        """
        # Configuration
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.enable_verification = enable_verification
        self.cache = ResultCache()
        
        # Configuration du cache joblib
        self.use_joblib_cache = use_joblib_cache
        if use_joblib_cache:
            self.memory = Memory(cache_dir, verbose=0)
            # Cache pour les opérations de recherche coûteuses
            self._cached_text_search = self.memory.cache(self._text_search_wrapper)
            self._cached_image_search = self.memory.cache(self._image_search_wrapper)
            self._cached_table_search = self.memory.cache(self._table_search_wrapper)
        else:
            self.memory = None
        
        # Logging
        self.logger = self._setup_logging()
        
        # Retrievers
        self.text_retriever = SimpleTextRetriever()
        self.image_retriever = ImageRetriever()
        self.table_retriever = TableRetriever()
        
        # Agent de vérification (optionnel)
        if enable_verification:
            if llm_provider == "mistral":
                    self.verif_agent = VerifAgent(
                        llm_provider=llm_provider,
                        model_name="mistral-small",
                    )
            else:
                self.verif_agent = VerifAgent(
                        llm_provider=llm_provider,
                        model_name=model_name,
                    )
        # Client LLM pour la génération de réponse
        self.llm_client = self._init_llm_client()

        # agent de vérification de la requête
        self.query_analyzer = QueryAnalysisAgent(
            llm_provider=llm_provider,
            model_name=model_name
        )
        
        # Gestion de mémoire conversationnelle
        self.enable_conversation_memory = enable_conversation_memory
        if enable_conversation_memory:
            # Génération d'un ID de session si non fourni
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())[:8]
            
            self.conversation_memory = ConversationMemory(
                session_id=session_id,
                window_size=7,
                max_turns_before_summary=10,
                llm_client=self.llm_client,
                model_name=model_name
            )
        else:
            self.conversation_memory = None
        
        # Add retry configuration
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 30.0,
            'exponential_base': 2,
            'jitter': True
        }
        
        # Provider fallback order
        self.provider_fallback = {
            'mistral': 'ollama',
            'ollama': 'mistral'
        }
    def _setup_logging(self):
        """Configure le logging"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _init_llm_client(self):
        """Initialise le client LLM approprié"""
        if self.llm_provider == "mistral":
            try:
                from mistralai import Mistral
                api_key = os.getenv("MISTRAL_API_KEY")
                if not api_key:
                    raise ValueError("MISTRAL_API_KEY not set")
                return {'type': 'mistral', 'client': Mistral(api_key=api_key)}
            except (ImportError, NameError):
                self.logger.error("Mistral AI package not installed or not found")
                raise ImportError("Mistral AI package not installed or not found")
        else:  # default to ollama
            try:
                import ollama
                return {'type': 'ollama', 'client': ollama}
            except ImportError:
                raise ImportError("Ollama package not installed")
    
    # Wrappers pour le cache joblib des opérations de recherche
    def _text_search_wrapper(self, query, top_k):
        """Wrapper pour le cache des recherches texte"""
        return self.text_retriever.search_with_context(query, top_k=top_k)
    
    def _image_search_wrapper(self, query, top_k):
        """Wrapper pour le cache des recherches image"""
        return self.image_retriever.search(query, top_k=top_k)
    
    def _table_search_wrapper(self, query, top_k):
        """Wrapper pour le cache des recherches tableau"""
        return self.table_retriever.search(query, top_k=top_k)
    
    def clear_joblib_cache(self):
        """Nettoie le cache joblib"""
        if self.memory:
            self.memory.clear()
            self.logger.info("Cache joblib nettoyé")
    
    def get_cache_stats(self):
        """Retourne des statistiques sur l'utilisation du cache"""
        if not self.memory:
            return {"joblib_cache": "disabled"}
        
        try:
            # Tenter d'obtenir des infos sur le cache
            cache_size = len(os.listdir(self.memory.location)) if os.path.exists(self.memory.location) else 0
            return {
                "joblib_cache": "enabled",
                "cache_location": self.memory.location,
                "cache_files": cache_size
            }
        except Exception as e:
            return {"joblib_cache": "enabled", "error": str(e)}
    
    def process_query(self, 
                     query: str, 
                     use_images: bool = True, 
                     use_tables: bool = True, 
                     top_k: int = 5,
                     use_conversation_context: bool = True) -> Dict:
        """
        Traite une requête et génère une réponse.
        
        Args:
            query: Question de l'utilisateur
            use_images: Inclure les résultats d'images
            use_tables: Inclure les résultats de tableaux
            top_k: Nombre de résultats à récupérer par source
            use_conversation_context: Utiliser le contexte conversationnel
            
        Returns:
            Dict contenant la réponse, les sources et les médias
        """
        # Vérifier le cache
        cache_params = {
            "use_images": use_images,
            "use_tables": use_tables,
            "top_k": top_k,
            "model": self.model_name,
            "verification": self.enable_verification
        }
        
        response = self.cache.get(query, cache_params)
        if response:
            self.logger.info("Résultat trouvé dans le cache")
            return response
        try:
            self.logger.info(f"Traitement de la requête: {query}")
            
            # 1. Analyser la requête
            self.logger.info("Analyse de la requête...")
            query_analysis = self.query_analyzer.analyse_query(query)
            
            # La fonctionnalité de recherche web n'étant pas implémentée,
            # nous commentons ce bloc pour éviter les faux positifs.
            # if query_analysis.get("recommend_web_search", False):
            #     return {
            #         "answer": "La question contient un lien ou nécessite une recherche web. Puis-je y accéder pour vous aider ?",
            #         "requires_web_consent": True,
            #         "urls": query_analysis.get("urls", []),
            #         "analysis": query_analysis
            #     }
            
            if query_analysis["needs_rag"]:
                # Utiliser le système RAG pour les questions réglementaires
                self.logger.info("Question identifiée comme réglementaire - utilisation du RAG")
                chunks = self._search_all_sources_parallel(query, use_images, use_tables, top_k)
                verified_chunks = self._verify_chunks(query, chunks) if self.enable_verification else chunks
                combined_context = self._prepare_context(verified_chunks)
                # Note: self_critic_agent n'est pas implémenté, on skip cette vérification
                # if not self.self_critic_agent.assess_context(query, combined_context):
                #     return {
                #         "answer": "Je suis désolé, mais les informations dont je dispose ne me permettent pas de répondre précisément à votre question.",
                #         "requires_web_consent": False,
                #         "urls": [],
                #         "analysis": query_analysis,
                #         "sources": [],
                #         "images": [],
                #         "tables": []
                #     }
                answer = self._generate_response(query, combined_context, use_conversation_context)
                
                # Ajouter les citations Vancouver si demandé
                if len(verified_chunks.get("text", [])) > 0:
                    from assistant_regulation.planning.services.citation_service import citation_service
                    sources = self._extract_sources(verified_chunks.get("text", []))
                    answer = citation_service.add_vancouver_citations(answer, sources)
                
                # Enregistrer la conversation en mémoire
                if self.conversation_memory:
                    metadata = {
                        "sources_count": len(verified_chunks.get("text", [])),
                        "images_count": len(verified_chunks.get("images", [])),
                        "tables_count": len(verified_chunks.get("tables", [])),
                        "query_type": query_analysis.get("query_type", "unknown")
                    }
                    self.conversation_memory.add_turn(query, answer, metadata)
                
                return {
                    "answer": answer,
                    "sources": self._extract_sources(verified_chunks.get("text", [])),
                    "images": verified_chunks.get("images", []),
                    "tables": verified_chunks.get("tables", []),
                    "analysis": query_analysis
                }

            else:
                # Utiliser directement le modèle pour les questions générales
                self.logger.info("Question identifiée comme générale - réponse directe")
                response = self._process_with_model(query, use_conversation_context)
                response["analysis"] = query_analysis
                
                # Enregistrer la conversation en mémoire pour les questions générales aussi
                if self.conversation_memory:
                    metadata = {
                        "query_type": query_analysis.get("query_type", "general"),
                        "sources_count": 0
                    }
                    self.conversation_memory.add_turn(query, response["answer"], metadata)
            self.cache.set(query, cache_params, response)
            return response
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {str(e)}")
            return {
                "answer": f"Je suis désolé, une erreur s'est produite lors du traitement de votre requête: {str(e)}",
                "sources": [],
                "images": [],
                "tables": [],
                "analysis": {"query_type": "error", "needs_rag": False}
            }   
        
    def _process_with_rag(self, query: str, use_images: bool, use_tables: bool, top_k: int) -> Dict:
        """Traite la requête avec le système RAG (logique existante)"""
        chunks = self._search_all_sources_parallel(query, use_images, use_tables, top_k)
        
        if self.enable_verification:
            verified_chunks = self._verify_chunks(query, chunks)
        else:
            verified_chunks = chunks
        
        combined_context = self._prepare_context(verified_chunks)
        response = self._generate_response(query, combined_context)
        
        return {
            "answer": response,
            "sources": self._extract_sources(verified_chunks.get("text", [])),
            "images": verified_chunks.get("images", []),
            "tables": verified_chunks.get("tables", [])
        }
    
    def _process_with_model(self, query: str, use_conversation_context: bool = True) -> Dict:
        """Traite la requête directement avec le modèle"""
        
        # Construire le contexte avec la mémoire conversationnelle si activée
        context_part = ""
        if use_conversation_context and self.conversation_memory:
            conversation_context = self.conversation_memory.get_context_for_query(query)
            if conversation_context.strip():
                self.logger.info("Utilisation du contexte conversationnel pour question générale")
                context_part = f"""
        CONTEXTE DE LA CONVERSATION:
        {conversation_context}
        
        """
            else:
                self.logger.info("Aucun contexte conversationnel disponible")
        
        prompt = f"""
        Répondez à la question suivante en utilisant vos connaissances générales.
        Ne faites pas référence à des réglementations spécifiques ni à des documents.
        {context_part}
        Question: {query}

        Réponse:
        """
        
        if self.llm_client['type'] == 'mistral':
            response = self.llm_client['client'].chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            answer = response.choices[0].message.content
        else:  # ollama
            response = self.llm_client['client'].chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={'temperature': 0.3}
            )
            answer = response['message']['content']
        
        return {
            "answer": answer,
            "sources": [],
            "images": [],
            "tables": []
        }
    def _generate_response_stream(self, query: str, context: str, conversation_context: str = ""):
        """
        Génère une réponse en streaming basée sur le contexte.
        
        Args:
            query: Question de l'utilisateur
            context: Contexte formaté
            conversation_context: Contexte conversationnel
            
        Yields:
            str: Morceaux de réponse
        """
        try:
            # Construire le prompt avec contexte conversationnel si disponible
            if conversation_context and conversation_context.strip():
                prompt = f"""
                {conversation_context}

                En tant qu'assistant réglementaire automobile, répondez à la question actuelle en utilisant:
                1. Le contexte de notre conversation précédente
                2. Les informations réglementaires ci-dessous

                INFORMATIONS RÉGLEMENTAIRES:
                {context}

                Réponse précise et conforme aux réglementations:
                """
            else:
                prompt = f"""
                En tant qu'assistant réglementaire automobile, répondez à cette question en utilisant 
                exclusivement les informations des réglementations fournies ci-dessous.

                INFORMATIONS RÉGLEMENTAIRES:
                {context}

                QUESTION: {query}

                Réponse précise et conforme aux réglementations:
                """
            
            # Streaming selon le provider
            if self.llm_client['type'] == 'mistral':
                stream_response = self.llm_client['client'].chat.stream(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1024
                )
                
                for chunk in stream_response:
                    if chunk.data.choices[0].delta.content is not None:
                        yield chunk.data.choices[0].delta.content
            
            else:  # ollama
                response = self.llm_client['client'].chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={'temperature': 0.3},
                    stream=True
                )
                
                for chunk in response:
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
            yield f"Erreur lors de la génération de réponse: {str(e)}"
    
    def process_query_stream(self, 
                           query: str, 
                           use_images: bool = True, 
                           use_tables: bool = True, 
                           top_k: int = 5):
        """
        Traite une requête et génère une réponse en streaming.
        
        Args:
            query: Question de l'utilisateur
            use_images: Inclure les résultats d'images
            use_tables: Inclure les résultats de tableaux
            top_k: Nombre de résultats à récupérer par source
            
        Returns:
            Generator: Génère des morceaux de réponse
        """
        try:
            self.logger.info(f"Traitement de la requête: {query}")
            
            # 1. Analyser la requête
            query_analysis = self.query_analyzer.analyse_query(query)
            
            # Yield analysis info
            yield {"type": "analysis", "content": query_analysis}

            # Préparer le contexte conversationnel si disponible
            conversation_context = ""
            if self.conversation_memory:
                conversation_context = self.conversation_memory.get_context_for_query(query)
            
            if query_analysis["needs_rag"]:
                # Utiliser le système RAG pour les questions réglementaires
                self.logger.info("Question identifiée comme réglementaire - utilisation du RAG")
                
                # Recherche et préparation du contexte
                chunks = self._search_all_sources(query, use_images, use_tables, top_k)
                
                if self.enable_verification:
                    verified_chunks = self._verify_chunks(query, chunks)
                else:
                    verified_chunks = chunks
                
                combined_context = self._prepare_context(verified_chunks)
                
                # Yield search completed
                yield {"type": "search_complete", "content": {
                    "sources": self._extract_sources(verified_chunks.get("text", [])),
                    "images": verified_chunks.get("images", []),
                    "tables": verified_chunks.get("tables", [])
                }}
                
                # Stream la réponse avec contexte conversationnel et fallback
                for text_chunk in self._generate_response_stream_with_fallback(query, combined_context, conversation_context):
                    yield {"type": "text", "content": text_chunk}
            
            else:
                # Utiliser directement le modèle pour les questions générales
                self.logger.info("Question identifiée comme générale - réponse directe")
                
                # Construire le prompt avec contexte conversationnel si disponible
                if conversation_context:
                    prompt = f"""
                    {conversation_context}

                    Répondez à la question actuelle en tenant compte du contexte de la conversation précédente.
                    Utilisez vos connaissances générales et faites référence aux échanges précédents si pertinent.

                    Réponse:
                    """
                else:
                    prompt = f"""
                    Répondez à la question suivante en utilisant vos connaissances générales.
                    Ne faites pas référence à des réglementations spécifiques ni à des documents.

                    Question: {query}

                    Réponse:
                    """
                
                # Stream la réponse directe
                if self.llm_client['type'] == 'mistral':
                    stream_response = self.llm_client['client'].chat.stream(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=1024
                    )
                    
                    for chunk in stream_response:
                        if chunk.data.choices[0].delta.content is not None:
                            yield {"type": "text", "content": chunk.data.choices[0].delta.content}
                
                else:  # ollama
                    response = self.llm_client['client'].chat(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        options={'temperature': 0.3},
                        stream=True
                    )
                    
                    for chunk in response:
                        if 'message' in chunk and 'content' in chunk['message']:
                            yield {"type": "text", "content": chunk['message']['content']}
            
            # Final end marker
            yield {"type": "done", "content": ""}
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement: {str(e)}")
            yield {"type": "error", "content": str(e)}
            
    def _search_all_sources(self, 
                           query: str, 
                           use_images: bool, 
                           use_tables: bool, 
                           top_k: int) -> Dict:
        """
        Effectue des recherches dans toutes les sources configurées.
        
        Returns:
            Dict avec les chunks par type
        """
        result = {}
        query_en = translate_query(query=query)
        # Recherche dans la base de texte (toujours activée)
        text_results = self.text_retriever.search_with_context(query_en, top_k=top_k)
        result["text"] = text_results
        
        # Recherche dans la base d'images (si activée)
        if use_images:
            self.logger.info(f"Recherche d'images pour la requête: {query}")
            image_results = self.image_retriever.search(query, top_k=top_k//2)
            
            # Log des images trouvées
            self.logger.info(f"Nombre d'images trouvées: {len(image_results)}")
            if image_results:
                for i, img in enumerate(image_results[:2]):  # Log a few for debug
                    url = img.get("metadata", {}).get("image_url", "")
                    self.logger.info(f"Image {i}: URL={url[:50]}...")
                    # Log the whole image object structure for debugging
                    self.logger.info(f"Image {i} structure: {img}")
            
            # Validation des images avec l'agent de vision
            if self.enable_verification and image_results:
                self.logger.info("Validation des images avec l'agent vision")
                # Ensure all images have properly formatted structure before validation
                normalized_images = []
                for img in image_results:
                    # Make sure metadata exists
                    if "metadata" not in img:
                        img["metadata"] = {}
                    
                    # Ensure image_url is in metadata
                    if "image_url" not in img.get("metadata", {}):
                        url = img.get("url", "")
                        if url:
                            img["metadata"]["image_url"] = url
                    
                    # Make sure there's a documents field
                    if "documents" not in img:
                        img["documents"] = img.get("description", "")
                    
                    normalized_images.append(img)
                
                # Now validate the normalized images
                image_display_agent = ImageDisplayAgent()
                valid_images = image_display_agent.validate_images(query, normalized_images)
                self.logger.info(f"Après validation: {len(valid_images)} images pertinentes")
                
                # Log the valid images for debugging
                for i, img in enumerate(valid_images[:2]):
                    self.logger.info(f"Valid image {i}: {img}")
                
                result["images"] = valid_images
            else:
                # Formater les images sans validation
                self.logger.info("Pas de validation des images")
                formatted_images = []
                for img in image_results:
                    # First check for direct url field
                    url = img.get("url", "")
                    
                    # If not present, try to get from metadata
                    if not url:
                        url = img.get("metadata", {}).get("image_url", "")
                    
                    if url and isinstance(url, str) and url.strip():
                        formatted_image = {
                            "url": url.strip(),
                            "description": img.get("description", img.get("documents", "")),
                            "page": img.get("page", img.get("metadata", {}).get("page", "N/A"))
                        }
                        self.logger.info(f"Formatted image: {formatted_image}")
                        formatted_images.append(formatted_image)
                
                result["images"] = formatted_images
        else:
            result["images"] = []
            
        # Recherche dans la base de tableaux (si activée)
        if use_tables:
            table_results = self.table_retriever.search(query_en, top_k=2)
            result["tables"] = table_results
        else:
            result["tables"] = []
            
        return result
    
    def _verify_chunks(self, query: str, chunks: Dict) -> Dict:
        """
        Vérifie la pertinence des chunks avec l'agent de vérification.
        
        Returns:
            Dict avec les chunks vérifiés par type
        """
        if not self.enable_verification:
            return chunks
        
        verified = {}
        
        # Vérifier les chunks de texte
        if "text" in chunks:
            verified_text = self.verif_agent.verify_chunks(query, chunks["text"])
            verified["text"] = verified_text
        
        # Vérifier les chunks d'images
        if "images" in chunks:
            verified_images = self.verif_agent.verify_chunks(query, chunks["images"])
            verified["images"] = verified_images
        
        # Vérifier les chunks de tableaux
        if "tables" in chunks:
            verified_tables = self.verif_agent.verify_chunks(query, chunks["tables"])
            verified["tables"] = verified_tables
        
        return verified
    def _search_all_sources_parallel(self, query, use_images, use_tables, top_k):
        """Version optimisée avec joblib de la recherche dans toutes les sources"""
        query_en = translate_query(query=query)
        
        # Définir les tâches de recherche
        search_tasks = []
        
        # Recherche texte (toujours activée) - avec cache si activé
        if self.use_joblib_cache:
            search_tasks.append(
                delayed(self._cached_text_search)(query_en, top_k)
            )
        else:
            search_tasks.append(
                delayed(self.text_retriever.search_with_context)(query_en, top_k=top_k)
            )
        
        # Recherche images (si activée) - avec cache si activé
        if use_images:
            if self.use_joblib_cache:
                search_tasks.append(
                    delayed(self._cached_image_search)(query, top_k//2)
                )
            else:
                search_tasks.append(
                    delayed(self.image_retriever.search)(query, top_k=top_k//2)
                )
        
        # Recherche tableaux (si activée) - avec cache si activé
        if use_tables:
            if self.use_joblib_cache:
                search_tasks.append(
                    delayed(self._cached_table_search)(query_en, 3)
                )
            else:
                search_tasks.append(
                    delayed(self.table_retriever.search)(query_en, top_k=3)
                )
        
        # Exécution parallèle avec joblib (optimisé pour les tâches I/O bound)
        try:
            results = Parallel(
                n_jobs=-1,  # Utilise tous les cœurs disponibles
                backend='threading',  # Optimal pour les tâches I/O bound
                prefer='threads'  # Force l'utilisation des threads
            )(search_tasks)
            
            # Mapper les résultats aux sources
            result = {}
            result_index = 0
            
            # Texte (toujours présent)
            result["text"] = results[result_index]
            result_index += 1
            
            # Images (si demandées)
            if use_images:
                image_results = results[result_index]
                result_index += 1
                
                # Post-traitement des images
                if self.enable_verification and image_results:
                    self.logger.info("Validation des images avec l'agent vision")
                    normalized_images = self._normalize_images(image_results)
                    image_display_agent = ImageDisplayAgent()
                    valid_images = image_display_agent.validate_images(query, normalized_images)
                    result["images"] = valid_images
                else:
                    result["images"] = self._format_images_without_validation(image_results)
            else:
                result["images"] = []
            
            # Tableaux (si demandés)
            if use_tables:
                result["tables"] = results[result_index]
            else:
                result["tables"] = []
                
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche parallèle: {str(e)}")
            # Fallback vers la méthode séquentielle
            return self._search_all_sources_fallback(query, use_images, use_tables, top_k)
    
    def _normalize_images(self, image_results):
        """Normalise le format des images pour la validation"""
        normalized_images = []
        for img in image_results:
            if "metadata" not in img:
                img["metadata"] = {}
            
            if "image_url" not in img.get("metadata", {}):
                url = img.get("url", "")
                if url:
                    img["metadata"]["image_url"] = url
            
            if "documents" not in img:
                img["documents"] = img.get("description", "")
            
            normalized_images.append(img)
        return normalized_images
    
    def _format_images_without_validation(self, image_results):
        """Formate les images sans validation"""
        formatted_images = []
        for img in image_results:
            url = img.get("url", "") or img.get("metadata", {}).get("image_url", "")
            
            if url and isinstance(url, str) and url.strip():
                formatted_image = {
                    "url": url.strip(),
                    "description": img.get("description", img.get("documents", "")),
                    "page": img.get("page", img.get("metadata", {}).get("page", "N/A"))
                }
                formatted_images.append(formatted_image)
        return formatted_images
    
    def _search_all_sources_fallback(self, query, use_images, use_tables, top_k):
        """Méthode de fallback en cas d'erreur avec joblib"""
        self.logger.warning("Utilisation de la méthode de fallback pour la recherche")
        # Code original avec concurrent.futures comme backup
        result = {}
        query_en = translate_query(query=query)
        
        search_functions = {
            "text": partial(self.text_retriever.search_with_context, query_en, top_k=top_k),
            "images": partial(self.image_retriever.search, query, top_k=top_k//2) if use_images else None,
            "tables": partial(self.table_retriever.search, query_en, top_k=3) if use_tables else None
        }
        
        active_searches = {k: v for k, v in search_functions.items() if v is not None}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_searches)) as executor:
            future_to_source = {executor.submit(func): source for source, func in active_searches.items()}
            
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result[source] = future.result()
                except Exception as e:
                    self.logger.error(f"Erreur lors de la recherche {source}: {str(e)}")
                    result[source] = []
        
        return result
    
    def _verify_chunks_parallel(self, query, chunks, max_workers=4):
        """Version optimisée avec joblib de la vérification des chunks"""
        if not self.enable_verification:
            return chunks
        
        verified = {}
        
        # Préparer les tâches de vérification par source
        verification_tasks = []
        source_names = []
        
        for source, source_chunks in chunks.items():
            if source_chunks:  # Seulement si il y a des chunks à vérifier
                verification_tasks.append(
                    delayed(self._verify_chunks_for_source)(query, source_chunks)
                )
                source_names.append(source)
        
        if not verification_tasks:
            return chunks
        
        try:
            # Exécution parallèle avec joblib
            results = Parallel(
                n_jobs=min(max_workers, len(verification_tasks)),
                backend='threading',  # Pour les appels API LLM
                prefer='threads'
            )(verification_tasks)
            
            # Reconstruire le dictionnaire des résultats
            for source_name, verified_chunks in zip(source_names, results):
                verified[source_name] = verified_chunks
            
            # Ajouter les sources vides
            for source in chunks:
                if source not in verified:
                    verified[source] = []
            
            return verified
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification parallèle: {str(e)}")
            # Fallback vers la vérification séquentielle
            return self._verify_chunks_fallback(query, chunks, max_workers)
    
    def _verify_chunks_for_source(self, query, chunks):
        """Vérifie tous les chunks d'une source donnée"""
        verified_chunks = []
        
        # Traiter les chunks par petits lots pour optimiser les appels API
        batch_size = 3
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            for chunk in batch:
                try:
                    is_valid = self.verif_agent.verify_chunks(query, [chunk])
                    if is_valid and len(is_valid) > 0:
                        verified_chunks.extend(is_valid)
                except Exception as e:
                    self.logger.error(f"Erreur de vérification pour un chunk: {str(e)}")
                    # En cas d'erreur, on garde le chunk (fallback conservateur)
                    verified_chunks.append(chunk)
        
        return verified_chunks
    
    def _verify_chunks_fallback(self, query, chunks, max_workers=4):
        """Méthode de fallback pour la vérification des chunks"""
        self.logger.warning("Utilisation de la méthode de fallback pour la vérification")
        verified = {}
        
        # Collecter tous les chunks à vérifier
        all_chunks = []
        chunk_sources = {}
        
        for source, source_chunks in chunks.items():
            for chunk in source_chunks:
                all_chunks.append(chunk)
                chunk_sources[id(chunk)] = source
        
        # Fonction pour vérifier un seul chunk
        def verify_single_chunk(chunk):
            try:
                result = self.verif_agent.verify_chunks(query, [chunk])
                return (chunk, result and len(result) > 0)
            except Exception as e:
                self.logger.error(f"Erreur de vérification: {str(e)}")
                return (chunk, True)  # Fallback conservateur
        
        # Vérifier en parallèle avec concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(verify_single_chunk, all_chunks))
        
        # Réorganiser les résultats par source
        for chunk, is_valid in results:
            source = chunk_sources[id(chunk)]
            if source not in verified:
                verified[source] = []
            
            if is_valid:
                verified[source].append(chunk)
        
        return verified
    def _prepare_context(self, verified_chunks: Dict) -> str:
        """
        Prépare un contexte combiné pour la génération de réponse.
        
        Returns:
            Contexte formaté
        """
        context = "CONTEXTE PERTINENT POUR RÉPONDRE À LA QUESTION:\n\n"
        
        # Ajouter le texte
        if "text" in verified_chunks and verified_chunks["text"]:
            context += "INFORMATIONS TEXTUELLES:\n"
            for i, chunk in enumerate(verified_chunks["text"]):
                source_id = f"[Source {i+1}]"
                regulation = chunk.get('regulation', 'Inconnu')
                page = chunk.get('section_id', 'Inconnu')
                content = chunk.get('content', '')
                
                context += f"{source_id} {regulation}, page {page}:\n{content}\n\n"
        
        # Ajouter les descriptions d'images
        if "images" in verified_chunks and verified_chunks["images"]:
            context += "INFORMATIONS VISUELLES:\n"
            for i, img in enumerate(verified_chunks["images"]):
                description = img.get('description', img.get('documents', ''))
                if description and description.strip() and description.strip() != "Aucune description":
                    context += f"[Image {i+1}] {description}\n\n"
                else:
                    context += f"[Image {i+1}] Image de la page {img.get('page', 'N/A')} (pas de description détaillée disponible)\n\n"
        
        # Ajouter les tableaux
        if "tables" in verified_chunks and verified_chunks["tables"]:
            context += "DONNÉES TABULAIRES:\n"
            for i, table in enumerate(verified_chunks["tables"]):
                context += f"[Tableau {i+1}]\n{table.get('documents', '')}\n\n"
        
        return context
    
    def _generate_response(self, query: str, context: str, use_conversation_context: bool = True) -> str:
        """
        Génère une réponse basée sur le contexte.
        
        Args:
            query: Question de l'utilisateur
            context: Contexte de recherche RAG
            use_conversation_context: Utiliser le contexte conversationnel
        
        Returns:
            Réponse générée
        """
        # Vérifier si des images sont mentionnées dans le contexte
        has_images = "[Image " in context
        
        # Construire le contexte final avec la mémoire conversationnelle
        final_context = context
        if use_conversation_context and self.conversation_memory:
            conversation_context = self.conversation_memory.get_context_for_query(query)
            if conversation_context.strip():
                final_context = f"{conversation_context}\n\n{context}"
        
        prompt = f"""
        Vous êtes un expert en réglementations automobiles. Vous répondrez à la question suivante en vous fondant STRICTEMENT sur les informations fournies dans le contexte (texte, tableaux, images).
        
        🔹 QUESTION :
        {query}
        
        🔹 CONTEXTE FOURNI :
        {final_context}
        
        🔹 CONSIGNES :
        1. **Sources exclusives**  
           Ne vous appuyez que sur le contexte ci-dessus. Ne faites aucune spéculation extérieure.
        2. **Langage et ton**  
           Utilisez un style factuel, précis et adapté aux documents réglementaires.
        3. **Analyse croisée**  
           - Considérez que textes, tableaux et images peuvent se compléter.  
           - Si un tableau ou une image indique des codes ou abréviations (B, C, D, …), vérifiez dans le texte toute précision ou valeur chiffrée correspondante.
        4. **Structure de la réponse**  
           - Organisez votre réponse en paragraphes clairs et, si utile, en listes à puces.  
           - Introduisez chaque partie par un titre en gras ou une accroche courte.
        5. **Gestion des informations manquantes**  
           Si le contexte ne permet pas de répondre de façon satisfaisante, indiquez-le explicitement.
        6. **Citations internes**  
           Référencez vos sources internes au contexte ainsi :  
           - Pour un passage textuel : [Source X]  
           - Pour une image : [Image X]  
           - Pour un tableau : [Tableau X]
        """
        
        # Ajouter une instruction spécifique pour les images si nécessaire
        if has_images:
            prompt += """
        7. **Utilisation des images**
           - Toutes les images mentionnées sont disponibles et ont des descriptions.
           - Utilisez ces descriptions d'images comme références légitimes au même titre que les textes.
           - NE JAMAIS indiquer que "les images n'ont pas de description et ne peuvent pas être utilisées comme référence".
           - Si vous faites référence à une image, citez-la avec [Image X].
        """
        
        prompt += """
        
        🔹 RÉPONSE :
        """
        
        if self.llm_client['type'] == 'mistral':
            response = self.llm_client['client'].chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048
            )
            return response.choices[0].message.content
        else:  # ollama
            response = self.llm_client['client'].chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={'temperature': 0.1}
            )
            return response['message']['content']
    
    def _extract_sources(self, text_chunks: List[Dict]) -> List[Dict]:
        """
        Extrait les informations de sources à partir des chunks de texte.
        Version basique.
        """
        sources = []
        
        for i, chunk in enumerate(text_chunks):
            content = chunk.get('documents', chunk.get('content', ''))
            metadata = chunk.get('metadata', {})
            
            # Informations basiques
            regulation = chunk.get('documents', chunk.get('document', ''))
            section = metadata.get('section', f'Section {i+1}')
            pages = chunk.get('documents', chunk.get('chunk_index', ''))
            
            # Si pages est une liste, prendre le premier élément
            if isinstance(pages, list) and pages:
                pages = pages[0]
            
            source = {
                'regulation': regulation,
                'section': section,
                'pages': str(pages),
                'text': content
            }
            
            sources.append(source)
        
        return sources

    def _generate_content_hash(self, content: str) -> str:
        """Génère un hash du contenu pour la mise en surbrillance"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    # ======== MÉTHODES DE GESTION DE MÉMOIRE CONVERSATIONNELLE ========
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la conversation actuelle"""
        if not self.conversation_memory:
            return {"conversation_memory": "disabled"}
        
        return self.conversation_memory.get_conversation_stats()
    
    def clear_conversation_memory(self) -> None:
        """Efface toute la mémoire conversationnelle"""
        if self.conversation_memory:
            self.conversation_memory.clear_memory()
            self.logger.info("Mémoire conversationnelle effacée")
    
    def export_conversation(self) -> Dict[str, Any]:
        """Exporte la conversation complète"""
        if not self.conversation_memory:
            return {"error": "Conversation memory disabled"}
        
        return self.conversation_memory.export_conversation()
    
    def get_conversation_context_preview(self, query: str) -> str:
        """Prévisualise le contexte conversationnel pour une requête (utile pour debugging)"""
        if not self.conversation_memory:
            return "Mémoire conversationnelle désactivée"
        
        return self.conversation_memory.get_context_for_query(query)

    def _retry_with_exponential_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self.retry_config['max_retries']):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a retryable error
                if any(error_type in error_str for error_type in [
                    'service unavailable', '503', 'timeout', 'connection', 
                    'rate limit', '429', 'server error', '500', '502', '504'
                ]):
                    if attempt < self.retry_config['max_retries'] - 1:
                        delay = min(
                            self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt),
                            self.retry_config['max_delay']
                        )
                        
                        if self.retry_config['jitter']:
                            delay *= (0.5 + random.random() * 0.5)
                            
                        self.logger.warning(f"API error (attempt {attempt + 1}/{self.retry_config['max_retries']}): {e}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                        continue
                
                # Non-retryable error or max retries reached
                break
        
        raise last_exception

    def _generate_response_stream_with_fallback(self, query: str, context: str, conversation_context: str = ""):
        """Generate response with fallback to alternative provider if current fails"""
        try:
            # Try current provider first
            yield from self._generate_response_stream(query, context, conversation_context)
        except Exception as e:
            self.logger.error(f"Primary provider {self.llm_provider} failed: {str(e)}")
            
            # Try fallback provider if available
            fallback_provider = self.provider_fallback.get(self.llm_provider)
            if fallback_provider:
                self.logger.info(f"Attempting fallback to {fallback_provider}")
                try:
                    # Temporarily switch provider
                    original_provider = self.llm_provider
                    original_client = self.llm_client
                    
                    self.llm_provider = fallback_provider
                    self._init_llm_client()
                    
                    yield from self._generate_response_stream(query, context, conversation_context)
                    
                except Exception as fallback_error:
                    self.logger.error(f"Fallback provider {fallback_provider} also failed: {str(fallback_error)}")
                    # Restore original provider
                    self.llm_provider = original_provider
                    self.llm_client = original_client
                    
                    yield f"Je rencontre des difficultés techniques avec les services IA. Erreur principale: {str(e)}. Erreur de secours: {str(fallback_error)}. Veuillez réessayer dans quelques instants."
                finally:
                    # Restore original provider settings
                    self.llm_provider = original_provider
                    self.llm_client = original_client
            else:
                yield f"Service temporairement indisponible. Erreur: {str(e)}. Veuillez réessayer dans quelques instants."