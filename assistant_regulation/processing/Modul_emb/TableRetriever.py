from .BaseRetriever import BaseRetriever, batch_processing
from typing import List, Dict
import json
import uuid

class TableRetriever(BaseRetriever):
    def __init__(self):
        super().__init__("pdf_tables")
    
    def store_chunks(self, chunks: List[Dict]):
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            context_text = f"{chunk['context']}\n{str(chunk['content'])}"
            metadata = {
                'page_number': chunk['page_number'],
                'bbox': json.dumps(chunk['bbox']),
                'type': 'table',
                'document_source': chunk.get('document_source', ''),
                'document_name': chunk.get('document_name', ''),
                'regulation_code': chunk.get('regulation_code', '')
            }

            ids.append(str(uuid.uuid4()))
            documents.append(context_text)
            embeddings.append(self._get_embedding(context_text))
            metadatas.append(metadata)

        batch_processing(self.collection, ids, documents, embeddings, metadatas)