import chromadb
from typing import List, Dict
import numpy as np
import ollama
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from functools import lru_cache

# Définir le chemin de la base de données de manière portable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT,"DB", "chroma_db")

def batch_processing(collection, ids, documents, embeddings, metadatas, batch_size=5000):
    """Stocke les données par lots pour éviter l'erreur de dépassement de batch"""
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_docs = documents[i:i+batch_size]
        batch_embeds = embeddings[i:i+batch_size]
        batch_meta = metadatas[i:i+batch_size]

        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_embeds,
            metadatas=batch_meta
        )
class BaseRetriever:
    def __init__(self, collection_name: str):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        # Initialisation TF-IDF
        self.vectorizer = TfidfVectorizer() 
        self._tfidf_matrix = None  # Cache sparse matrix
        self._doc_ids_cache = []
        self._all_docs_cache = []

    # ------------------------------------------------------------------
    # Utils de cache
    # ------------------------------------------------------------------
    def _ensure_tfidf_cache(self):
        """Construit ou met à jour le cache TF-IDF si nécessaire."""
        current_docs = self.collection.get()
        all_docs = current_docs['documents']
        doc_ids = current_docs['ids']

        # --- Gestion collection vide ---------------------------------
        # Si la base est vide, on ne peut pas ajuster le vectoriseur.
        # On réinitialise simplement le cache et on sort.
        if not all_docs:
            self._tfidf_matrix = None
            self._all_docs_cache = []
            self._doc_ids_cache = []
            return
        # -------------------------------------------------------------

        # Rebuild only if nb docs changed
        if self._tfidf_matrix is None or len(all_docs) != len(self._all_docs_cache):
            self._all_docs_cache = all_docs
            self._doc_ids_cache = doc_ids
            # Fit TF-IDF once
            self._tfidf_matrix = self.vectorizer.fit_transform(all_docs)

    def _get_embedding(self, text: str) -> List[float]:
        """Génère les embeddings selon le provider disponible"""
        @lru_cache(maxsize=1024)
        def _cached_ollama(prompt: str):
            resp = ollama.embeddings(model="mxbai-embed-large:latest", prompt=prompt)
            return tuple(resp["embedding"])  # Tuple pour être hashable

        return list(_cached_ollama(text))

    def _store_data(self, ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        """Méthode interne pour le stockage générique"""
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
    def search(self, query: str, search_type: str = 'hybrid', top_k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """
        Recherche unifiée avec différents modes :
        - 'vector' : Recherche sémantique pure
        - 'text' : Recherche textuelle TF-IDF
        - 'hybrid' : Combinaison des deux (alpha = poids vectoriel)
        """
        if search_type == 'vector':
            return self._vector_search(query, top_k)
        elif search_type == 'text':
            return self._text_search(query, top_k)
        elif search_type == 'hybrid':
            return self._hybrid_search(query, top_k, alpha)
        else:
            raise ValueError("Type de recherche invalide. Choisir 'vector', 'text' ou 'hybrid'.")

    def search_with_context(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Recherche avec contexte - alias pour la recherche hybride
        Utilisée par RetrievalService pour maintenir la compatibilité
        """
        return self.search(query, search_type='hybrid', top_k=top_k, alpha=0.7)

    def _vector_search(self, query: str, top_k: int) -> List[Dict]:
        """Recherche par similarité vectorielle"""
        query_embedding = self._get_embedding(query)
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            # Un résultat vide peut arriver si la base est vide
            if not results or not results.get('ids') or len(results['ids'][0]) == 0:
                return []
            return self._format_results(results)
        except Exception:
            # Par défaut, en cas d'erreur (par ex. base vide), on renvoie une liste vide
            return []

    def _text_search(self, query: str, top_k: int) -> List[Dict]:
        """Recherche textuelle avec TF-IDF"""
        # Assure le cache (re)calculé une seule fois par changements
        self._ensure_tfidf_cache()

        # Si la matrice TF-IDF est vide, on n'a aucun résultat possible
        if self._tfidf_matrix is None or self._tfidf_matrix.shape[0] == 0:
            return []

        tfidf_matrix = self._tfidf_matrix
        doc_ids = self._doc_ids_cache
        query_vec = self.vectorizer.transform([query])

        # Calcul similarité
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        return [{
            'id': doc_ids[i],
            'score': float(similarities[i]),
            'metadata': self.collection.get(ids=[doc_ids[i]])['metadatas'][0],
            'documents': self._all_docs_cache[i]
        } for i in top_indices]

    def _hybrid_search(self, query: str, top_k: int, alpha: float) -> List[Dict]:
        """Recherche hybride vectorielle + textuelle"""
        vector_results = self._vector_search(query, top_k*2)
        text_results = self._text_search(query, top_k*2)

        # Si aucune source ne contient de documents, on renvoie immédiatement
        if not vector_results and not text_results:
            return []

        # Fusion des résultats
        combined = {}
        for res in vector_results:
            combined[res['id']] = {
                'vector_score': res['score'],
                'text_score': 0,
                'metadata': res['metadata'],
                'documents': res['documents']
            }
        
        for res in text_results:
            if res['id'] in combined:
                combined[res['id']]['text_score'] = res['score']
            else:
                combined[res['id']] = {
                    'vector_score': 0,
                    'text_score': res['score'],
                    'metadata': res['metadata'],
                    'documents': res['documents']
                }

        # Normalisation et combinaison
        max_vec = max([v['vector_score'] for v in combined.values()]) or 1
        max_text = max([v['text_score'] for v in combined.values()]) or 1
        
        for key in combined:
            combined[key]['combined_score'] = (
                alpha * (combined[key]['vector_score'] / max_vec) +
                (1 - alpha) * (combined[key]['text_score'] / max_text))
            
        return sorted(combined.values(), key=lambda x: x['combined_score'], reverse=True)[:top_k]

    def _format_results(self, chroma_results) -> List[Dict]:
        """Formate les résultats ChromaDB"""
        return [{
            'id': id,
            'score': 1 - distance,  # Conversion distance -> similarité
            'metadata': metadata,
            'documents': documents
        } for id, metadata,documents,distance in zip(
            chroma_results['ids'][0],
            chroma_results['metadatas'][0],
            chroma_results['documents'][0],
            chroma_results['distances'][0]
        )]

    # ------------------------------------------------------------------
    # Nouvelles fonctionnalités pour la recherche par réglementation
    # ------------------------------------------------------------------
    
    def search_by_regulation(self, regulation_code: str, query: str, top_k: int = 10, search_type: str = 'hybrid', alpha: float = 0.7) -> List[Dict]:
        """
        Recherche ciblée dans une réglementation spécifique
        
        Args:
            regulation_code: Code de la réglementation (ex: 'R003', 'R107', 'ECE R46')
            query: Requête de recherche
            top_k: Nombre de résultats à retourner
            search_type: Type de recherche ('vector', 'text', 'hybrid')
            alpha: Poids de la recherche vectorielle pour le mode hybride
            
        Returns:
            Liste des résultats filtrés par réglementation
        """
        # Normaliser le code de réglementation
        regulation_code = regulation_code.upper()
        # Ne pas ajouter 'R' si c'est déjà un code ECE complet
        if not regulation_code.startswith('R') and not regulation_code.startswith('ECE'):
            regulation_code = 'R' + regulation_code
        
        # Effectuer la recherche normale avec plus de résultats
        all_results = self.search(query, top_k=top_k*3, search_type=search_type, alpha=alpha)
        
        # Filtrer par réglementation
        filtered_results = []
        for result in all_results:
            metadata = result.get('metadata', {})
            result_regulation = metadata.get('regulation_code', '').upper()
            
            if result_regulation == regulation_code:
                filtered_results.append(result)
                
            # Arrêter si on a assez de résultats
            if len(filtered_results) >= top_k:
                break
        
        return filtered_results

    def get_all_chunks_for_regulation(self, regulation_code: str) -> List[Dict]:
        """
        Récupère tous les chunks d'une réglementation pour résumé complet
        
        Args:
            regulation_code: Code de la réglementation (ex: 'R003', 'R107')
            
        Returns:
            Liste de tous les chunks de la réglementation
        """
        # Normaliser le code de réglementation
        regulation_code = regulation_code.upper()
        # Ne pas ajouter 'R' si c'est déjà un code ECE complet
        if not regulation_code.startswith('R') and not regulation_code.startswith('ECE'):
            regulation_code = 'R' + regulation_code
        
        # Récupérer tous les documents de la collection
        all_data = self.collection.get()
        
        # Filtrer par réglementation
        regulation_chunks = []
        for i, metadata in enumerate(all_data['metadatas']):
            if metadata.get('regulation_code', '').upper() == regulation_code:
                regulation_chunks.append({
                    'id': all_data['ids'][i],
                    'metadata': metadata,
                    'documents': all_data['documents'][i],
                    'page_no': metadata.get('page_no', 0)
                })
        
        # Trier par numéro de page pour avoir un ordre logique
        regulation_chunks.sort(key=lambda x: x.get('page_no', 0))
        
        return regulation_chunks

    def get_available_regulations(self) -> List[str]:
        """
        Retourne la liste des réglementations disponibles dans la base
        
        Returns:
            Liste des codes de réglementation disponibles
        """
        # Récupérer toutes les métadonnées
        all_data = self.collection.get()
        
        # Extraire les codes de réglementation uniques
        regulation_codes = set()
        for metadata in all_data['metadatas']:
            reg_code = metadata.get('regulation_code', '')
            if reg_code and reg_code != 'UNKNOWN':
                regulation_codes.add(reg_code.upper())
        
        return sorted(list(regulation_codes))

    def get_regulation_stats(self, regulation_code: str) -> Dict:
        """
        Retourne des statistiques sur une réglementation
        
        Args:
            regulation_code: Code de la réglementation
            
        Returns:
            Dictionnaire avec les statistiques
        """
        # Normaliser le code
        regulation_code = regulation_code.upper()
        # Ne pas ajouter 'R' si c'est déjà un code ECE complet
        if not regulation_code.startswith('R') and not regulation_code.startswith('ECE'):
            regulation_code = 'R' + regulation_code
            
        chunks = self.get_all_chunks_for_regulation(regulation_code)
        
        if not chunks:
            return {'error': f'Réglementation {regulation_code} non trouvée'}
        
        # Calculer les statistiques
        pages = set()
        total_content_length = 0
        
        for chunk in chunks:
            pages.add(chunk.get('page_no', 0))
            total_content_length += len(chunk.get('documents', ''))
        
        return {
            'regulation_code': regulation_code,
            'total_chunks': len(chunks),
            'total_pages': len(pages),
            'total_content_length': total_content_length,
            'average_chunk_size': total_content_length / len(chunks) if chunks else 0,
            'pages_covered': sorted(list(pages))
        }

    def search_multiple_regulations(self, regulation_codes: List[str], query: str, top_k: int = 5, search_type: str = 'hybrid') -> Dict[str, List[Dict]]:
        """
        Recherche dans plusieurs réglementations simultanément
        
        Args:
            regulation_codes: Liste des codes de réglementation
            query: Requête de recherche
            top_k: Nombre de résultats par réglementation
            search_type: Type de recherche
            
        Returns:
            Dictionnaire avec les résultats par réglementation
        """
        results = {}
        
        for reg_code in regulation_codes:
            # Normaliser le code
            reg_code_normalized = reg_code.upper()
            if not reg_code_normalized.startswith('R') and not reg_code_normalized.startswith('ECE'):
                reg_code_normalized = 'R' + reg_code_normalized
            
            # Rechercher dans cette réglementation
            reg_results = self.search_by_regulation(reg_code_normalized, query, top_k, search_type)
            results[reg_code_normalized] = reg_results
        
        return results

    def compare_regulations(self, regulation_codes: List[str], query: str, top_k: int = 5) -> Dict:
        """
        Compare plusieurs réglementations sur un sujet donné
        
        Args:
            regulation_codes: Liste des codes de réglementation à comparer
            query: Sujet de comparaison
            top_k: Nombre de résultats par réglementation
            
        Returns:
            Dictionnaire structuré pour la comparaison
        """
        # Rechercher dans chaque réglementation
        regulation_results = self.search_multiple_regulations(regulation_codes, query, top_k)
        
        # Structurer pour la comparaison
        comparison_data = {
            'query': query,
            'regulations_compared': regulation_codes,
            'results_by_regulation': regulation_results,
            'comparison_summary': self._generate_comparison_summary(regulation_results, query)
        }
        
        return comparison_data

    def _generate_comparison_summary(self, regulation_results: Dict[str, List[Dict]], query: str) -> Dict:
        """
        Génère un résumé de comparaison entre réglementations
        
        Args:
            regulation_results: Résultats par réglementation
            query: Sujet de comparaison
            
        Returns:
            Résumé structuré de la comparaison
        """
        summary = {
            'regulations_with_results': [],
            'regulations_without_results': [],
            'total_chunks_found': 0,
            'coverage_analysis': {}
        }
        
        for reg_code, results in regulation_results.items():
            if results:
                summary['regulations_with_results'].append(reg_code)
                summary['total_chunks_found'] += len(results)
                
                # Analyser la couverture
                pages_covered = set()
                for result in results:
                    pages_covered.add(result['metadata'].get('page_no', 0))
                
                summary['coverage_analysis'][reg_code] = {
                    'chunks_found': len(results),
                    'pages_covered': sorted(list(pages_covered)),
                    'avg_relevance': sum(result.get('score', 0) for result in results) / len(results) if results else 0
                }
            else:
                summary['regulations_without_results'].append(reg_code)
        
        return summary

    def get_regulation_intersection(self, regulation_codes: List[str], query: str) -> Dict:
        """
        Trouve les éléments communs entre plusieurs réglementations
        
        Args:
            regulation_codes: Liste des codes de réglementation
            query: Requête de recherche
            
        Returns:
            Analyse des éléments communs
        """
        regulation_results = self.search_multiple_regulations(regulation_codes, query, top_k=10)
        
        # Analyser les termes communs
        common_terms = set()
        regulation_contents = {}
        
        for reg_code, results in regulation_results.items():
            if results:
                # Extraire le contenu textuel
                content = ' '.join([result['documents'] for result in results])
                regulation_contents[reg_code] = content.lower()
                
                # Extraire les termes (simplification)
                terms = set(content.lower().split())
                if not common_terms:
                    common_terms = terms
                else:
                    common_terms = common_terms.intersection(terms)
        
        return {
            'query': query,
            'regulations_analyzed': regulation_codes,
            'common_terms': list(common_terms)[:20],  # Limiter pour lisibilité
            'regulation_contents': regulation_contents,
            'intersection_analysis': self._analyze_intersection(regulation_contents, query)
        }

    def _analyze_intersection(self, regulation_contents: Dict[str, str], query: str) -> Dict:
        """
        Analyse l'intersection entre les contenus des réglementations
        
        Args:
            regulation_contents: Contenu par réglementation
            query: Requête originale
            
        Returns:
            Analyse de l'intersection
        """
        analysis = {
            'similar_concepts': [],
            'unique_to_regulation': {},
            'coverage_comparison': {}
        }
        
        # Analyser les concepts uniques par réglementation
        for reg_code, content in regulation_contents.items():
            words = set(content.split())
            
            # Trouver les mots uniques à cette réglementation
            unique_words = words.copy()
            for other_reg, other_content in regulation_contents.items():
                if other_reg != reg_code:
                    unique_words -= set(other_content.split())
            
            analysis['unique_to_regulation'][reg_code] = list(unique_words)[:10]  # Limiter
            
            # Analyser la couverture du sujet
            query_words = set(query.lower().split())
            coverage = len(query_words.intersection(words)) / len(query_words) if query_words else 0
            analysis['coverage_comparison'][reg_code] = coverage
        
        return analysis