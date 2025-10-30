"""
Page À propos - Présentation du projet Assistant Réglementaire
"""

import streamlit as st
from translations import t


def main():
    """Page principale À propos"""

    # Titre principal
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #343a40; font-weight: 400; font-size: 2rem; margin: 0;">{t('about_page_title')}</h1>
        <p style="color: #6c757d; font-size: 1rem; margin: 0.5rem 0 0 0;">{t('about_page_subtitle')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Section 1 : Description du projet
    st.markdown(f"### {t('about_project_section_title')}")

    st.markdown(f"""
    {t('about_project_intro')}

    - {t('about_project_search')}
    - {t('about_project_analyze')}
    - {t('about_project_answers')}
    - {t('about_project_summaries')}

    {t('about_project_rag_explanation')}
    """)

    st.divider()

    # Section 2 : Vidéo explicative
    st.markdown(f"### {t('about_video_section_title')}")

    st.markdown(f"""
    {t('about_video_description')}
    """)

    # Intégration YouTube
    video_id = "AM50pVSx4Mg"

    st.markdown(f"""
    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 2rem 0;">
        <iframe
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
            src="https://www.youtube.com/embed/{video_id}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
        </iframe>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Section 3 : Architecture technique
    st.markdown(f"### {t('about_architecture_section_title')}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **{t('about_main_components_title')}**

        - {t('about_component_interface')}
        - {t('about_component_database')}
        - {t('about_component_llm')}
        - {t('about_component_embeddings')}
        - {t('about_component_processing')}
        """)

    with col2:
        st.markdown(f"""
        **{t('about_rag_architecture_title')}**

        1. {t('about_rag_ingestion')}
        2. {t('about_rag_indexation')}
        3. {t('about_rag_search')}
        4. {t('about_rag_generation')}
        5. {t('about_rag_validation')}
        """)

    st.markdown(f"""
    {t('about_architecture_modularity')}
    - {t('about_architecture_retrieval')}
    - {t('about_architecture_generation')}
    - {t('about_architecture_memory')}
    - {t('about_architecture_routing')}
    """)

    st.divider()

    # Section 4 : Guide d'utilisation
    st.markdown(f"### {t('about_usage_guide_title')}")

    with st.expander(t('about_how_to_ask_question_title'), expanded=True):
        st.markdown(f"""
        {t('about_how_to_ask_steps_title')}

        1. {t('about_how_to_ask_step1')}
        2. {t('about_how_to_ask_step2')}
        3. {t('about_how_to_ask_step3')}
        4. {t('about_how_to_ask_step4')}

        {t('about_question_examples_title')}
        - {t('about_question_example1')}
        - {t('about_question_example2')}
        - {t('about_question_example3')}
        """)

    with st.expander(t('about_configuration_section_title')):
        st.markdown(f"""
        {t('about_configuration_params_title')}

        - {t('about_configuration_llm_provider')}
        - {t('about_configuration_model')}
        - {t('about_configuration_rag_options')}
        - {t('about_configuration_memory')}
        - {t('about_configuration_thresholds')}
        """)

    with st.expander(t('about_summary_generation_title')):
        st.markdown(f"""
        {t('about_summary_steps_title')}

        1. {t('about_summary_step1')}
        2. {t('about_summary_step2')}
        3. {t('about_summary_step3')}
        4. {t('about_summary_step4')}
        5. {t('about_summary_step5')}
        6. {t('about_summary_step6')}
        """)

    with st.expander(t('about_database_management_title')):
        st.markdown(f"""
        {t('about_database_features_title')}

        - {t('about_database_ingestion')}
        - {t('about_database_search')}
        - {t('about_database_cleanup')}
        - {t('about_database_statistics')}
        - {t('about_database_users')}
        """)

    st.divider()

    # Section 5 : Informations complémentaires
    st.markdown(f"### {t('about_additional_info_title')}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(t('about_version_label'), "1.0", help=t('about_version_help'))

    with col2:
        st.metric(t('about_architecture_label'), "RAG", help=t('about_architecture_help'))

    with col3:
        st.metric(t('about_modalities_label'), "3", help=t('about_modalities_help'))

    st.markdown("<br>", unsafe_allow_html=True)

    # Footer
    st.info(f"""
    {t('about_need_help_title')}

    {t('about_need_help_message')}
    """)


if __name__ == "__main__":
    main()
