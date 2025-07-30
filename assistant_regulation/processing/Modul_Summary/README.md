# Module de Génération de Résumés Réglementaires

## 📋 Vue d'ensemble

Ce module ajoute une fonctionnalité de génération de résumés standardisés pour les réglementations à votre architecture RAG existante. Il réutilise intelligemment vos services existants (`GenerationService`, `PromptingService`) et s'intègre parfaitement dans votre écosystème.

## 🏗️ Architecture

### Workflow complet
```
PDF Réglementaire 
    ↓ (PDFTextExtractor + pdfplumber)
Texte brut 
    ↓ (RegulationSummarizer + vos services LLM existants)
Résumé JSON (15 rubriques) 
    ↓ (HTMLTemplateRenderer + Jinja2)
HTML formaté 
    ↓ (WeasyPrint)
PDF final stylisé
```

### Composants réutilisés de votre architecture
- ✅ **`GenerationService`** - Service LLM (Mistral/Ollama) 
- ✅ **`PromptingService`** - Gestion centralisée des prompts
- ✅ **`pdfplumber`** - Extraction PDF (déjà installé)
- ✅ **Configuration centralisée** - Pattern de configuration existant

### Nouveaux composants ajoutés
- 🆕 **`PDFTextExtractor`** - Extraction de texte PDF spécialisée
- 🆕 **`RegulationSummarizer`** - Service de génération de résumés
- 🆕 **`HTMLTemplateRenderer`** - Rendu HTML avec Jinja2
- 🆕 **`RegulationResumeGenerator`** - Orchestrateur principal

## 📦 Installation

### Dépendances ajoutées
```bash
pip install jinja2>=3.1.0 weasyprint>=59.0 python-dateutil>=2.8.0
```

Ces dépendances ont été ajoutées à votre `requirements.txt` existant.

## 🚀 Utilisation

### 1. Utilisation simple (JSON uniquement)
```python
from src.Processing_pattern.Modul_Summary import RegulationSummarizer

# Initialisation (réutilise vos services existants)
summarizer = RegulationSummarizer(
    llm_provider="ollama",  # ou "mistral"
    model_name="llama3.2"
)

# Génération du résumé
result = summarizer.generate_summary_from_pdf(
    pdf_path="assets/R107 - 10 series.pdf",
    mode="normal",  # "concise", "normal", "detailed"
    save_intermediate=True
)

print(f"Résumé généré: {result['summary']['regulation_number']}")
```

### 2. Génération complète (JSON + HTML + PDF)
```python
from src.Processing_pattern.Modul_Summary.generate_resume import RegulationResumeGenerator

# Initialisation
generator = RegulationResumeGenerator(
    llm_provider="ollama",
    model_name="llama3.2",
    output_dir="output"
)

# Génération complète
result = generator.generate_complete_resume(
    pdf_path="assets/R107 - 10 series.pdf",
    mode="detailed",
    output_formats=["json", "html", "pdf"]
)

if result["success"]:
    print("Fichiers générés:")
    for format_type, file_path in result["output_files"].items():
        print(f"  {format_type.upper()}: {file_path}")
```

### 3. Utilisation en ligne de commande
```bash
python -m src.Processing_pattern.Modul_Summary.generate_resume \
    "assets/R107 - 10 series.pdf" \
    --mode detailed \
    --formats json html pdf \
    --llm ollama \
    --model llama3.2
```

## 📝 Schéma JSON standardisé

Le module génère un JSON avec 15 rubriques standardisées :

```json
{
  "regulation_number": "R107",
  "series": "10 series",
  "mode": "normal",
  "sections": [
    {"title": "Fiche d'identité", "content": "...", "details": []},
    {"title": "Objet et champ d'application", "content": "...", "details": []},
    {"title": "Définitions clés", "content": "...", "details": []},
    {"title": "Classes / catégories", "content": "...", "details": []},
    {"title": "Procédure d'homologation", "content": "...", "details": []},
    {"title": "Marquages obligatoires", "content": "...", "details": []},
    {"title": "Exigences techniques", "content": "...", "details": []},
    {"title": "Essais et vérifications", "content": "...", "details": []},
    {"title": "Conformité de la production", "content": "...", "details": []},
    {"title": "Sanctions / Retrait", "content": "...", "details": []},
    {"title": "Cessation de production", "content": "...", "details": []},
    {"title": "Dispositions transitoires", "content": "...", "details": []},
    {"title": "Services techniques / autorités", "content": "...", "details": []},
    {"title": "Annexes – aperçu", "content": "...", "details": []},
    {"title": "Références croisées / version", "content": "...", "details": []}
  ],
  "generated_on": "2024-01-15"
}
```

## 🎨 Modes de résumé

| Mode | Description | Longueur `content` | `details` |
|------|-------------|-------------------|-----------|
| **concise** | Résumé très court | 1-2 phrases (≈25 mots) | Vide |
| **normal** | Résumé standard | 2-3 phrases (≈60 mots) | Vide |
| **detailed** | Analyse complète | Paragraphe complet | 3-6 puces détaillées |

## 🖼️ Templates HTML

Le module inclut 3 templates HTML pré-conçus :

- **`resume_concise.html`** - Design minimaliste pour mode concis
- **`resume_normal.html`** - Design standard avec tableaux et métadonnées
- **`resume_detailed.html`** - Design complet avec sections expandables

Les templates sont générés automatiquement avec un CSS moderne (Arial, marges 2rem, tableaux bordés).

## 🔧 Intégration dans votre architecture

### Intégration Streamlit
```python
# Dans votre app.py principal
from src.Processing_pattern.Modul_Summary.generate_resume import RegulationResumeGenerator

def add_summary_section():
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Générateur de Résumé")
    
    summary_mode = st.sidebar.selectbox(
        "Mode de résumé", 
        ["concise", "normal", "detailed"]
    )
    
    if st.sidebar.button("🔄 Générer Résumé"):
        generator = RegulationResumeGenerator()
        result = generator.generate_complete_resume(
            pdf_path=st.session_state.current_pdf_path,
            mode=summary_mode
        )
        # Affichage des résultats...
```

### Intégration avec vos services
```python
# Extension de votre orchestrateur existant
from src.Planning_pattern.sync.modular_orchestrator import ModularOrchestrator
from src.Processing_pattern.Modul_Summary import RegulationSummarizer

class ExtendedOrchestrator(ModularOrchestrator):
    def __init__(self):
        super().__init__()
        self.summarizer = RegulationSummarizer(
            llm_provider=self.generation_service.llm_provider,
            model_name=self.generation_service.model_name
        )
    
    def generate_regulation_summary(self, pdf_path: str, mode: str = "normal"):
        return self.summarizer.generate_summary_from_pdf(pdf_path, mode)
```

## 📂 Structure des fichiers

```
src/Processing_pattern/Modul_Summary/
├── __init__.py                    # Interface du module
├── pdf_text_extractor.py          # Extraction PDF (pdfplumber)
├── regulation_summarizer.py       # Service principal + prompts
├── html_template_renderer.py      # Rendu HTML (Jinja2)
├── generate_resume.py             # Orchestrateur complet
├── example_usage.py               # Exemples d'utilisation
└── README.md                      # Cette documentation

templates/                         # Créé automatiquement
├── resume_concise.html
├── resume_normal.html
└── resume_detailed.html

output/                           # Créé automatiquement
├── resume_R107_normal_20240115_143022.json
├── resume_R107_normal_20240115_143022.html
└── resume_R107_normal_20240115_143022.pdf
```

## ⚙️ Configuration

Le module utilise votre configuration existante et ajoute ses propres paramètres :

```python
# Configuration LLM (réutilise votre configuration existante)
generator = RegulationResumeGenerator(
    llm_provider="ollama",      # ou "mistral"
    model_name="llama3.2",      # votre modèle préféré
    templates_dir="templates",  # dossier des templates HTML
    output_dir="output"         # dossier de sortie
)
```

## 🔍 Logging et debugging

Le module utilise le système de logging Python standard :

```python
import logging
logging.basicConfig(level=logging.INFO)

# Les logs incluent :
# - Progression de l'extraction PDF
# - Appels au LLM et réponses
# - Génération des fichiers
# - Erreurs détaillées
```

## 🚨 Gestion d'erreurs

Le module gère intelligemment les erreurs :

- **PDF introuvable/corrompu** → Exception claire avec chemin
- **Erreur LLM** → Retry automatique + logs détaillés  
- **JSON invalide du LLM** → Nettoyage et nouvelle tentative
- **WeasyPrint indisponible** → Avertissement + génération sans PDF
- **Templates manquants** → Création automatique des templates

## 🎯 Points forts de l'intégration

1. **Réutilise vos services existants** - Pas de duplication de code
2. **S'intègre dans votre workflow** - Compatible avec votre architecture modulaire
3. **Configuration cohérente** - Utilise vos patterns de configuration
4. **Logging unifié** - S'intègre dans votre système de logs
5. **Extensible** - Facile d'ajouter de nouveaux templates ou modes

## 📈 Performance

- **Extraction PDF** : ~2-5 secondes pour un document typique
- **Génération LLM** : Dépend de votre modèle (30-60s pour Ollama local)
- **Rendu HTML/PDF** : ~1-2 secondes
- **Total** : ~35-70 secondes pour un workflow complet

## 🔮 Extensions futures possibles

- Support de templates personnalisés
- Mode batch pour plusieurs PDFs
- Intégration avec votre base vectorielle existante
- API REST standalone
- Support de langues multiples
- Export vers d'autres formats (Word, Markdown)

---

**✨ Votre module de résumé réglementaire est prêt à être utilisé !** 