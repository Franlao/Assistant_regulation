from typing import List, Dict
import pdfplumber

class PageTracker:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.page_map = []
        self.full_text = ""
        self._build_page_map()

    def _build_page_map(self):
        """Construit la cartographie caractère -> page"""
        with pdfplumber.open(self.pdf_path) as pdf:
            current_pos = 0
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() + "\n"
                text_length = len(text)
                
                self.page_map.append({
                    "start": current_pos,
                    "end": current_pos + text_length,
                    "page_number": page_num + 1,
                    "text": text
                })
                
                self.full_text += text
                current_pos += text_length

    def get_page_range(self, chunk_text: str) -> Dict:
        """Trouve l'intervalle de pages pour un chunk donné"""
        start = self.full_text.find(chunk_text)
        end = start + len(chunk_text)
        
        if start == -1:
            return {"start": None, "end": None}

        start_page = None
        end_page = None
        
        for page in self.page_map:
            if start >= page["start"] and start < page["end"]:
                start_page = page["page_number"]
            if end >= page["start"] and end < page["end"]:
                end_page = page["page_number"]
            if start_page and end_page:
                break

        return {
            "start": start_page,
            "end": end_page or end_page
        }