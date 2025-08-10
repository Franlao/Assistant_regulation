# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Recent Updates

**✅ ModularOrchestrator Integration Complete**
The application now uses the new `ModularOrchestrator` instead of the deprecated `SimpleOrchestrator` (orchestrator_2). This provides:
- Better service separation and modularity  
- Enhanced routing capabilities with intelligent query analysis
- Improved conversation memory management
- Full backward compatibility with existing UI components

## Project Overview

This is an AI-powered automotive regulatory assistant built with Python and Streamlit. The system uses a RAG (Retrieval-Augmented Generation) architecture to answer questions about UN/ECE automotive regulations by searching through text, images, and tables from regulatory documents.

## Key Architecture

The codebase follows a modular RAG architecture with clear separation of concerns:

### Core Components
- **ModularOrchestrator** (`assistant_regulation/planning/Orchestrator/modular_orchestrator.py`): Main orchestration layer that coordinates all services
- **Retrievers** (`assistant_regulation/processing/Modul_emb/`): Multimodal retrieval system with separate retrievers for text, images, and tables
- **Services** (`assistant_regulation/planning/services/`): Modular services for retrieval, generation, memory, validation, context building, and routing
- **Processing Pipeline** (`assistant_regulation/processing/`): Document ingestion, chunking with Late Chunker, and embedding generation

### Service Architecture
The system uses a service-oriented architecture where each service has a specific responsibility:
- **RetrievalService**: Handles multimodal search across text/image/table collections
- **GenerationService**: LLM response generation with multiple provider support (Ollama/Mistral)
- **MemoryService**: Conversation context and session management
- **ValidationService**: LLM-based relevance verification of retrieved chunks
- **ContextBuilderService**: Constructs contextual prompts from retrieved information
- **RerankerService**: Optional reranking using Jina API
- **RoutingServices**: Intelligent query routing and analysis

### Document Processing
The system uses **chonkie** (Late Chunker) for text chunking, which provides:
- 15x faster processing than previous Docling solution
- Global context preservation across chunks
- Optimal chunking for regulatory documents
- Better semantic coherence

### Data Flow
1. PDF documents are processed into chunks (text/images/tables) using Late Chunker and stored in ChromaDB
2. User queries are analyzed and routed to appropriate retrievers
3. Retrieved context is validated, reranked, and used to build prompts
4. LLM generates responses with conversation memory integration

## Common Development Commands

### Application Startup
```bash
# Start the Streamlit application
streamlit run app.py

# The application will be available at http://localhost:8501
```

### Document Processing
```bash
# Initialize vector databases from PDF documents
python -c "from assistant_regulation.processing.process_regulations import process_regulation_document; process_regulation_document('./Data')"

# Regenerate chunks from scratch (text only for faster processing)
python -m assistant_regulation.processing.process_regulations --regenerate --text-only

# Regenerate all chunks (including images and tables)
python -m assistant_regulation.processing.process_regulations --regenerate

# Parallel chunk generation (faster, recommended)
python -m assistant_regulation.processing.process_regulations --regenerate-parallel --workers 4

# Clean database collections only
python -m assistant_regulation.processing.process_regulations --clean-only

# Test environment before processing
python -m assistant_regulation.processing.process_regulations --test
```

### Configuration Testing
```bash
# Test configuration system
python config/config.py
```

### Development Notebooks
```bash
# Launch Jupyter for development notebooks
jupyter notebook notebooks/
```

## Configuration System

The application uses a centralized configuration system:
- **Main config**: `config/config.json` - Auto-generated configuration file
- **Config classes**: `config/config.py` - Dataclass-based configuration management
- **Environment variables**: Support for `.env` file and environment overrides

Key configuration areas:
- **LLM providers**: Ollama (local) and Mistral AI (cloud) support
- **RAG settings**: Confidence thresholds, multimodal options, caching
- **Memory management**: Conversation window size and retention
- **UI preferences**: Language, themes, display limits

## Dependencies and Requirements

The project uses modern Python libraries:
- **Core**: `streamlit`, `langchain`, `chromadb`, `sentence-transformers`
- **Document processing**: `PyMuPDF`, `chonkie`, `pdfplumber` 
- **LLM providers**: `ollama`, `mistralai`
- **Performance**: `joblib` caching, `psutil` monitoring
- **Export**: `reportlab`, `weasyprint`, `python-docx`

### Installation Note
The chunking system requires chonkie with streamlit support:
```bash
pip install 'chonkie[st]'
```

## Database and Storage

- **Vector stores**: ChromaDB collections for text/image/table chunks
- **Caching**: Joblib cache in `./joblib_cache/` for retrieval optimization  
- **Memory**: Conversation memory stored in `.conversation_memory/`
- **Logs**: Application logs in `logs/` directory
- **Data**: PDF documents in `Data/` directory, processed chunks cached as `.pkl` files

## Development Patterns

### Adding New Services
Services follow a consistent pattern with dependency injection through the ModularOrchestrator. New services should:
1. Implement their core functionality as standalone classes
2. Accept LLM provider/model configuration in constructor
3. Be injected into ModularOrchestrator and passed to QueryProcessor

### Text Chunking with Late Chunker
The system uses `LateChunkerRegulation` class which wraps chonkie's Late Chunker:
- Preserves global context across the entire document
- Optimal for regulatory documents with cross-references
- Provides enhanced metadata including content analysis and quality scores
- Use `hybrid_chunk_document()` function for compatibility with existing code

### Memory Management
The system uses conversation memory with configurable window sizes. Memory is automatically summarized when conversations exceed the configured length.

### Error Handling
All services include comprehensive error handling and logging. The processing pipeline has retry logic and graceful degradation for failed operations.

### Multimodal RAG
The system supports three retrieval modes that can be enabled/disabled:
- Text chunks from document content (using Late Chunker)
- Image chunks with AI-generated descriptions
- Table chunks with structured data extraction

## Important File Locations

- **Main entry**: `app.py` - Streamlit application entry point
- **Orchestrator**: `assistant_regulation/planning/Orchestrator/modular_orchestrator.py`
- **Services**: `assistant_regulation/planning/services/`
- **Processing**: `assistant_regulation/processing/process_regulations.py`
- **Text Chunking**: `assistant_regulation/processing/Modul_Process/chunking_text.py` (Late Chunker implementation)
- **Configuration**: `config/config.py` and `config/config.json`
- **UI Components**: `assistant_regulation/app/`
- **Translations**: `translations/` for multilingual support