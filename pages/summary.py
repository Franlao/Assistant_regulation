"""
Page Summary - Interface pour le résumé intelligent de réglementations
Utilise l'IntelligentSummaryService pour générer des synthèses de réglementations complètes
"""

import streamlit as st
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    from assistant_regulation.planning.services.intelligent_summary_service import IntelligentSummaryService, SummaryConfig
except ImportError as e:
    st.error(f"Erreur: Module IntelligentSummaryService non trouvé: {e}")
    IntelligentSummaryService = None
    SummaryConfig = None

try:
    from assistant_regulation.planning.Database.list_regulations import RegulationListManager
except ImportError as e:
    st.error(f"Erreur: Module RegulationListManager non trouvé: {e}")
    RegulationListManager = None

import chromadb

# Configuration du logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_available_regulations():
    """Récupère la liste des réglementations disponibles dans la base"""
    try:
        if RegulationListManager is None:
            logger.error("RegulationListManager non disponible")
            return []
        
        # Utiliser RegulationListManager pour récupérer les données
        manager = RegulationListManager()
        all_data = manager.get_all_regulations()
        
        # Convertir au format attendu par la page summary
        regulations = []
        for reg_code, details in all_data.get("regulations_details", {}).items():
            chunks_total = details["chunks"]["total"]
            # Estimation: ~10 chunks par page
            estimated_pages = max(1, chunks_total // 10)
            
            regulations.append({
                'code': reg_code,
                'collection': 'simple_text',
                'chunks': chunks_total,
                'estimated_pages': estimated_pages,
                'chunks_breakdown': {
                    'text': details["chunks"]["text"],
                    'images': details["chunks"]["images"],
                    'tables': details["chunks"]["tables"]
                },
                'pages_info': details["pages"],
                'documents_count': details["documents_count"]
            })
        
        return sorted(regulations, key=lambda x: x['code'])
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réglementations: {e}")
        return []


def load_regulation_chunks(regulation_code: str) -> List[Dict]:
    """Charge les chunks d'une réglementation spécifique depuis ChromaDB"""
    try:
        client = chromadb.PersistentClient(path="./DB/chroma_db")
        collection = client.get_collection("simple_text")
        
        # Filtrer par regulation_code dans les métadonnées
        results = collection.get(
            where={"regulation_code": regulation_code},
            include=['documents', 'metadatas']
        )
        
        if not results['documents']:
            logger.warning(f"Aucun chunk trouvé pour la réglementation {regulation_code}")
            return []
        
        chunks = []
        for doc_id, document, metadata in zip(results['ids'], results['documents'], results['metadatas']):
            chunk = {
                'id': doc_id,
                'content': document,
                'page_no': metadata.get('page_no', metadata.get('page', 1)),
                'regulation_code': regulation_code,
                'document_name': metadata.get('document_name', f'{regulation_code}.pdf'),
                'metadata': metadata
            }
            chunks.append(chunk)
        
        # Trier par numéro de page pour maintenir l'ordre
        chunks.sort(key=lambda x: x['page_no'])
        
        logger.info(f"Chargés {len(chunks)} chunks pour {regulation_code}")
        return chunks
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des chunks pour {regulation_code}: {e}")
        return []


def save_summary_result(summary_result, regulation_code: str):
    """Sauvegarde le résumé généré"""
    try:
        # Créer le dossier s'il n'existe pas
        summary_dir = ".regulation_summaries"
        os.makedirs(summary_dir, exist_ok=True)
        
        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{regulation_code}_{timestamp}.json"
        filepath = os.path.join(summary_dir, filename)
        
        # Préparer les données à sauvegarder
        summary_data = {
            "regulation_code": summary_result.regulation_code,
            "original_pages": summary_result.original_pages,
            "summary_length": summary_result.summary_length,
            "summary_ratio": summary_result.summary_ratio,
            "sections_count": summary_result.sections_count,
            "summary_text": summary_result.summary_text,
            "sections_summaries": summary_result.sections_summaries,
            "processing_time": summary_result.processing_time,
            "metadata": summary_result.metadata,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        return filepath
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")
        return None


def load_saved_summaries() -> List[Dict]:
    """Charge les résumés sauvegardés"""
    summaries = []
    summary_dir = ".regulation_summaries"
    
    if not os.path.exists(summary_dir):
        return summaries
    
    try:
        for filename in os.listdir(summary_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(summary_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                    summary_data['filename'] = filename
                    summary_data['filepath'] = filepath
                    summaries.append(summary_data)
        
        # Trier par date de génération
        summaries.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des résumés: {e}")
    
    return summaries


def render_summary_generator():
    """Interface de génération de résumés"""
    st.markdown("""
    <div style="background: linear-gradient(90deg, #FF5722, #FF9800); padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem;">
        <h3 style="color: white; margin: 0; font-weight: 600;">Générateur de Résumés Intelligents</h3>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 0.9rem;">Synthèses proportionnelles de réglementations complètes</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Récupérer les réglementations disponibles
    regulations = get_available_regulations()
    
    if not regulations:
        st.error("Aucune réglementation trouvée dans la base de données.")
        st.info("Assurez-vous que des documents ont été ingérés dans la base ChromaDB.")
        return
    
    # Interface de sélection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Sélection de la réglementation simplifiée
        reg_options = {}
        for reg in regulations:
            display_text = f"{reg['code']} ({reg['estimated_pages']} pages)"
            reg_options[display_text] = reg['code']
        
        selected_display = st.selectbox(
            "Sélectionnez une réglementation",
            options=list(reg_options.keys()),
            help="Choisissez la réglementation à résumer"
        )
        
        selected_reg_code = reg_options[selected_display]
        selected_reg = next(r for r in regulations if r['code'] == selected_reg_code)
    
    with col2:
        # Configuration LLM
        llm_provider = st.selectbox(
            "Modèle LLM",
            ["mistral", "ollama"],
            help="Mistral recommandé pour la qualité, Ollama pour l'usage local"
        )
        
        if llm_provider == "mistral":
            model_name = st.selectbox("Modèle Mistral", 
                                    ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"])
        else:
            model_name = st.text_input("Modèle Ollama", value="llama3.2", help="Ex: llama3.2, codellama")
    
    # Informations sur la réglementation sélectionnée
    st.markdown("""
    <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; border-left: 4px solid #FF5722; margin: 1rem 0;">
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Réglementation:** {selected_reg['code']}")
    with col2:
        st.markdown(f"**Pages:** {selected_reg['estimated_pages']}")
    with col3:
        # Calculer la longueur estimée du résumé
        if IntelligentSummaryService:
            service = IntelligentSummaryService()
            target_pages, ratio = service.calculate_target_length(selected_reg['estimated_pages'], selected_reg['chunks'])
            st.markdown(f"**Résumé estimé:** {target_pages} pages")
        else:
            st.markdown("**Résumé estimé:** N/A")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Configuration avancée (masquée par défaut)
    with st.expander("Paramètres avancés", expanded=False):
        st.markdown(f"""
        **Chunks total:** {selected_reg['chunks']}  
        **Ratio de compression:** {ratio:.1%}  
        **Modèle LLM:** {llm_provider}/{model_name}
        """)
        
        if selected_reg.get('chunks_breakdown'):
            breakdown = selected_reg['chunks_breakdown']
            st.markdown(f"**Contenu:** {breakdown['text']} texte, {breakdown['images']} images, {breakdown['tables']} tableaux")
    
    # Bouton de génération moderne
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Générer le Résumé", type="primary", use_container_width=True):
        
        # Vérifications préliminaires
        if llm_provider == "mistral" and not os.getenv("MISTRAL_API_KEY"):
            st.error("ERREUR: MISTRAL_API_KEY non configurée. Configurez votre clé API Mistral.")
            return
        
        with st.spinner("Génération du résumé en cours..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialiser le service
                status_text.text("Initialisation du service...")
                progress_bar.progress(10)
                
                service = IntelligentSummaryService(
                    llm_provider=llm_provider,
                    model_name=model_name,
                    max_workers=2  # Limiter pour éviter les surcharges
                )
                
                # Générer le résumé directement
                status_text.text("Génération du résumé par le LLM...")
                progress_bar.progress(30)
                
                # La méthode generate_regulation_summary prend seulement le regulation_code
                summary_result = service.generate_regulation_summary(selected_reg['code'])
                
                progress_bar.progress(90)
                status_text.text("Sauvegarde...")
                
                # Sauvegarder
                saved_path = save_summary_result(summary_result, selected_reg['code'])
                
                progress_bar.progress(100)
                status_text.text("Terminé!")
                
                # Stocker dans le session state
                st.session_state.current_summary = summary_result
                st.session_state.summary_saved_path = saved_path
                
                st.success(f"Résumé généré avec succès en {summary_result.processing_time:.1f}s!")
                
                # Statistiques finales épurées
                st.markdown("""
                <div style="background: rgba(76, 175, 80, 0.1); padding: 1rem; border-radius: 8px; border: 1px solid rgba(76, 175, 80, 0.3); margin: 1rem 0;">
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Longueur:** {summary_result.summary_length:,} mots")
                with col2:
                    st.markdown(f"**Compression:** {summary_result.summary_ratio:.1%}")
                with col3:
                    st.markdown(f"**Sections:** {summary_result.sections_count}")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Nettoyer la barre de progression
                progress_bar.empty()
                status_text.empty()
                
                st.rerun()
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Erreur lors de la génération: {str(e)}")
                logger.error(f"Erreur génération résumé: {e}")


def render_current_summary():
    """Affiche le résumé actuellement généré"""
    if "current_summary" not in st.session_state:
        return
    
    summary = st.session_state.current_summary
    
    # En-tête moderne
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2E7D32, #4CAF50); padding: 1.5rem; border-radius: 10px; margin: 2rem 0 1rem 0;">
        <h3 style="color: white; margin: 0; font-weight: 600;">Résumé: {summary.regulation_code}</h3>
        <div style="display: flex; gap: 2rem; margin-top: 1rem; flex-wrap: wrap;">
            <span style="color: rgba(255,255,255,0.9);"><strong>{summary.original_pages}</strong> pages originales</span>
            <span style="color: rgba(255,255,255,0.9);"><strong>{summary.summary_length:,}</strong> mots</span>
            <span style="color: rgba(255,255,255,0.9);"><strong>{summary.summary_ratio:.1%}</strong> compression</span>
            <span style="color: rgba(255,255,255,0.9);"><strong>{summary.processing_time:.1f}s</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Actions modernes
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("Nouveau résumé", use_container_width=True):
            del st.session_state.current_summary
            if "summary_saved_path" in st.session_state:
                del st.session_state.summary_saved_path
            st.rerun()
    
    # Contenu du résumé dans une carte moderne
    st.markdown("""
    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.5rem; margin: 1rem 0;">
    """, unsafe_allow_html=True)
    
    st.markdown(summary.summary_text, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Conseil utilisateur discret
    st.markdown(
        '<p style="color: rgba(255,255,255,0.6); font-size: 0.85rem; text-align: center; margin-top: 1rem;">'
        'Utilisez Ctrl+A puis Ctrl+C pour copier le résumé'
        '</p>', 
        unsafe_allow_html=True
    )
    
    # Détails techniques (repliable)
    with st.expander("Détails techniques", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.json({
                "regulation_code": summary.regulation_code,
                "sections_count": summary.sections_count,
                "processing_time": f"{summary.processing_time:.2f}s"
            })
        
        with col2:
            if summary.metadata:
                st.json(summary.metadata)


def render_saved_summaries():
    """Affiche les résumés sauvegardés"""
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1976D2, #42A5F5); padding: 1rem; border-radius: 10px; margin-bottom: 1.5rem;">
        <h3 style="color: white; margin: 0; font-weight: 600;">Historique des Résumés</h3>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 0.9rem;">Résumés précédemment générés</p>
    </div>
    """, unsafe_allow_html=True)
    
    summaries = load_saved_summaries()
    
    if not summaries:
        st.markdown("""
        <div style="background: rgba(158, 158, 158, 0.1); padding: 2rem; border-radius: 8px; text-align: center; border: 1px dashed rgba(158, 158, 158, 0.3);">
            <p style="color: rgba(255,255,255,0.7); margin: 0;">Aucun résumé sauvegardé</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filtres
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Filtrer par réglementation
        all_reg_codes = sorted(list(set(s.get('regulation_code', 'Unknown') for s in summaries)))
        selected_regs = st.multiselect(
            "Filtrer par réglementation",
            all_reg_codes,
            default=all_reg_codes[:5] if len(all_reg_codes) > 5 else all_reg_codes
        )
    
    with col2:
        sort_by = st.selectbox(
            "Trier par",
            ["Date (récent)", "Date (ancien)", "Réglementation", "Taille"]
        )
    
    # Filtrer et trier
    filtered_summaries = [s for s in summaries if s.get('regulation_code') in selected_regs]
    
    if sort_by == "Date (ancien)":
        filtered_summaries.sort(key=lambda x: x.get('generated_at', ''))
    elif sort_by == "Réglementation":
        filtered_summaries.sort(key=lambda x: x.get('regulation_code', ''))
    elif sort_by == "Taille":
        filtered_summaries.sort(key=lambda x: x.get('summary_length', 0), reverse=True)
    
    # Affichage des résumés dans des cartes modernes
    for summary in filtered_summaries:
        with st.expander(f"{summary.get('regulation_code', 'Unknown')} ({summary.get('summary_length', 0):,} mots)", expanded=False):
            
            # Métadonnées
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.caption(f"**Pages:** {summary.get('original_pages', 'N/A')}")
            with col2:
                st.caption(f"**Ratio:** {summary.get('summary_ratio', 0):.1%}")
            with col3:
                st.caption(f"**Sections:** {summary.get('sections_count', 'N/A')}")
            with col4:
                generated_at = summary.get('generated_at', '')
                if generated_at:
                    try:
                        date_obj = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                        st.caption(f"**Généré:** {formatted_date}")
                    except:
                        st.caption(f"**Généré:** {generated_at}")
            
            # Contenu
            st.markdown("---")
            summary_text = summary.get('summary_text', 'Contenu indisponible')
            st.markdown(summary_text, unsafe_allow_html=True)
            
            # Actions
            col1, col2 = st.columns([4, 1])
            
            with col2:
                if st.button("Supprimer", key=f"delete_{summary.get('filename', '')}", help="Supprimer ce résumé"):
                    try:
                        if os.path.exists(summary['filepath']):
                            os.remove(summary['filepath'])
                            st.success("Résumé supprimé!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")


def main():
    """Page principale des résumés de réglementations"""
    st.set_page_config(
        page_title="Résumés Intelligents - Assistant Réglementaire",
        page_icon="📄",
        layout="wide"
    )
    
    # Titre moderne
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="color: white; font-weight: 700; font-size: 2.5rem; margin: 0;">Résumés Intelligents</h1>
        <p style="color: rgba(255,255,255,0.8); font-size: 1.1rem; margin: 0.5rem 0 0 0;">Synthèses automatiques de réglementations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Information sur le service (plus discrète)
    with st.expander("Comment ça marche", expanded=False):
        st.markdown("""
        **Fonctionnement:**
        • Analyse intelligente des documents réglementaires
        • Résumés proportionnels à la taille du document  
        • Structure hiérarchique préservée
        • Informations techniques conservées
        
        **Tailles de résumé:**
        • ≤15 pages → 1 page de résumé
        • ≤30 pages → 2 pages de résumé  
        • ≤60 pages → 3-4 pages de résumé
        • ≤100 pages → 5-7 pages de résumé
        • >100 pages → 8-12 pages maximum
        """)
    
    # Onglets épurés
    tab1, tab2 = st.tabs(["Générateur", "Historique"])
    
    with tab1:
        render_summary_generator()
        render_current_summary()
    
    with tab2:
        render_saved_summaries()


if __name__ == "__main__":
    main()