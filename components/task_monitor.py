"""
Composant de monitoring des tâches asynchrones
Interface Streamlit pour suivre les tâches en cours et terminées
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import List, Optional
from utils.task_manager import get_task_manager, TaskStatus, TaskInfo
from translations import t


def render_task_monitor(show_completed: bool = True, max_tasks: int = 20, key_prefix: str = "main"):
    """
    Affiche le moniteur de tâches dans la sidebar ou en section principale
    
    Args:
        show_completed: Afficher les tâches terminées
        max_tasks: Nombre maximum de tâches à afficher
        key_prefix: Préfixe pour les clés d'éléments (éviter les doublons)
    """
    task_manager = get_task_manager()
    
    # Nettoyer les anciennes tâches terminées
    task_manager.cleanup_completed_tasks()
    
    # Récupérer les tâches
    active_tasks = task_manager.get_active_tasks()
    all_tasks = task_manager.get_all_tasks()
    
    # Filtrer et trier les tâches
    if show_completed:
        display_tasks = sorted(all_tasks, key=lambda t: t.started_at or datetime.min, reverse=True)[:max_tasks]
    else:
        display_tasks = active_tasks
    
    # En-tête avec compteurs
    active_count = len(active_tasks)
    
    if active_count > 0:
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #2ecc71, #27ae60); color: white; 
                    padding: 10px; border-radius: 8px; margin-bottom: 15px;">
            <strong>🔄 {active_count} tâche(s) en cours</strong>
        </div>
        """, unsafe_allow_html=True)
    
    # Affichage des tâches
    if not display_tasks:
        st.info(t('no_task_running'))
        return
    
    # Grouper par statut
    running_tasks = [t for t in display_tasks if t.status == TaskStatus.RUNNING]
    pending_tasks = [t for t in display_tasks if t.status == TaskStatus.PENDING]
    completed_tasks = [t for t in display_tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]]
    
    # Tâches en cours d'exécution
    if running_tasks:
        st.markdown("### 🔄 En cours")
        for i, task in enumerate(running_tasks):
            render_task_card(task, expanded=True, key_prefix=f"{key_prefix}_running_{i}")
    
    # Tâches en attente
    if pending_tasks:
        st.markdown(f"### ⏳ {t('pending')}")
        for i, task in enumerate(pending_tasks):
            render_task_card(task, expanded=False, key_prefix=f"{key_prefix}_pending_{i}")
    
    # Tâches terminées (si demandées)
    if show_completed and completed_tasks:
        with st.expander(f"📋 Historique ({len(completed_tasks)} tâches)", expanded=False):
            for i, task in enumerate(completed_tasks[:10]):  # Limiter l'historique
                render_task_card(task, expanded=False, show_details=False, key_prefix=f"{key_prefix}_completed_{i}")


def render_task_card(task: TaskInfo, expanded: bool = False, show_details: bool = True, key_prefix: str = "card"):
    """
    Affiche une carte pour une tâche individuelle
    
    Args:
        task: Information de la tâche
        expanded: Afficher les détails par défaut
        show_details: Afficher les détails complets
        key_prefix: Préfixe pour les clés d'éléments
    """
    # Icône et couleur selon le statut
    status_config = {
        TaskStatus.PENDING: {"icon": "⏳", "color": "#f39c12"},
        TaskStatus.RUNNING: {"icon": "🔄", "color": "#3498db"},
        TaskStatus.COMPLETED: {"icon": "✅", "color": "#2ecc71"},
        TaskStatus.FAILED: {"icon": "❌", "color": "#e74c3c"},
        TaskStatus.CANCELLED: {"icon": "⏹️", "color": "#95a5a6"}
    }
    
    config = status_config.get(task.status, {"icon": "❓", "color": "#7f8c8d"})
    
    # Calculer la durée
    duration_text = ""
    if task.started_at:
        if task.completed_at:
            duration = task.completed_at - task.started_at
            duration_text = f" ({format_duration(duration)})"
        elif task.status == TaskStatus.RUNNING:
            duration = datetime.now() - task.started_at
            duration_text = f" ({format_duration(duration)})"
    
    # En-tête de la tâche
    header_html = f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <span style="font-size: 20px; margin-right: 8px;">{config['icon']}</span>
        <strong style="color: {config['color']};">{task.name}</strong>
        <span style="color: #7f8c8d; font-size: 0.9em; margin-left: auto;">{duration_text}</span>
    </div>
    """
    
    if show_details:
        with st.expander(f"{config['icon']} {task.name}{duration_text}", expanded=expanded):
            st.markdown(header_html, unsafe_allow_html=True)
            
            # Message actuel
            if task.message:
                st.write(f"📝 **Statut:** {task.message}")
            
            # Barre de progression
            if task.status == TaskStatus.RUNNING:
                progress_pct = int(task.progress * 100)
                st.progress(task.progress)
                st.write(f"⚡ **Progression:** {progress_pct}%")
            
            # Informations détaillées
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"🆔 **ID:** `{task.id}`")
                if task.started_at:
                    st.write(f"🕐 **Démarré:** {task.started_at.strftime('%H:%M:%S')}")
            
            with col2:
                st.write(f"📊 **État:** {task.status.value.capitalize()}")
                if task.completed_at:
                    st.write(f"🏁 **Terminé:** {task.completed_at.strftime('%H:%M:%S')}")
            
            # Résultats ou erreurs
            if task.status == TaskStatus.COMPLETED and task.result:
                with st.expander("📊 Résultats", expanded=False):
                    display_task_results(task.result)
            
            elif task.status == TaskStatus.FAILED and task.error:
                st.error(f"❌ **Erreur:** {task.error}")
            
            # Actions
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                if st.button(f"⏹️ Annuler", key=f"cancel_{key_prefix}_{task.id}"):
                    task_manager = get_task_manager()
                    if task_manager.cancel_task(task.id):
                        st.success(t('task_cancelled'))
                        st.rerun()
    else:
        # Affichage compact
        status_text = task.status.value.capitalize()
        st.write(f"{config['icon']} **{task.name}** - {status_text}{duration_text}")


def display_task_results(result: dict):
    """Affiche les résultats d'une tâche terminée"""
    if not result:
        st.info(t('no_result_available'))
        return
    
    task_type = result.get("type", "unknown")
    
    if task_type == "upload":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Fichiers traités", result.get("successful_uploads", 0))
        with col2:
            st.metric("Total fichiers", result.get("total_files", 0))
        with col3:
            st.metric("Chunks ajoutés", result.get("total_chunks_added", 0))
        
        errors = result.get("errors", [])
        if errors:
            st.warning(f"⚠️ {len(errors)} erreur(s) rencontrée(s)")
            with st.expander("Détails des erreurs", expanded=False):
                for error in errors[:5]:  # Limiter l'affichage
                    st.write(f"• {error}")
    
    elif task_type == "folder_ingestion":
        if result.get("success"):
            st.success(t('ingestion_success'))
            
            stats = result.get("stats", {})
            if stats:
                st.json(stats)
        else:
            st.error(t('ingestion_failed'))
    
    elif task_type == "ingestion":
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Fichiers traités", result.get("successful_uploads", 0))
        with col2:
            st.metric("Total fichiers", result.get("total_files", 0))


def render_task_notifications():
    """Affiche les notifications de tâches dans la sidebar"""
    task_manager = get_task_manager()
    active_tasks = task_manager.get_active_tasks()
    
    if not active_tasks:
        return
    
    # Notification compacte dans la sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 Tâches Actives")
    
    for i, task in enumerate(active_tasks):
        if task.status == TaskStatus.RUNNING:
            progress_pct = int(task.progress * 100)
            st.sidebar.write(f"🔄 {task.name}")
            st.sidebar.progress(task.progress)
            st.sidebar.caption(f"{progress_pct}% - {task.message}")
        else:
            st.sidebar.write(f"⏳ {task.name}")
            st.sidebar.caption("En attente...")
    
    # Bouton pour rafraîchir
    if st.sidebar.button("🔄 Actualiser", key="refresh_tasks_sidebar"):
        st.rerun()


def format_duration(duration: timedelta) -> str:
    """Formate une durée pour affichage"""
    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def auto_refresh_tasks(interval: int = 5):
    """
    Auto-refresh des tâches toutes les X secondes
    À utiliser avec st.empty() et une boucle
    """
    task_manager = get_task_manager()
    
    # Vérifier s'il y a des tâches actives
    active_tasks = task_manager.get_active_tasks()
    
    if active_tasks and 'last_task_refresh' in st.session_state:
        last_refresh = st.session_state.last_task_refresh
        if (datetime.now() - last_refresh).seconds >= interval:
            st.session_state.last_task_refresh = datetime.now()
            st.rerun()
    elif active_tasks:
        st.session_state.last_task_refresh = datetime.now()


def render_task_status_bar():
    """Affiche une barre de statut pour les tâches actives"""
    task_manager = get_task_manager()
    active_tasks = task_manager.get_active_tasks()
    
    if not active_tasks:
        return
    
    running_count = len([t for t in active_tasks if t.status == TaskStatus.RUNNING])
    pending_count = len([t for t in active_tasks if t.status == TaskStatus.PENDING])
    
    # Barre de statut compacte
    status_html = f"""
    <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(52, 73, 94, 0.95);
        color: white;
        padding: 10px 15px;
        border-radius: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1000;
        font-size: 14px;
        backdrop-filter: blur(10px);
    ">
        🔄 {running_count} en cours • ⏳ {pending_count} en attente
    </div>
    """
    
    st.markdown(status_html, unsafe_allow_html=True)