from __future__ import annotations

from typing import Dict, List


class ContextBuilderService:
    """Assemble un bloc de contexte linéaire à partir de chunks multimodaux.

    • Concatène le contenu du texte, des tableaux et la description des images.
    • Peut être étendue plus tard (format Markdown, mise en forme citations, etc.)
    """

    # ------------------------------------------------------------------
    def build_context(self, chunks: Dict) -> str:
        parts: List[str] = []

        # Texte
        for txt in chunks.get("text", []):
            content = (
                txt.get("content")
                or txt.get("documents")
                or txt.get("text")
            )
            if content:
                parts.append(content)

        # Tableaux
        for tbl in chunks.get("tables", []):
            content = tbl.get("content") or tbl.get("documents")
            if content:
                parts.append(content)

        # Images (on utilise la description)
        for img in chunks.get("images", []):
            desc = img.get("description") or img.get("documents")
            if desc:
                parts.append(desc)

        # Séparateur double saut de ligne pour rester simple
        return "\n\n".join(parts) 