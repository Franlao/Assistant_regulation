#!/usr/bin/env python3
"""
Utilitaire d'aide à la migration vers le nouveau système i18n
Identifie automatiquement les textes hardcodés dans les fichiers Python
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Tuple

class I18nMigrationHelper:
    """Assistant pour migrer vers le nouveau système d'internationalisation"""

    def __init__(self):
        self.hardcoded_patterns = [
            # Patterns pour identifier les textes hardcodés
            r'st\.(title|header|subheader|write|success|error|warning|info|caption)\s*\(\s*["\']([^"\']{10,})["\']',
            r'st\.selectbox\s*\(\s*["\']([^"\']{5,})["\']',
            r'st\.text_input\s*\(\s*["\']([^"\']{5,})["\']',
            r'st\.button\s*\(\s*["\']([^"\']{5,})["\']',
            r'st\.toggle\s*\(\s*["\']([^"\']{5,})["\']',
            r'st\.slider\s*\(\s*["\']([^"\']{5,})["\']',
            r'st\.markdown\s*\(\s*["\']([^"\']{15,})["\']',
        ]

    def scan_file(self, file_path: Path) -> List[Tuple[str, str, int]]:
        """
        Scanne un fichier pour trouver les textes hardcodés

        Args:
            file_path: Chemin vers le fichier à scanner

        Returns:
            Liste de tuples (fonction, texte, ligne)
        """
        hardcoded_texts = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in self.hardcoded_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        function = match.group(1) if match.lastindex >= 1 else "unknown"
                        text = match.group(2) if match.lastindex >= 2 else match.group(1)

                        # Filtrer les textes trop techniques ou non-traduisibles
                        if self._should_translate(text):
                            hardcoded_texts.append((function, text, line_num))

        except (UnicodeDecodeError, FileNotFoundError) as e:
            print(f"Erreur lors de la lecture de {file_path}: {e}")

        return hardcoded_texts

    def _should_translate(self, text: str) -> bool:
        """Détermine si un texte doit être traduit"""
        # Ignorer les textes techniques
        ignore_patterns = [
            r'^[\w_]+$',  # Variables uniquement
            r'^\*{2,}.*\*{2,}$',  # Markdown styling uniquement
            r'^<.*>$',  # Tags HTML uniquement
            r'^[0-9\s\-_\.]+$',  # Nombres et caractères techniques
            r'^\w+\(\)$',  # Noms de fonctions
        ]

        for pattern in ignore_patterns:
            if re.match(pattern, text.strip()):
                return False

        return len(text.strip()) >= 5  # Minimum 5 caractères

    def generate_translation_keys(self, texts: List[str]) -> Dict[str, str]:
        """Génère des clés de traduction automatiquement"""
        translation_keys = {}

        for text in texts:
            # Créer une clé à partir du texte
            key = self._text_to_key(text)
            translation_keys[key] = text

        return translation_keys

    def _text_to_key(self, text: str) -> str:
        """Convertit un texte en clé de traduction"""
        # Nettoyer le texte
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        clean_text = re.sub(r'\s+', '_', clean_text.strip())

        # Limiter la longueur
        if len(clean_text) > 30:
            words = clean_text.split('_')[:4]
            clean_text = '_'.join(words)

        return clean_text

    def scan_directory(self, directory: Path, extensions: List[str] = None) -> Dict[str, List[Tuple[str, str, int]]]:
        """
        Scanne un répertoire entier pour les textes hardcodés

        Args:
            directory: Répertoire à scanner
            extensions: Extensions de fichiers à inclure

        Returns:
            Dict avec les résultats par fichier
        """
        if extensions is None:
            extensions = ['.py']

        results = {}

        for file_path in directory.rglob('*'):
            if file_path.suffix in extensions and file_path.is_file():
                hardcoded = self.scan_file(file_path)
                if hardcoded:
                    results[str(file_path)] = hardcoded

        return results

    def generate_migration_report(self, scan_results: Dict[str, List[Tuple[str, str, int]]]) -> str:
        """Génère un rapport de migration"""
        report = []
        report.append("# Rapport de Migration I18N")
        report.append("=" * 50)
        report.append("")

        total_hardcoded = sum(len(texts) for texts in scan_results.values())
        report.append(f"**Total de textes hardcodés trouvés: {total_hardcoded}**")
        report.append(f"**Fichiers affectés: {len(scan_results)}**")
        report.append("")

        # Détail par fichier
        for file_path, texts in scan_results.items():
            report.append(f"## {file_path}")
            report.append(f"*{len(texts)} texte(s) hardcodé(s)*")
            report.append("")

            for function, text, line_num in texts:
                report.append(f"- **Ligne {line_num}** ({function}): `{text[:50]}{'...' if len(text) > 50 else ''}`")
                suggested_key = self._text_to_key(text)
                report.append(f"  → Clé suggérée: `{suggested_key}`")

            report.append("")

        return "\n".join(report)

    def generate_example_migration(self, file_path: str, texts: List[Tuple[str, str, int]]) -> str:
        """Génère un exemple de migration pour un fichier"""
        example = []
        example.append(f"# Migration exemple pour {file_path}")
        example.append("")
        example.append("## 1. Ajouter l'import")
        example.append("```python")
        example.append("from translations import t, _")
        example.append("```")
        example.append("")
        example.append("## 2. Remplacer les textes hardcodés")
        example.append("")

        for function, text, line_num in texts[:5]:  # Limiter aux 5 premiers
            key = self._text_to_key(text)
            example.append(f"### Ligne {line_num}")
            example.append("**Avant:**")
            example.append(f"```python")
            example.append(f'st.{function}("{text}")')
            example.append("```")
            example.append("**Après:**")
            example.append(f"```python")
            example.append(f"st.{function}(t('{key}'))")
            example.append("```")
            example.append("")

        return "\n".join(example)


def main():
    """Fonction principale pour scanner le projet"""
    print("Assistant de Migration I18N")
    print("=" * 30)

    # Scanner le projet
    project_root = Path(__file__).parent.parent
    helper = I18nMigrationHelper()

    # Directories à scanner
    directories_to_scan = [
        project_root / "pages",
        project_root / "components",
        project_root / "assistant_regulation" / "app"
    ]

    all_results = {}
    for directory in directories_to_scan:
        if directory.exists():
            results = helper.scan_directory(directory)
            all_results.update(results)

    # Générer le rapport
    report = helper.generate_migration_report(all_results)

    # Sauvegarder le rapport
    report_file = project_root / "i18n_migration_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Rapport genere: {report_file}")
    print(f"Textes hardcodes trouves: {sum(len(texts) for texts in all_results.values())}")
    print(f"Fichiers affectes: {len(all_results)}")


if __name__ == "__main__":
    main()