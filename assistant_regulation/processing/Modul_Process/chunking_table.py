import pdfplumber
from typing import List, Dict

def extract_context(page, table_bbox, context_bbox):
    """Extrait le texte autour d'un tableau avec mise en page préservée"""
    context_area = page.within_bbox(context_bbox)
    chars = sorted(context_area.chars, key=lambda c: (c['top'], c['x0']))
    
    text = []
    prev_char = None
    
    for char in chars:
        # Filtrer les caractères du tableau
        if (table_bbox[0] <= char['x0'] <= table_bbox[2] and 
            table_bbox[1] <= char['top'] <= table_bbox[3]):
            continue
            
        # Ajouter un espace si nécessaire
        if prev_char:
            same_line = abs(char['top'] - prev_char['top']) < 2
            x_gap = char['x0'] - prev_char['x1']
            
            if same_line and x_gap > 3:  # Seuil d'espacement
                text.append(' ')
        
        # Ajouter un saut de ligne si nécessaire
        if prev_char and char['top'] > prev_char['bottom'] + 2:
            text.append('\n')
            
        text.append(char['text'])
        prev_char = char
    
    return ''.join(text).strip()

def extract_tables(pdf_path: str, context_margin: int = 50) -> List[Dict]:
    """Extrait les tableaux avec contexte environnant"""
    import os
    tables = []
    # Extraire le nom complet du fichier avec extension
    document_name = os.path.basename(pdf_path)
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            detected_tables = page.find_tables()
            
            for table in detected_tables:
                # Définir la zone de contexte
                x0, top, x1, bottom = table.bbox
                ctx_bbox = (
                    max(x0 - context_margin, 0),
                    max(top - context_margin, 0),
                    min(x1 + context_margin, page.width),
                    min(bottom + context_margin, page.height)
                )
                
                # Extraire les données
                tables.append({
                    "page_number": page_num + 1,
                    "content": table.extract(),
                    "context": extract_context(page, table.bbox, ctx_bbox),
                    "bbox": table.bbox,
                    "type": "table",
                    "document_source": pdf_path,
                    "document_name": document_name
                })
    
    return tables