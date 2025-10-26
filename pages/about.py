"""
Page À propos - Présentation du projet Assistant Réglementaire
"""

import streamlit as st
import os
from pathlib import Path


def main():
    """Page principale À propos"""

    # Titre principal
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #343a40; font-weight: 400; font-size: 2rem; margin: 0;">À propos de l'Assistant Réglementaire</h1>
        <p style="color: #6c757d; font-size: 1rem; margin: 0.5rem 0 0 0;">Découvrez le projet et son fonctionnement</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Section 1 : Description du projet
    st.markdown("### Présentation du projet")

    st.markdown("""
    L'**Assistant Réglementaire Automobile** est un système intelligent basé sur l'IA qui permet de :

    - **Rechercher** facilement dans les réglementations UN/ECE automobiles
    - **Analyser** le contenu des documents réglementaires (texte, images, tableaux)
    - **Obtenir** des réponses précises et contextualisées à vos questions
    - **Générer** des résumés automatiques de réglementations

    Le système utilise une architecture RAG (Retrieval-Augmented Generation) pour fournir des réponses
    basées sur les documents officiels avec citations et références.
    """)

    st.divider()

    # Section 2 : Vidéo explicative
    st.markdown("### Vidéo de présentation")

    video_path = Path("assets/videos/presentation.mp4")

    if video_path.exists():
        # Lecteur vidéo HTML5
        video_file = open(video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)
    else:
        # Placeholder si la vidéo n'est pas encore disponible
        st.info("""
        **Vidéo de présentation à venir**

        Pour ajouter votre vidéo :
        1. Placez votre fichier MP4 dans le dossier `assets/videos/`
        2. Renommez-le en `presentation.mp4`
        3. Rechargez la page

        Chemin attendu : `assets/videos/presentation.mp4`
        """)

        # Afficher un placeholder visuel
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            padding: 4rem 2rem;
            text-align: center;
            color: white;
            margin: 2rem 0;
        ">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🎬</div>
            <div style="font-size: 1.2rem; font-weight: 500;">Vidéo explicative</div>
            <div style="font-size: 0.9rem; opacity: 0.9; margin-top: 0.5rem;">
                Découvrez comment utiliser l'Assistant Réglementaire
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Section 3 : Architecture technique
    st.markdown("### Architecture technique")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Composants principaux**

        - **Interface** : Streamlit (Python)
        - **Base de données** : ChromaDB (vectorielle)
        - **LLM** : Ollama (local) ou Mistral AI (cloud)
        - **Embeddings** : Sentence Transformers
        - **Traitement** : PyMuPDF, Chonkie
        """)

    with col2:
        st.markdown("""
        **Architecture RAG**

        1. **Ingestion** : Extraction et chunking des PDF
        2. **Indexation** : Génération d'embeddings
        3. **Recherche** : Récupération multimodale
        4. **Génération** : Réponses contextualisées par LLM
        5. **Validation** : Vérification de pertinence
        """)

    st.markdown("""
    Le système est modulaire avec séparation claire entre :
    - Services de récupération (texte, images, tableaux)
    - Services de génération et validation
    - Services de mémoire conversationnelle
    - Services de routage intelligent
    """)

    st.divider()

    # Section 4 : Guide d'utilisation
    st.markdown("### Guide d'utilisation")

    with st.expander("📖 Comment poser une question", expanded=True):
        st.markdown("""
        **Étapes pour obtenir une réponse :**

        1. Accédez à la page **Chat** depuis le menu
        2. Tapez votre question sur une réglementation UN/ECE
        3. Le système recherche dans les documents pertinents
        4. Vous recevez une réponse avec citations et sources

        **Exemples de questions :**
        - "Quelles sont les exigences du R46 sur les rétroviseurs ?"
        - "Que dit le règlement R100 sur les batteries des véhicules électriques ?"
        - "Quels sont les tests requis pour la protection des passagers ?"
        """)

    with st.expander("⚙️ Configuration du système"):
        st.markdown("""
        **Paramètres disponibles** (page Configuration) :

        - **LLM Provider** : Choisir entre Ollama (local) ou Mistral AI
        - **Modèle** : Sélectionner le modèle de langue
        - **Options RAG** : Activer/désactiver images et tableaux
        - **Mémoire** : Configurer la taille de la fenêtre conversationnelle
        - **Seuils** : Ajuster les seuils de confiance
        """)

    with st.expander("📊 Génération de résumés"):
        st.markdown("""
        **Pour générer un résumé de réglementation :**

        1. Accédez à la page **Summary**
        2. Sélectionnez une réglementation
        3. Choisissez les sections à inclure
        4. Configurez les options de génération
        5. Cliquez sur "Générer le Résumé"
        6. Exportez au format souhaité (PDF, Word, Markdown)
        """)

    with st.expander("🗃️ Gestion de la base de données (Admin)"):
        st.markdown("""
        **Fonctionnalités administrateur :**

        - **Ingestion** : Ajouter de nouveaux documents PDF
        - **Recherche** : Explorer le contenu de la base
        - **Nettoyage** : Supprimer des réglementations
        - **Statistiques** : Visualiser l'état de la base
        - **Utilisateurs** : Gérer les comptes et les rôles
        """)

    st.divider()

    # Section 5 : Informations complémentaires
    st.markdown("### Informations complémentaires")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Version", "1.0", help="Version actuelle du système")

    with col2:
        st.metric("Architecture", "RAG", help="Retrieval-Augmented Generation")

    with col3:
        st.metric("Modalités", "3", help="Texte, Images, Tableaux")

    st.markdown("<br>", unsafe_allow_html=True)

    # Footer
    st.info("""
    **Besoin d'aide ?**

    Pour toute question ou assistance, contactez l'administrateur du système.
    """)


if __name__ == "__main__":
    main()
