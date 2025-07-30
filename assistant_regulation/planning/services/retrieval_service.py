from typing import Dict

from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever
from assistant_regulation.planning.sync.lang_py import translate_query


class RetrievalService:
    """Centralise la recherche dans les différentes bases (texte, image, tableau).

    Cette couche ne contient *aucune* logique de vérification ou de mise en forme
    avancée ; elle se contente d'interroger les retrievers et de renvoyer les
    résultats bruts. Elle peut donc être testée indépendamment avec des mocks
    de retrievers.
    """

    def __init__(
        self,
        text_retriever: SimpleTextRetriever | None = None,
        image_retriever: ImageRetriever | None = None,
        table_retriever: TableRetriever | None = None,
    ) -> None:
        self.text_retriever = text_retriever or SimpleTextRetriever()
        self.image_retriever = image_retriever or ImageRetriever()
        self.table_retriever = table_retriever or TableRetriever()

    # ---------------------------------------------------------------------
    # API public
    # ---------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
    ) -> Dict:
        """Retourne un dictionnaire {text, images, tables}.

        Les clés *images* ou *tables* contiennent des listes vides si la source
        n'est pas désirée.
        """
        query_en = translate_query(query=query)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Prépare les tâches parallèles
        tasks: Dict[str, any] = {}
        with ThreadPoolExecutor(max_workers=16) as executor:
            # Texte (toujours)
            tasks["text"] = executor.submit(
                self.text_retriever.search_with_context, query_en, top_k=top_k
            )

            # Images
            if use_images:
                tasks["images"] = executor.submit(
                    self.image_retriever.search, query, top_k=max(1, top_k // 2)
                )
            else:
                tasks["images"] = None

            # Tables
            if use_tables:
                tasks["tables"] = executor.submit(
                    self.table_retriever.search, query_en, top_k=2
                )
            else:
                tasks["tables"] = None

            # Collecte des résultats
            results: Dict[str, list] = {"text": [], "images": [], "tables": []}
            for name, future in tasks.items():
                if future is None:
                    continue
                try:
                    results[name] = future.result()
                except Exception as e:
                    # En cas d'erreur, on logge et continue
                    results[name] = []

        return results 

    # ---------------------------------------------------------------------
    # Délégation des méthodes avancées de BaseRetriever
    # ---------------------------------------------------------------------
    def search_by_regulation(self, regulation_code: str, query: str, top_k: int = 10, search_type: str = 'hybrid', alpha: float = 0.7):
        return self.text_retriever.search_by_regulation(regulation_code, query, top_k, search_type, alpha)

    def get_all_chunks_for_regulation(self, regulation_code: str):
        return self.text_retriever.get_all_chunks_for_regulation(regulation_code)

    def get_available_regulations(self):
        return self.text_retriever.get_available_regulations()

    def get_regulation_stats(self, regulation_code: str):
        return self.text_retriever.get_regulation_stats(regulation_code)

    def search_multiple_regulations(self, regulation_codes, query, top_k = 5, search_type = 'hybrid'):
        return self.text_retriever.search_multiple_regulations(regulation_codes, query, top_k, search_type)

    def compare_regulations(self, regulation_codes, query, top_k = 5):
        return self.text_retriever.compare_regulations(regulation_codes, query, top_k)

    def get_regulation_intersection(self, regulation_codes, query):
        return self.text_retriever.get_regulation_intersection(regulation_codes, query) 