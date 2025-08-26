"""
Gestionnaire de tâches asynchrones pour l'ingestion de documents
Permet d'exécuter des tâches en arrière-plan sans bloquer l'interface
"""

import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import streamlit as st
import tempfile
import os


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information sur une tâche"""
    id: str
    name: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self):
        """Convertit en dictionnaire pour affichage"""
        data = asdict(self)
        data['status'] = self.status.value
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class AsyncTaskManager:
    """Gestionnaire de tâches asynchrones"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
    
    def create_task(self, name: str, task_func: Callable, *args, **kwargs) -> str:
        """Crée une nouvelle tâche asynchrone"""
        task_id = str(uuid.uuid4())[:8]
        
        with self._lock:
            task_info = TaskInfo(
                id=task_id,
                name=name,
                status=TaskStatus.PENDING
            )
            self.tasks[task_id] = task_info
        
        # Créer le thread
        thread = threading.Thread(
            target=self._run_task,
            args=(task_id, task_func, args, kwargs),
            daemon=True
        )
        
        self.threads[task_id] = thread
        thread.start()
        
        return task_id
    
    def _run_task(self, task_id: str, task_func: Callable, args: tuple, kwargs: dict):
        """Exécute une tâche dans un thread séparé"""
        try:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.RUNNING
                    self.tasks[task_id].started_at = datetime.now()
                    self.tasks[task_id].message = "Démarrage..."
            
            # Fonction de callback pour mise à jour du progrès
            def update_progress(progress: float, message: str = ""):
                with self._lock:
                    if task_id in self.tasks:
                        self.tasks[task_id].progress = min(max(progress, 0.0), 1.0)
                        if message:
                            self.tasks[task_id].message = message
            
            # Exécuter la tâche avec callback de progrès
            result = task_func(*args, progress_callback=update_progress, **kwargs)
            
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.COMPLETED
                    self.tasks[task_id].completed_at = datetime.now()
                    self.tasks[task_id].progress = 1.0
                    self.tasks[task_id].message = "Terminé avec succès"
                    self.tasks[task_id].result = result
                    
        except Exception as e:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.FAILED
                    self.tasks[task_id].completed_at = datetime.now()
                    self.tasks[task_id].error = str(e)
                    self.tasks[task_id].message = f"Erreur: {str(e)}"
        
        finally:
            # Nettoyer le thread
            if task_id in self.threads:
                del self.threads[task_id]
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Récupère les informations d'une tâche"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """Récupère toutes les tâches"""
        with self._lock:
            return list(self.tasks.values())
    
    def get_active_tasks(self) -> List[TaskInfo]:
        """Récupère les tâches actives (en cours ou en attente)"""
        with self._lock:
            return [
                task for task in self.tasks.values() 
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
            ]
    
    def cancel_task(self, task_id: str) -> bool:
        """Annule une tâche (marque comme annulée, ne peut pas arrêter le thread)"""
        with self._lock:
            if task_id in self.tasks and self.tasks[task_id].status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                self.tasks[task_id].completed_at = datetime.now()
                self.tasks[task_id].message = "Tâche annulée"
                return True
        return False
    
    def cleanup_completed_tasks(self, max_completed: int = 10):
        """Nettoie les tâches terminées anciennes"""
        with self._lock:
            completed_tasks = [
                task for task in self.tasks.values()
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]
            
            if len(completed_tasks) > max_completed:
                # Garder les plus récentes
                completed_tasks.sort(key=lambda t: t.completed_at or datetime.min)
                to_remove = completed_tasks[:-max_completed]
                
                for task in to_remove:
                    if task.id in self.tasks:
                        del self.tasks[task.id]


# Gestionnaire global pour l'application
def get_task_manager() -> AsyncTaskManager:
    """Récupère le gestionnaire de tâches global"""
    if 'async_task_manager' not in st.session_state:
        st.session_state.async_task_manager = AsyncTaskManager()
    return st.session_state.async_task_manager


# Fonctions de tâches asynchrones pour l'ingestion

def async_upload_files(uploaded_files: List, text_only: bool, overwrite: bool, 
                      progress_callback: Callable[[float, str], None] = None) -> Dict[str, Any]:
    """Tâche asynchrone pour l'upload de fichiers"""
    try:
        if progress_callback:
            progress_callback(0.1, "Préparation des fichiers...")
        
        # Utiliser le dossier Data/ au lieu d'un dossier temporaire
        data_dir = os.path.join(os.getcwd(), 'Data')
        os.makedirs(data_dir, exist_ok=True)
        saved_paths = []
        
        # Sauvegarder les fichiers directement dans Data/
        for i, file_data in enumerate(uploaded_files):
            if progress_callback:
                progress_callback(0.1 + (i / len(uploaded_files)) * 0.3, f"Sauvegarde: {file_data['name']}")
            
            data_path = os.path.join(data_dir, file_data['name'])
            with open(data_path, "wb") as f:
                f.write(file_data['content'])
            saved_paths.append(data_path)
        
        if progress_callback:
            progress_callback(0.4, "Vérification de la base de données...")
        
        # Import ici pour éviter les problèmes de circular import
        from assistant_regulation.planning.Database import (
            PDFUploadManager, PDFIngestionManager, check_database_health
        )
        
        health = check_database_health()
        
        if health.get("healthy", False):
            if progress_callback:
                progress_callback(0.5, "Traitement avec base existante...")
            
            manager = PDFUploadManager(data_folder="./Data")
            results = manager.upload_multiple_pdfs(
                saved_paths,
                copy_to_data=True,
                text_only=text_only,
                overwrite_existing=overwrite
            )
            
            if progress_callback:
                progress_callback(0.9, "Finalisation...")
            
            result = {
                "type": "upload",
                "successful_uploads": results['successful_uploads'],
                "total_files": results['total_files'],
                "total_chunks_added": results['total_chunks_added'],
                "errors": results.get('errors', [])
            }
        else:
            if progress_callback:
                progress_callback(0.5, "Création de nouvelle base...")
            
            manager = PDFIngestionManager()
            success_count = 0
            
            for i, file_path in enumerate(saved_paths):
                if progress_callback:
                    progress = 0.5 + (i / len(saved_paths)) * 0.4
                    progress_callback(progress, f"Traitement: {os.path.basename(file_path)}")
                
                if manager.ingest_single_pdf(file_path, text_only=text_only):
                    success_count += 1
            
            result = {
                "type": "ingestion", 
                "successful_uploads": success_count,
                "total_files": len(saved_paths),
                "errors": []
            }
        
        # Les fichiers sont maintenant dans Data/ de façon permanente
        # Pas besoin de nettoyage
        
        if progress_callback:
            progress_callback(1.0, "Upload terminé avec succès!")
        
        return result
        
    except Exception as e:
        if progress_callback:
            progress_callback(0.0, f"Erreur: {str(e)}")
        raise


def async_folder_ingestion(folder_path: str, text_only: bool, parallel: bool, 
                          workers: int, progress_callback: Callable[[float, str], None] = None) -> Dict[str, Any]:
    """Tâche asynchrone pour l'ingestion de dossier"""
    try:
        if progress_callback:
            progress_callback(0.1, f"Vérification du dossier {folder_path}...")
        
        if not os.path.exists(folder_path):
            raise ValueError(f"Le dossier {folder_path} n'existe pas")
        
        # Import ici pour éviter les problèmes de circular import
        from assistant_regulation.planning.Database import PDFIngestionManager
        
        if progress_callback:
            progress_callback(0.2, "Initialisation du gestionnaire...")
        
        manager = PDFIngestionManager()
        
        if progress_callback:
            progress_callback(0.3, "Démarrage de l'ingestion...")
        
        # Note: Le PDFIngestionManager devrait être modifié pour accepter un callback de progrès
        success = manager.ingest_from_folder(
            folder_path,
            text_only=text_only,
            parallel=parallel,
            workers=workers
        )
        
        if progress_callback:
            progress_callback(0.9, "Vérification post-ingestion...")
        
        if success:
            stats = manager.verify_ingestion()
            
            if progress_callback:
                progress_callback(1.0, "Ingestion terminée avec succès!")
            
            return {
                "type": "folder_ingestion",
                "success": True,
                "stats": stats
            }
        else:
            raise ValueError("Erreurs lors de l'ingestion")
            
    except Exception as e:
        if progress_callback:
            progress_callback(0.0, f"Erreur: {str(e)}")
        raise