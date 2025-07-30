# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered regulatory assistant specialized in automotive regulations (UN/ECE standards). The application uses a RAG (Retrieval-Augmented Generation) architecture to answer questions about regulatory documents by combining retrieval from multiple data sources (text, images, tables) with language model generation.

## Architecture

The codebase follows a modular pattern-based architecture:

### Core Components
- **Processing Pattern** (`assistant_regulation/processing/`): Document ingestion, chunking, and embedding
  - `Modul_Process/`: Text, image, and table chunking with page tracking
  - `Modul_emb/`: Specialized retrievers for different content types (BaseRetriever, ImageRetriever, TableRetriever, TextRetriever)
  - `Modul_verif/`: LLM-based verification agent for result relevance
  - `Modul_Summary/`: Regulatory document summarization with HTML/PDF export

- **Planning Pattern** (`assistant_regulation/planning/`): Orchestration and workflow management
  - `sync/`: Synchronous orchestrator with conversation memory and caching
  - `services/`: Modular services (retrieval, generation, validation, routing, etc.)
  - `langgraph/`: Advanced workflow orchestration (experimental)

- **App Layer** (`assistant_regulation/app/`): Streamlit UI components
  - UI styling, chat generation, data extraction, display management

### Key Features
- **Multimodal RAG**: Retrieves from text chunks, images, and tables
- **Conversation Memory**: Tracks context across chat sessions with configurable window size
- **Intelligent Routing**: Routes queries to appropriate RAG components based on content analysis
- **Verification Layer**: Optional LLM verification of retrieval relevance before generation
- **Reranking**: Uses Jina API for result reranking (configurable)

## Development Commands

### Running the Application
```bash
# Start Streamlit app
streamlit run app.py

# Alternative: Start with environment variables
python -m streamlit run app.py
```

### Database Initialization
```bash
# Initialize vector databases with PDF documents
python -c "from assistant_regulation.processing.process_regulations import process_pdf_directory; process_pdf_directory('./Data')"
```

### Testing
```bash
# Run tests (if pytest is configured)
pytest

# Manual testing of configuration
python config/config.py
```

### Requirements Management
```bash
# Install dependencies
pip install -r requirements.txt

# For development with additional tools
pip install pytest pytest-asyncio httpx
```

## Configuration

The application uses a centralized configuration system in `config/config.py`:

- **LLM Configuration**: Supports Ollama and Mistral AI providers
- **RAG Configuration**: Confidence thresholds, verification settings, force keywords
- **Memory Configuration**: Conversation window size, session timeout
- **UI Configuration**: Language support (FR/EN), themes, display limits
- **Database Configuration**: Vector store paths and search parameters

Configuration can be:
1. Modified in `config/config.json` (auto-generated on first run)
2. Overridden via environment variables
3. Accessed programmatically via `get_config()` singleton

## Key Environment Variables

```bash
# API Keys
JINA_API_KEY=your_jina_api_key  # For reranking service
MISTRAL_API_KEY=your_mistral_key  # If using Mistral AI

# Optional overrides
STREAMLIT_SERVER_TIMEOUT=300
```

## Data Structure

```
Data/                           # PDF regulatory documents
data/vectorstores/             # Vector databases (auto-created)
  ├── text_chunks/
  ├── image_chunks/
  └── table_chunks/
description_cache/             # Cached image descriptions
.conversation_memory/          # Chat session storage
joblib_cache/                  # Processing cache
```

## Key Classes and Entry Points

- **SimpleOrchestrator** (`assistant_regulation.planning.sync.orchestrator_2`): Main orchestration engine
- **AppConfig** (`config.config`): Centralized configuration management
- **BaseRetriever, ImageRetriever, TableRetriever, TextRetriever**: Content retrieval engines
- **ConversationMemory**: Session management and context tracking

## Development Notes

- The codebase uses Python dataclasses extensively for configuration
- Streamlit components are modularized for reusability
- Cache management uses joblib for performance optimization
- Image processing leverages PyMuPDF and Pillow
- LLM integration supports both local (Ollama) and cloud (Mistral) providers
- The system includes comprehensive error handling and logging

## Document Processing Pipeline

1. **Ingestion**: PDFs are processed using PyMuPDF and pdfplumber
2. **Chunking**: Documents split into text, image, and table chunks with page tracking
3. **Embedding**: Each chunk type uses specialized embedding strategies
4. **Storage**: Vector stores created using ChromaDB
5. **Retrieval**: Multi-modal search across all content types
6. **Verification**: Optional LLM verification of relevance
7. **Generation**: Context-aware response generation with source citations