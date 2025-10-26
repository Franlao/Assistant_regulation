"""
Page Database - Gestion complète de ChromaDB (Admin uniquement)
Intègre tous les scripts du module Database
"""

import streamlit as st
import os
import tempfile
import pandas as pd
import json
from typing import List, Dict, Any
from utils.session_utils import initialize_session_state
from components.modern_auth_integration import require_modern_admin_access
from utils.task_manager import get_task_manager, async_upload_files, async_folder_ingestion
from components.task_monitor import render_task_monitor, render_task_notifications, render_task_status_bar
from components.auth_components import SimpleAuth
from datetime import datetime

# Import des managers Database
try:
    from assistant_regulation.planning.Database import (
        PDFIngestionManager,
        DatabaseSummaryManager,
        RegulationSearchManager,
        DatabaseCleanupManager,
        RegulationListManager,
        PDFUploadManager,
        check_database_health
    )
    # Vérifier que la fonction est bien disponible
    if 'check_database_health' not in locals():
        st.error("La fonction check_database_health n'a pas été importée correctement")
except ImportError as e:
    st.error(f"Erreur d'import des modules Database: {e}")
    # Définir une fonction de fallback
    def check_database_health():
        return {
            "healthy": False,
            "error": "Modules Database non disponibles",
            "issues": ["Import failed"]
        }


def render_database_status():
    """Affiche l'état actuel de la base de données"""
    st.markdown("""
    <div style="padding: 2rem 0;">
        <h2 style="color: #343a40; font-weight: 360; font-size: 2rem; margin: 0;">État de la Base de Données</h2>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Importer streamlit-elements
        from streamlit_elements import elements, mui, nivo
    except ImportError:
        st.error("streamlit-elements n'est pas installé. Utilisation du fallback.")
        return _render_database_status_fallback()
    
    try:
        health = check_database_health()
        
        # Layout principal avec streamlit-elements
        with elements("database_status"):
            
            # Container principal
            with mui.Box(sx={"display": "flex", "gap": 3, "alignItems": "flex-start"}):
                
                # Section graphique (gauche)
                with mui.Box(sx={"flex": 1, "minHeight": 400}):
                    collections_status = health.get('collections_status', {})
                    
                    if collections_status:
                        # Préparer les données pour Nivo pie chart
                        chart_data = []
                        for col_type, status in collections_status.items():
                            if isinstance(status, dict):
                                count = status.get('count', 0)
                                if count > 0:  # Seulement les collections avec des données
                                    chart_data.append({
                                        "id": col_type.capitalize(),
                                        "label": col_type.capitalize(), 
                                        "value": count
                                    })
                        
                        if chart_data:
                            # Créer le graphique camembert avec Nivo
                            with mui.Paper(elevation=2, sx={"p": 2, "height": 350,"display": "flex","flexDirection": "column","alignItems": "center","justifyContent": "center"}):
                                mui.Typography("Collections ChromaDB", variant="h6", sx={"mb": 2, "textAlign": "center"})

                                nivo.Pie(
                                    data=chart_data,
                                    height=300,
                                    margin={"top": 40, "right": 60, "bottom": 70, "left": 70},
                                    innerRadius=0.5,
                                    padAngle=0.7,
                                    cornerRadius=3,
                                    activeOuterRadiusOffset=8,
                                    colors=["#FF6B6B", "#4ECDC4", "#45B7D1"],
                                    borderWidth=1,
                                    borderColor={"from": "color", "modifiers": [["darker", 0.2]]},
                                    arcLinkLabelsSkipAngle=10,
                                    arcLinkLabelsTextColor="#333333",
                                    arcLinkLabelsThickness=2,
                                    arcLinkLabelsColor={"from": "color"},
                                    arcLabelsSkipAngle=10,
                                    arcLabelsTextColor={"from": "color", "modifiers": [["darker", 2]]},
                                    legends=[
                                        {
                                            "anchor": "bottom",
                                            "direction": "row",
                                            "justify": False,
                                            "translateX": 0,
                                            "translateY": 56,
                                            "itemsSpacing": 0,
                                            "itemWidth": 100,
                                            "itemHeight": 18,
                                            "itemTextColor": "#999",
                                            "itemDirection": "left-to-right",
                                            "itemOpacity": 1,
                                            "symbolSize": 18,
                                            "symbolShape": "circle"
                                        }
                                    ],
                                    theme={
                                        "background": "#FFFFFF",
                                        "textColor": "#31333F"
                                    }
                                )
                        else:
                            with mui.Paper(elevation=2, sx={"p": 3, "height": 350, "display": "flex", "alignItems": "center", "justifyContent": "center"}):
                                mui.Typography("Aucune donnée à afficher", variant="body1", color="textSecondary")
                    else:
                        with mui.Paper(elevation=2, sx={"p": 3, "height": 350, "display": "flex", "alignItems": "center", "justifyContent": "center"}):
                            mui.Typography("Impossible de récupérer l'état des collections", variant="body1", color="error")
                
                # Section métriques (droite)
                with mui.Box(sx={"flex": 1}):
                    with mui.Paper(elevation=2, sx={"p": 2, "height": 350}):
                        mui.Typography("Métriques", variant="h6", sx={"mb": 2, "textAlign": "center"})
                        
                        # Grille 2x2 pour les métriques
                        with mui.Grid(container=True, spacing=2):
                            
                            # État Général
                            with mui.Grid(item=True, xs=6):
                                is_healthy = health.get("healthy", False)
                                status_color = "success" if is_healthy else "error"
                                with mui.Paper(elevation=1, sx={"p": 2, "textAlign": "center", "minHeight": 80, "display": "flex", "flexDirection": "column", "justifyContent": "center", "alignItems": "center"}):
                                    mui.Typography("État Général", variant="body2", color="textSecondary", sx={"mb": 1})
                                    if is_healthy:
                                        mui.icon.CheckCircle(sx={"fontSize": 40, "color": "success.main"})
                                    else:
                                        mui.icon.Error(sx={"fontSize": 40, "color": "error.main"})
                            
                            # Documents
                            with mui.Grid(item=True, xs=6):
                                with mui.Paper(elevation=1, sx={"p": 2, "textAlign": "center", "minHeight": 80}):
                                    mui.Typography("Documents", variant="body2", color="textSecondary")
                                    mui.Typography(f"{health.get('total_documents', 0):,}", variant="h5", sx={"fontWeight": "bold"})
                            
                            # Réglementations  
                            with mui.Grid(item=True, xs=6):
                                with mui.Paper(elevation=1, sx={"p": 2, "textAlign": "center", "minHeight": 80}):
                                    mui.Typography("Réglementations", variant="body2", color="textSecondary")
                                    mui.Typography(str(health.get('total_regulations', 0)), variant="h5", sx={"fontWeight": "bold"})
                            
                            # Collections
                            with mui.Grid(item=True, xs=6):
                                collections_ok = sum(
                                    1 for col in health.get('collections_status', {}).values() 
                                    if isinstance(col, dict) and col.get('healthy', False)
                                )
                                total_collections = len(health.get('collections_status', {}))
                                with mui.Paper(elevation=1, sx={"p": 2, "textAlign": "center", "minHeight": 80}):
                                    mui.Typography("Collections", variant="body2", color="textSecondary")
                                    mui.Typography(f"{collections_ok}/{total_collections}", variant="h5", sx={"fontWeight": "bold"})
        
        # Problèmes détectés (en dessous, en Streamlit standard)
        issues = health.get('issues', [])
        if issues:
            st.warning("**Problèmes détectés:**")
            for issue in issues:
                st.write(f"  • {issue}")
        
        return health
        
    except Exception as e:
        st.error(f"  Impossible de vérifier l'état de la base: {e}")
        return {"healthy": False, "error": str(e)}


def _render_database_status_fallback():
    """Version de fallback sans streamlit-elements"""
    try:
        health = check_database_health()
        
        # Layout principal: graphique à gauche, métriques à droite
        col_chart, col_metrics = st.columns([1, 1])
        
        with col_chart:
            st.info("Graphique non disponible (streamlit-elements requis)")
            
            # Affichage simple des collections
            collections_status = health.get('collections_status', {})
            if collections_status:
                st.markdown("**Collections ChromaDB:**")
                for col_type, status in collections_status.items():
                    if isinstance(status, dict):
                        count = status.get('count', 0)
                        st.write(f"• **{col_type.capitalize()}:** {count:,} documents")
        
        with col_metrics:
            # Métriques en 2x2
            col1, col2 = st.columns(2)
            
            with col1:
                status_text = "Sain" if health.get("healthy", False) else "Problème"
                st.metric("État Général", status_text)
            
            with col2:
                st.metric("Documents", f"{health.get('total_documents', 0):,}")
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.metric("Réglementations", health.get('total_regulations', 0))
            
            with col4:
                collections_ok = sum(
                    1 for col in health.get('collections_status', {}).values() 
                    if isinstance(col, dict) and col.get('healthy', False)
                )
                total_collections = len(health.get('collections_status', {}))
                st.metric("Collections", f"{collections_ok}/{total_collections}")
        
        # Problèmes détectés
        issues = health.get('issues', [])
        if issues:
            st.warning("**Problèmes détectés:**")
            for issue in issues:
                st.write(f"  • {issue}")
        
        return health
        
    except Exception as e:
        st.error(f"  Impossible de vérifier l'état de la base: {e}")
        return {"healthy": False, "error": str(e)}


def render_pdf_ingestion():
    """Interface d'ingestion de PDFs avec support asynchrone"""
    #st.subheader("Ingestion de Documents PDF")
    st.markdown("""
    <div style="padding: 2rem 0;">
        <h2 style="color: #343a40; font-weight: 360; font-size: 2rem; margin: 0;">Ingestion de Documents PDF</h2>
    </div>
    """, unsafe_allow_html=True)
    # Moniteur des tâches en cours avec rafraîchissement automatique
    task_manager = get_task_manager()
    active_tasks = task_manager.get_active_tasks()
    
    if active_tasks:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            with st.expander(f"[ACTIF] {len(active_tasks)} tâche(s) en cours", expanded=True):
                render_task_monitor(show_completed=False, key_prefix="ingestion_active")
        
        with col2:
            if st.button("Actualiser", help="Rafraîchir l'état des tâches"):
                st.rerun()
            
            # Auto-refresh toutes les 10 secondes si des tâches sont actives
            import time
            if 'last_auto_refresh' not in st.session_state:
                st.session_state.last_auto_refresh = time.time()
            elif time.time() - st.session_state.last_auto_refresh > 10:
                st.session_state.last_auto_refresh = time.time()
                st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["Upload Fichiers", "Dossier Local", "Historique"])
    
    with tab1:
        st.markdown("**Upload et traitement asynchrone de fichiers PDF**")
        
        # Upload de fichiers
        uploaded_files = st.file_uploader(
            "Sélectionner des fichiers PDF",
            type=['pdf'],
            accept_multiple_files=True,
            help="Vous pouvez sélectionner plusieurs fichiers PDF à traiter"
        )
        
        if uploaded_files:
            st.success(f"  {len(uploaded_files)} fichier(s) sélectionné(s)")
            
            col1, col2 = st.columns(2)
            with col1:
                text_only = st.checkbox("Texte seulement (plus rapide)", value=False)
            with col2:
                overwrite = st.checkbox("Écraser fichiers existants", value=False)
            
            col_btn1, col_btn2 = st.columns([1, 3])
            
            with col_btn1:
                if st.button("Traiter (Async)", type="primary", help="Lance le traitement en arrière-plan"):
                    launch_async_upload(uploaded_files, text_only, overwrite)
            
            with col_btn2:
                if st.button("Traitement Immédiat", help="Traitement synchrone (bloquant)"):
                    process_uploaded_files(uploaded_files, text_only, overwrite)
    
    with tab2:
        st.markdown("**Sélection et ingestion d'un dossier complet**")
        
        # Sélecteur de dossier avec st.file_uploader
        folder_files = st.file_uploader(
            "Sélectionner un dossier contenant des PDFs",
            accept_multiple_files="directory",
            type=["pdf"],
            help="Cliquez pour ouvrir l'explorateur de fichiers et sélectionner un dossier"
        )
        
        if folder_files:
            st.success(f"Dossier sélectionné: {len(folder_files)} fichiers PDF trouvés")
            
            # Afficher un aperçu des fichiers
            with st.expander(f"Aperçu des fichiers ({min(len(folder_files), 5)} premiers)", expanded=False):
                for i, file in enumerate(folder_files[:5]):
                    st.write(f"• {file.name}")
                if len(folder_files) > 5:
                    st.write(f"... et {len(folder_files) - 5} autres")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                text_only_folder = st.checkbox("Texte seulement", value=True, key="folder_text_only")
            with col2:
                parallel = st.checkbox("Traitement parallèle", value=True)
            with col3:
                workers = st.number_input("Workers", min_value=1, max_value=8, value=4)
            
            col_btn1, col_btn2 = st.columns([1, 3])
            
            with col_btn1:
                if st.button("Ingérer Async", type="primary", help="Lance l'ingestion en arrière-plan"):
                    launch_async_folder_files_ingestion(folder_files, text_only_folder, parallel, workers)
            
            with col_btn2:
                if st.button("Ingestion Immédiate", help="Ingestion synchrone bloquante"):
                    process_folder_files_ingestion(folder_files, text_only_folder, parallel, workers)
    
    with tab3:
        st.markdown("**Historique des tâches d'ingestion**")
        render_task_monitor(show_completed=True, max_tasks=50, key_prefix="ingestion_history")


def launch_async_upload(uploaded_files: List, text_only: bool, overwrite: bool):
    """Lance l'upload de fichiers en mode asynchrone"""
    try:
        task_manager = get_task_manager()
        
        # Créer une copie des fichiers pour le thread
        file_data = []
        for uploaded_file in uploaded_files:
            file_data.append({
                'name': uploaded_file.name,
                'content': uploaded_file.getvalue()
            })
        
        # Lancer la tâche asynchrone
        task_id = task_manager.create_task(
            name=f"Upload {len(uploaded_files)} PDF(s)",
            task_func=async_upload_files,
            uploaded_files=file_data,
            text_only=text_only,
            overwrite=overwrite
        )
        
        st.success(f"Tâche lancée! ID: {task_id}")
        st.info("Le traitement se fait en arrière-plan. Vous pouvez continuer à utiliser l'application.")
        
        # Forcer un rafraîchissement pour voir la tâche
        st.rerun()
        
    except Exception as e:
        st.error(f"Erreur de lancement: {e}")
        import traceback
        st.code(traceback.format_exc())


def launch_async_folder_files_ingestion(folder_files: List, text_only: bool, parallel: bool, workers: int):
    """Lance l'ingestion de fichiers de dossier en mode asynchrone"""
    try:
        task_manager = get_task_manager()
        
        # Convertir les fichiers Streamlit en données pour le thread
        file_data = []
        for uploaded_file in folder_files:
            file_data.append({
                'name': uploaded_file.name,
                'content': uploaded_file.getvalue()
            })
        
        task_id = task_manager.create_task(
            name=f"Ingestion {len(folder_files)} PDF(s) dossier",
            task_func=async_upload_files,  # Réutiliser la fonction existante
            uploaded_files=file_data,
            text_only=text_only,
            overwrite=False
        )
        
        st.success(f"Tâche lancée! ID: {task_id}")
        st.info("L'ingestion se fait en arrière-plan. Vous pouvez continuer à utiliser l'application.")
        
        # Forcer un rafraîchissement pour voir la tâche
        st.rerun()
        
    except Exception as e:
        st.error(f"Erreur de lancement: {e}")
        import traceback
        st.code(traceback.format_exc())


def launch_async_folder_ingestion(folder_path: str, text_only: bool, parallel: bool, workers: int):
    """Lance l'ingestion de dossier en mode asynchrone"""
    try:
        task_manager = get_task_manager()
        
        task_id = task_manager.create_task(
            name=f"Ingestion {folder_path}",
            task_func=async_folder_ingestion,
            folder_path=folder_path,
            text_only=text_only,
            parallel=parallel,
            workers=workers
        )
        
        st.success(f"Tâche lancée! ID: {task_id}")
        st.info("L'ingestion se fait en arrière-plan. Vous pouvez continuer à utiliser l'application.")
        
        # Forcer un rafraîchissement pour voir la tâche
        st.rerun()
        
    except Exception as e:
        st.error(f"Erreur de lancement: {e}")


def process_uploaded_files(uploaded_files: List, text_only: bool, overwrite: bool):
    """Traite les fichiers uploadés"""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Utiliser le dossier Data/ au lieu d'un dossier temporaire
        data_dir = os.path.join(os.getcwd(), 'Data')
        os.makedirs(data_dir, exist_ok=True)
        saved_paths = []
        
        # Vérifier et préparer les fichiers dans Data/
        for i, uploaded_file in enumerate(uploaded_files):
            # Extraire juste le nom du fichier sans le chemin de dossier
            filename = os.path.basename(uploaded_file.name)
            data_path = os.path.join(data_dir, filename)
            
            if os.path.exists(data_path):
                # Fichier existe déjà dans Data/, l'utiliser
                status_text.text(f"Fichier existant: {uploaded_file.name}")
                progress_bar.progress((i + 1) / (len(uploaded_files) * 2))
                saved_paths.append(data_path)
            else:
                # Fichier n'existe pas, le copier dans Data/
                status_text.text(f"Nouveau fichier: {uploaded_file.name}")
                progress_bar.progress((i + 1) / (len(uploaded_files) * 2))
                
                try:
                    with open(data_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    saved_paths.append(data_path)
                except Exception as e:
                    st.error(f"Erreur lors de la copie de {uploaded_file.name}: {e}")
                    continue
        
        # Traitement
        health = check_database_health()
        
        if health.get("healthy", False):
            # Base existante - utiliser upload manager
            status_text.text(f"Traitement avec base existante... (text_only={text_only})")
            manager = PDFUploadManager(data_folder="./Data")
            
            results = manager.upload_multiple_pdfs(
                saved_paths,
                copy_to_data=False,  # Fichiers déjà dans Data/, pas de copie
                text_only=text_only,
                overwrite_existing=overwrite
            )
            
            progress_bar.progress(1.0)
            status_text.text("  Traitement terminé!")
            
            st.success(f"Upload terminé: {results['successful_uploads']}/{results['total_files']} fichiers")
            st.info(f"Nouveaux chunks: {results['total_chunks_added']:,}")
            
            if results.get('errors'):
                with st.expander("[ATTENTION] Erreurs rencontrées", expanded=False):
                    for error in results['errors'][:10]:
                        st.write(f"• {error}")
        
        else:
            # Base inexistante - créer avec ingestion
            status_text.text("Création de nouvelle base...")
            manager = PDFIngestionManager()
            
            success_count = 0
            for i, file_path in enumerate(saved_paths):
                status_text.text(f"Traitement: {os.path.basename(file_path)}")
                progress_bar.progress(0.5 + (i + 1) / (len(saved_paths) * 2))
                
                if manager.ingest_single_pdf(file_path, text_only=text_only):
                    success_count += 1
            
            progress_bar.progress(1.0)
            status_text.text("Ingestion terminée!")
            
            st.success(f"Ingestion terminée: {success_count}/{len(saved_paths)} fichiers")
        
        # Les fichiers sont maintenant dans Data/ de façon permanente
        
    except Exception as e:
        st.error(f"  Erreur de traitement: {e}")


def process_folder_files_ingestion(folder_files: List, text_only: bool, parallel: bool, workers: int):
    """Traite l'ingestion des fichiers de dossier sélectionnés"""
    try:
        # Réutiliser la logique existante en traitant les fichiers comme des uploads
        process_uploaded_files(folder_files, text_only, overwrite=False)
        
    except Exception as e:
        st.error(f"Erreur d'ingestion dossier: {e}")


def process_folder_ingestion(folder_path: str, text_only: bool, parallel: bool, workers: int):
    """Traite l'ingestion depuis un dossier"""
    if not os.path.exists(folder_path):
        st.error(f"Le dossier {folder_path} n'existe pas")
        return
    
    try:
        with st.spinner("Ingestion en cours..."):
            manager = PDFIngestionManager()
            
            success = manager.ingest_from_folder(
                folder_path,
                text_only=text_only,
                parallel=parallel,
                workers=workers
            )
            
            if success:
                st.success("Ingestion terminée!")
                
                # Statistiques
                stats = manager.verify_ingestion()
                with st.expander("Statistiques post-ingestion", expanded=True):
                    for key, value in stats.items():
                        st.write(f"**{key}:** {value}")
            else:
                st.error("Erreurs lors de l'ingestion")
                
    except Exception as e:
        st.error(f"Erreur: {e}")


def render_database_summary():
    """Interface de résumé de base de données"""
    st.subheader("Résumé de la Base")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Générer Résumé", type="primary"):
            generate_summary()
    
    with col2:
        format_type = st.selectbox("Format Export", ["json", "csv", "txt"])
        if st.button("Exporter"):
            export_summary(format_type)


def generate_summary():
    """Génère et affiche le résumé détaillé"""
    try:
        with st.spinner("Génération du résumé..."):
            manager = DatabaseSummaryManager()
            summary = manager.get_complete_summary()
            
            if not summary:
                st.warning("Aucune donnée trouvée")
                return
            
            # Statistiques générales
            stats = summary.get("statistics", {})
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Chunks", f"{stats.get('total_chunks', 0):,}")
            with col2:
                st.metric("Documents", stats.get('total_unique_documents', 0))
            with col3:
                st.metric("Réglementations", stats.get('total_regulations', 0))
            with col4:
                avg = stats.get('average_chunks_per_regulation', 0)
                st.metric("Moy/Rég", f"{avg:.1f}")
            
            # Collections
            collections = summary.get("collections", {})
            st.markdown("**État des Collections:**")
            
            for col_type, col_info in collections.items():
                if isinstance(col_info, dict):
                    status = " " if col_info.get("exists", False) else " "
                    count = col_info.get("count", 0)
                    st.write(f"{status} **{col_type.capitalize()}:** {count:,} documents")
            
            # Top réglementations
            if stats.get("largest_regulation"):
                largest = stats["largest_regulation"]
                smallest = stats.get("smallest_regulation")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"[PLUS-GRANDE] **Plus grande:** {largest['code']} ({largest['chunks_count']:,})")
                with col2:
                    if smallest:
                        st.info(f"[PLUS-PETITE] **Plus petite:** {smallest['code']} ({smallest['chunks_count']})")
            
            # Liste des réglementations (aperçu)
            regulations = summary.get("regulations", {})
            reg_list = regulations.get("regulations_list", [])[:15]
            
            if reg_list:
                st.markdown("**Réglementations Disponibles:**")
                
                # Affichage en colonnes
                cols = st.columns(3)
                for i, reg in enumerate(reg_list):
                    with cols[i % 3]:
                        st.write(f"• {reg}")
                
                total_regs = regulations.get("total_regulations", 0)
                if total_regs > 15:
                    st.write(f"... et {total_regs - 15} autres")
                    
    except Exception as e:
        st.error(f"  Erreur: {e}")


def export_summary(format_type: str):
    """Exporte le résumé"""
    try:
        manager = DatabaseSummaryManager()
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"db_summary_{timestamp}.{format_type}"
        
        manager.export_summary(filename)
        
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                st.download_button(
                    label=f"Télécharger {filename}",
                    data=f.read(),
                    file_name=filename,
                    mime=f"application/{format_type}"
                )
            os.remove(filename)
            
    except Exception as e:
        st.error(f"Erreur d'export: {e}")


def render_regulation_search():
    """Interface de recherche par réglementation"""
    st.subheader("Recherche par Réglementation")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        regulation_code = st.text_input(
            "Code de réglementation",
            placeholder="R046, ECE R46, UN R107...",
            help="Le système teste automatiquement différentes variantes"
        )
    
    with col2:
        detailed = st.checkbox("Recherche détaillée", value=False)
    
    if regulation_code:
        if st.button("Rechercher", type="primary"):
            search_regulation(regulation_code, detailed)


def search_regulation(regulation_code: str, detailed: bool):
    """Recherche une réglementation"""
    try:
        with st.spinner(f"Recherche de {regulation_code}..."):
            manager = RegulationSearchManager()
            
            if detailed:
                result = manager.search_regulation_complete(regulation_code)
                display_detailed_result(result)
            else:
                result = manager.search_regulation_summary(regulation_code)
                display_summary_result(result)
                
    except Exception as e:
        st.error(f"Erreur de recherche: {e}")


def display_summary_result(result: Dict):
    """Affiche le résultat résumé"""
    if not result.get("found", False):
        st.error(f"'{result.get('regulation_code', 'N/A')}' non trouvée")
        return
    
    st.success(f"'{result['regulation_code']}' trouvée")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Chunks", result.get("total_chunks", 0))
    with col2:
        st.metric("Documents", result.get("documents_count", 0))
    with col3:
        st.metric("Pages", result.get("pages_count", 0))
    with col4:
        st.metric("Variant", result.get("variant_used", "N/A"))


def display_detailed_result(result: Dict):
    """Affiche le résultat détaillé"""
    if not result.get("text_chunks"):
        st.error(f"'{result.get('regulation_code', 'N/A')}' non trouvée")
        return
    
    st.success(f"'{result['regulation_code']}' trouvée")
    
    # Statistiques détaillées
    stats = result.get("statistics", {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Chunks", stats.get("total_chunks", 0))
    with col2:
        st.metric("Texte", stats.get("text_chunks_count", 0))
    with col3:
        st.metric("Images", stats.get("image_chunks_count", 0))
    with col4:
        st.metric("Tables", stats.get("table_chunks_count", 0))
    
    # Analyse du contenu
    content = result.get("content_analysis", {})
    if any(content.values()):
        st.markdown("**Analyse du Contenu:**")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Exigences", content.get("requirements_count", 0))
        with col2:
            st.metric("Définitions", content.get("definitions_count", 0))
        with col3:
            st.metric("Procédures", content.get("procedures_count", 0))
        with col4:
            st.metric("Références", content.get("references_count", 0))
    
    # Export des données
    if st.button("Exporter Données"):
        try:
            reg_code = result.get("regulation_code", "unknown")
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            
            st.download_button(
                label=f"Télécharger {reg_code}_data.json",
                data=json_str,
                file_name=f"{reg_code}_data.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Erreur d'export: {e}")


def render_regulations_list():
    """Interface de listage des réglementations"""
    st.subheader("Liste des Réglementations")
    
    # Filtres
    with st.expander("Filtres Avancés", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            min_chunks = st.number_input("Chunks minimum", min_value=0, value=0)
            has_images = st.selectbox("Avec images", ["Peu importe", "Oui", "Non"])
        
        with col2:
            max_chunks = st.number_input("Chunks maximum", min_value=0, value=0)
            has_tables = st.selectbox("Avec tables", ["Peu importe", "Oui", "Non"])
        
        contains = st.text_input("Contient le texte")
        
        # Convertir les filtres
        has_images = None if has_images == "Peu importe" else (has_images == "Oui")
        has_tables = None if has_tables == "Peu importe" else (has_tables == "Oui")
        max_chunks = max_chunks if max_chunks > 0 else None
        min_chunks = min_chunks if min_chunks > 0 else None
    
    # Boutons d'action
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Lister Toutes", type="primary"):
            list_all_regulations()
    
    with col2:
        if st.button("Appliquer Filtres"):
            list_filtered_regulations(min_chunks, max_chunks, has_images, has_tables, contains)


def list_all_regulations():
    """Liste toutes les réglementations"""
    try:
        with st.spinner("Récupération..."):
            manager = RegulationListManager()
            data = manager.get_all_regulations()
            display_regulations_table(data)
    except Exception as e:
        st.error(f"Erreur: {e}")


def list_filtered_regulations(min_chunks, max_chunks, has_images, has_tables, contains):
    """Liste avec filtres"""
    try:
        with st.spinner("Filtrage..."):
            manager = RegulationListManager()
            
            filtered = manager.get_regulations_by_criteria(
                min_chunks=min_chunks,
                max_chunks=max_chunks,
                has_images=has_images,
                has_tables=has_tables,
                contains_text=contains if contains else None
            )
            
            st.write(f"**{len(filtered)} réglementations** correspondent aux critères")
            
            if filtered:
                df = pd.DataFrame({"Code Réglementation": filtered})
                st.dataframe(df, width='stretch')
            else:
                st.info("Aucun résultat")
                
    except Exception as e:
        st.error(f" Erreur: {e}")


def display_regulations_table(data: Dict):
    """Affiche la table des réglementations"""
    try:
        details = data.get("regulations_details", {})
        
        if not details:
            st.info("Aucune réglementation trouvée")
            return
        
        # Créer DataFrame
        rows = []
        for reg_code, reg_details in details.items():
            chunks = reg_details.get("chunks", {})
            rows.append({
                "Code": reg_code,
                "Documents": reg_details.get("documents_count", 0),
                "Total": chunks.get("total", 0),
                "Texte": chunks.get("text", 0),
                "Images": chunks.get("images", 0),
                "Tables": chunks.get("tables", 0),
                "Pages": reg_details.get("pages", {}).get("count", 0)
            })
        
        df = pd.DataFrame(rows).sort_values("Total", ascending=False)
        
        # Statistiques générales
        stats = data.get("statistics", {})
        st.markdown("**Résumé:**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Réglementations", stats.get("total_regulations", 0))
        with col2:
            st.metric("Documents", stats.get("total_documents", 0))
        with col3:
            st.metric("Chunks", f"{stats.get('total_chunks', 0):,}")
        
        # Tableau
        st.dataframe(df, width='stretch')
        
        # Export CSV
        csv = df.to_csv(index=False)
        st.download_button("CSV", csv, "regulations.csv", "text/csv")
        
    except Exception as e:
        st.error(f"Erreur d'affichage: {e}")


def render_database_cleanup():
    """Interface de nettoyage"""
    st.subheader("Nettoyage de la Base")
    
    st.warning("**ATTENTION:** Ces opérations suppriment définitivement des données!")
    
    tab1, tab2, tab3 = st.tabs(["Collections", "Sélectif", "Complet"])
    
    with tab1:
        collection = st.selectbox("Collection à vider", ["text", "images", "tables", "toutes"])
        
        if st.button("Vider Collection", type="secondary"):
            cleanup_collections(collection)
    
    with tab2:
        regulations = st.text_area(
            "Réglementations à supprimer (une par ligne)",
            placeholder="R046\nECE R107\nUN R048"
        )
        
        if regulations and st.button("Supprimer Sélection", type="secondary"):
            reg_codes = [code.strip() for code in regulations.split('\n') if code.strip()]
            cleanup_selective(reg_codes)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Vider Tout", type="secondary"):
                cleanup_complete()
        
        with col2:
            if st.button("Supprimer Fichiers", type="secondary"):
                cleanup_files()


def cleanup_collections(collection: str):
    """Nettoie les collections"""
    try:
        with st.spinner("Nettoyage..."):
            manager = DatabaseCleanupManager()
            
            if collection == "toutes":
                results = manager.clear_all_collections()
                st.success("  Toutes les collections vidées")
                
                for col_type, success in results.items():
                    status = " " if success else " "
                    st.write(f"{status} {col_type}")
            else:
                success = manager.clear_collection(collection)
                if success:
                    st.success(f"  Collection {collection} vidée")
                else:
                    st.error(f"  Erreur avec {collection}")
                    
    except Exception as e:
        st.error(f"  Erreur: {e}")


def cleanup_selective(reg_codes: List[str]):
    """Nettoyage sélectif"""
    try:
        with st.spinner("Suppression..."):
            manager = DatabaseCleanupManager()
            results = manager.selective_cleanup(reg_codes)
            
            st.success(f"  {results['deleted_documents']} documents supprimés")
            
            for reg in results.get('regulations_processed', []):
                st.write(f"• {reg['code']}: {reg['deleted_count']} documents")
            
            if results.get('errors'):
                with st.expander("[ERREURS] Erreurs", expanded=False):
                    for error in results['errors']:
                        st.write(f"• {error}")
                        
    except Exception as e:
        st.error(f"  Erreur: {e}")


def cleanup_complete():
    """Nettoyage complet avec confirmation"""
    if not st.session_state.get("confirm_cleanup", False):
        st.error("[ATTENTION] Cette action supprimera TOUTES les données!")
        if st.checkbox("Je confirme vouloir tout supprimer", key="confirm_cleanup"):
            st.rerun()
        return
    
    try:
        with st.spinner("Nettoyage complet..."):
            manager = DatabaseCleanupManager()
            
            results = manager.clear_all_collections()
            cache_ok = manager.clean_cache_files()
            
            st.success("  Nettoyage complet terminé!")
            
            for col_type, success in results.items():
                status = " " if success else " "
                st.write(f"{status} {col_type}")
            
            st.write(f"{' ' if cache_ok else ' '} Cache nettoyé")
            
        st.session_state["confirm_cleanup"] = False
        
    except Exception as e:
        st.error(f"  Erreur: {e}")


def cleanup_files():
    """Suppression des fichiers avec confirmation"""
    if not st.session_state.get("confirm_files", False):
        st.error("[ATTENTION] Suppression PHYSIQUE des fichiers DB!")
        if st.checkbox("Je confirme la suppression des fichiers", key="confirm_files"):
            st.rerun()
        return
    
    try:
        with st.spinner("Suppression des fichiers..."):
            manager = DatabaseCleanupManager()
            success = manager.delete_database_files(force=True)
            
            if success:
                st.success("  Fichiers supprimés!")
            else:
                st.error("  Erreur de suppression")
                
        st.session_state["confirm_files"] = False
        
    except Exception as e:
        st.error(f"  Erreur: {e}")


def main():
    """Fonction principale de la page database"""
    
    # Vérification admin obligatoire
    if not require_modern_admin_access():
        return
    
    # Initialisation
    initialize_session_state()

    # État de la base
    health = render_database_status()
    
    st.divider()
    
    # Navigation par onglets
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ingestion",
        "Résumé",
        "Recherche",
        "Liste",
        "Nettoyage"
    ])
    
    with tab1:
        render_pdf_ingestion()
    
    with tab2:
        render_database_summary()
    
    with tab3:
        render_regulation_search()
    
    with tab4:
        render_regulations_list()
    
    with tab5:
        render_database_cleanup()
    
    # Footer d'aide
    st.divider()
    with st.expander("[GUIDE] Guide d'utilisation", expanded=False):
        st.markdown("""
        **[CONSEILS] Conseils pour une utilisation optimale:**
        
        **Ingestion:**
        - Utilisez "Texte seulement" pour un traitement plus rapide
        - Le traitement parallèle améliore les performances
        - Vérifiez l'état de la base avant ingestion massive
        
        **Recherche:**
        - Le système reconnaît automatiquement R46, R046, ECE R46, etc.
        - La recherche détaillée fournit l'analyse du contenu
        
        **Nettoyage:**
        - Toujours faire une sauvegarde avant nettoyage complet
        - Le nettoyage sélectif préserve les autres réglementations
        - La suppression de fichiers est irréversible
        
        **Performance:**
        - Surveillez régulièrement l'état des collections
        - Nettoyez le cache périodiquement
        - Optimisez le nombre de workers selon votre CPU
        """)


def render_user_management():
    """Affiche l'interface de gestion des utilisateurs (Admin uniquement)"""
    st.markdown("""
    <div style="padding: 1rem 0;">
        <h2 style="color: #343a40; font-weight: 360; font-size: 1.5rem; margin: 0;">Gestion des Utilisateurs</h2>
        <p style="color: #6c757d; font-size: 0.9rem;">Créer, modifier et supprimer des comptes utilisateurs</p>
    </div>
    """, unsafe_allow_html=True)

    auth = SimpleAuth()

    # Section 1: Créer un nouvel utilisateur
    st.markdown("### ➕ Créer un utilisateur")
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_username = st.text_input("Nom d'utilisateur", placeholder="Minimum 3 caractères")
            new_password = st.text_input("Mot de passe", type="password", placeholder="Minimum 6 caractères")

        with col2:
            new_role = st.selectbox("Rôle", options=["user", "admin"],
                                   help="Admin: accès complet | User: accès limité")
            st.markdown("<br>", unsafe_allow_html=True)

        submitted = st.form_submit_button("✅ Créer l'utilisateur", type="primary", use_container_width=True)

        if submitted:
            if new_username and new_password:
                success, message = auth.create_user(new_username, new_password, new_role)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Veuillez remplir tous les champs")

    st.divider()

    # Section 2: Liste des utilisateurs existants
    st.markdown("### 👥 Utilisateurs existants")

    users = auth.list_users()

    if not users:
        st.info("Aucun utilisateur trouvé")
    else:
        # Afficher le nombre total
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total utilisateurs", len(users))
        with col2:
            admin_count = sum(1 for u in users if u[1] == 'admin')
            st.metric("Administrateurs", admin_count)
        with col3:
            user_count = sum(1 for u in users if u[1] == 'user')
            st.metric("Utilisateurs", user_count)

        st.markdown("<br>", unsafe_allow_html=True)

        # Créer un DataFrame pour l'affichage
        users_data = []
        for username, role, created_at in users:
            users_data.append({
                "Utilisateur": username,
                "Rôle": role.upper(),
                "Créé le": created_at,
                "Actions": username  # Pour la colonne actions
            })

        df = pd.DataFrame(users_data)

        # Afficher chaque utilisateur avec des actions
        for idx, user in enumerate(users):
            username, role, created_at = user

            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 3, 2, 2])

                with col1:
                    # Badge avec icône selon le rôle
                    if role == 'admin':
                        st.markdown(f"**👑 {username}**")
                    else:
                        st.markdown(f"**👤 {username}**")

                with col2:
                    if role == 'admin':
                        st.markdown("🔴 `ADMIN`")
                    else:
                        st.markdown("🔵 `USER`")

                with col3:
                    # Formater la date
                    try:
                        date_obj = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                    except:
                        formatted_date = created_at
                    st.text(formatted_date)

                with col4:
                    # Bouton pour changer le rôle
                    new_role = "admin" if role == "user" else "user"
                    if st.button(f"→ {new_role.upper()}", key=f"role_{username}_{idx}",
                                help=f"Changer le rôle vers {new_role}"):
                        success, message = auth.update_user_role(username, new_role)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                with col5:
                    # Bouton pour supprimer
                    if st.button("🗑️ Suppr.", key=f"delete_{username}_{idx}",
                                type="secondary", help=f"Supprimer {username}"):
                        success, message = auth.delete_user(username)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

    st.divider()

    # Section 3: Réinitialiser le mot de passe
    st.markdown("### 🔑 Réinitialiser un mot de passe")

    if users:
        with st.form("reset_password_form"):
            col1, col2 = st.columns(2)

            with col1:
                user_to_reset = st.selectbox(
                    "Sélectionner un utilisateur",
                    options=[u[0] for u in users],
                    help="Choisir l'utilisateur dont le mot de passe sera réinitialisé"
                )

            with col2:
                new_pwd = st.text_input("Nouveau mot de passe", type="password",
                                       placeholder="Minimum 6 caractères")

            reset_submitted = st.form_submit_button("🔄 Réinitialiser le mot de passe",
                                                   type="primary", use_container_width=True)

            if reset_submitted:
                if user_to_reset and new_pwd:
                    success, message = auth.reset_password(user_to_reset, new_pwd)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Veuillez remplir tous les champs")
    else:
        st.info("Aucun utilisateur disponible")

    # Avertissement de sécurité
    st.divider()
    st.warning("""
    **⚠️ Consignes de sécurité:**
    - Ne supprimez jamais le dernier administrateur
    - Utilisez des mots de passe forts (minimum 6 caractères)
    - Changez régulièrement les mots de passe par défaut
    - Auditez régulièrement les comptes utilisateurs
    """)


if __name__ == "__main__":
    main()