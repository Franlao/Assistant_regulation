"""
Exemple d'utilisation du module de génération de résumés réglementaires.
Démontre comment utiliser RegulationResumeGenerator avec votre architecture existante.
"""

import logging
from pathlib import Path
from assistant_regulation.processing.Modul_Summary import RegulationSummarizer
from assistant_regulation.processing.Modul_Summary.generate_resume import RegulationResumeGenerator

# Configuration du logging pour l'exemple
logging.basicConfig(level=logging.INFO)

def example_simple_json_summary():
    """Exemple 1: Génération simple d'un résumé JSON"""
    print("=== Exemple 1: Résumé JSON simple ===")
    
    # Initialisation du service de résumé (réutilise vos services existants)
    summarizer = RegulationSummarizer(
        llm_provider="mistral",  # ou "mistral"
        model_name="Mistral-large-latest"
    )
    
    # Génération du résumé
    pdf_path = "assets/R107 - 10 series.pdf"  # Utilisez votre PDF existant
    
    try:
        result = summarizer.generate_summary_from_pdf(
            pdf_path=pdf_path,
            mode="normal",
            save_intermediate=True
        )
        
        print(f"✅ Résumé généré pour: {result['summary']['regulation_number']}")
        print(f"📄 Pages analysées: {result['processing_info']['page_count']}")
        print(f"📝 Texte extrait: {result['processing_info']['text_length']} caractères")
        
        # Aperçu des sections
        sections = result['summary']['sections']
        print(f"\n📋 Sections générées ({len(sections)}):")
        for i, section in enumerate(sections[:3], 1):  # Première 3 sections
            print(f"  {i}. {section['title']}: {section['content'][:100]}...")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

def example_complete_generation():
    """Exemple 2: Génération complète (JSON + HTML + PDF)"""
    print("\n=== Exemple 2: Génération complète ===")
    
    # Initialisation du générateur complet
    generator = RegulationResumeGenerator(
        llm_provider="mistral",
        model_name="mistral-large-latest",
        templates_dir="templates",
        output_dir="output"
    )
    
    pdf_path = "assets/R107 - 10 series.pdf"
    
    try:
        # Génération avec tous les formats
        result = generator.generate_complete_resume(
            pdf_path=pdf_path,
            mode="detailed",  # Mode détaillé pour plus de contenu
            output_formats=["json", "html", "pdf"],
            regulation_number=None  # Auto-détection
        )
        
        if result["success"]:
            print(f"✅ Génération réussie pour: {result['regulation_number']}")
            print(f"📅 Généré le: {result['generated_at']}")
            
            print("\n📁 Fichiers générés:")
            for format_type, file_path in result["output_files"].items():
                print(f"  {format_type.upper()}: {file_path}")
                
        else:
            print(f"❌ Erreur: {result['error']}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def example_integration_with_existing_rag():
    """Exemple 3: Intégration avec votre RAG existant"""
    print("\n=== Exemple 3: Intégration RAG ===")
    
    # Ce module peut être intégré dans votre workflow RAG existant
    # Par exemple, dans votre interface Streamlit ou votre orchestrateur
    
    print("💡 Points d'intégration possibles:")
    print("  1. Ajouter un bouton 'Générer résumé' dans votre interface Streamlit")
    print("  2. Utiliser le service dans votre modular_orchestrator.py")
    print("  3. Créer un nouveau endpoint dans votre API si vous en avez une")
    print("  4. Intégrer dans vos services Planning_pattern")
    
    # Exemple d'intégration dans l'interface utilisateur
    example_streamlit_integration()

def example_streamlit_integration():
    """Exemple de code pour intégration Streamlit"""
    print("\n📝 Exemple de code Streamlit:")
    
    streamlit_code = '''
import streamlit as st
from assistant_regulation.processing.Modul_Summary.generate_resume import RegulationResumeGenerator

def add_summary_section():
    """Ajoute une section de génération de résumé à votre interface"""
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Générateur de Résumé")
    
    # Options de résumé
    summary_mode = st.sidebar.selectbox(
        "Mode de résumé",
        ["concise", "normal", "detailed"],
        index=1
    )
    
    output_formats = st.sidebar.multiselect(
        "Formats de sortie",
        ["json", "html", "pdf"],
        default=["html", "pdf"]
    )
    
    # Bouton de génération
    if st.sidebar.button("🔄 Générer Résumé"):
        if "current_pdf_path" in st.session_state:
            with st.spinner("Génération du résumé en cours..."):
                generator = RegulationResumeGenerator()
                result = generator.generate_complete_resume(
                    pdf_path=st.session_state.current_pdf_path,
                    mode=summary_mode,
                    output_formats=output_formats
                )
                
                if result["success"]:
                    st.success(f"Résumé généré pour {result['regulation_number']}")
                    
                    # Liens de téléchargement
                    for format_type, file_path in result["output_files"].items():
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📄 Télécharger {format_type.upper()}",
                                data=f.read(),
                                file_name=Path(file_path).name,
                                mime=get_mime_type(format_type)
                            )
                else:
                    st.error(f"Erreur: {result['error']}")
        else:
            st.warning("Aucun PDF chargé")

def get_mime_type(format_type):
    return {
        "json": "application/json",
        "html": "text/html",
        "pdf": "application/pdf"
    }.get(format_type, "application/octet-stream")
'''
    
    print(streamlit_code)

def example_api_integration():
    """Exemple d'intégration API"""
    print("\n🌐 Exemple d'endpoint API:")
    
    api_code = '''
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from assistant_regulation.processing.Modul_Summary.generate_resume import RegulationResumeGenerator

app = FastAPI()

@app.post("/generate-summary/")
async def generate_regulation_summary(
    file: UploadFile = File(...),
    mode: str = "normal",
    formats: list = ["json", "html", "pdf"]
):
    """Endpoint pour générer un résumé réglementaire"""
    
    # Sauvegarde temporaire du fichier
    temp_path = f"temp/{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Génération du résumé
    generator = RegulationResumeGenerator()
    result = generator.generate_complete_resume(
        pdf_path=temp_path,
        mode=mode,
        output_formats=formats
    )
    
    return result

@app.get("/download-summary/{regulation_number}/{format_type}")
async def download_summary(regulation_number: str, format_type: str):
    """Télécharge un fichier de résumé généré"""
    file_path = f"output/resume_{regulation_number}_{format_type}.{format_type}"
    return FileResponse(file_path)
'''
    
    print(api_code)

def main():
    """Exécute tous les exemples"""
    print("🚀 Démonstration du Module de Résumé Réglementaire")
    print("=" * 60)
    
    # Vérifier que le PDF exemple existe
    pdf_path = Path("assets/R107 - 10 series.pdf")
    if not pdf_path.exists():
        print(f"⚠️  PDF d'exemple non trouvé: {pdf_path}")
        print("   Veuillez ajuster le chemin dans les exemples")
        return
    
    # Exécuter les exemples
    example_simple_json_summary()
    example_complete_generation()
    example_integration_with_existing_rag()
    example_api_integration()
    
    print("\n" + "=" * 60)
    print("✨ Module prêt à être intégré dans votre architecture!")

if __name__ == "__main__":
    main() 