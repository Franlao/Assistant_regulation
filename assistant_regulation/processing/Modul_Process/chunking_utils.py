import re
from pathlib import Path

def extract_document_metadata(file_path: str) -> dict:
    """Extrait le nom du document et le numéro de réglementation"""
    path = Path(file_path)
    stem = path.stem  # Enlève l'extension
    full_name = path.name  # Nom complet avec extension
    
    # Extraction du code de réglementation (ex: R107)
    regulation_match = re.search(r'r\d+', stem, re.IGNORECASE)
    regulation = regulation_match.group().upper() if regulation_match else "INCONNU"
    
    # Garder le nom complet du fichier au lieu du nom nettoyé
    doc_name = full_name
    
    return {
        "document_name": doc_name,
        "regulation_code": regulation
    }

def process_pdf_directory(directory_path: str, processor_function) -> list:
    """Traite tous les PDF d'un dossier avec une fonction de traitement"""
    pdf_files = list(Path(directory_path).glob("*.pdf"))
    all_chunks = []
    
    for pdf_file in pdf_files:
        metadata = extract_document_metadata(str(pdf_file))
        chunks = processor_function(str(pdf_file))
        for chunk in chunks:
            chunk.update(metadata)
        all_chunks.extend(chunks)
    
    return all_chunks