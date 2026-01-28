# ⚖️ LegalGuard AI - Legal Document Assistant with RAG

A production-ready intelligent chatbot that analyzes legal documents in French using Retrieval-Augmented Generation (RAG) with PII protection.

## 🎯 Overview

LegalGuard AI combines modern NLP techniques to:
- **Load & Index** legal documents (PDF/TXT)
- **Detect sensitive data** (PII) before processing
- **Retrieve relevant information** via semantic search
- **Generate intelligent responses** using Ollama LLM
- **Expose via API** with FastAPI
- **User-friendly interface** with Streamlit

## 🏗️ Architecture

### RAG Pipeline

```
User Query
    ↓
PII Detection & Redaction
    ↓
Vector Store Retrieval
    ↓
LLM Response Generation
    ↓
Final Answer
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector Store** | LangChain + ChromaDB | Document indexing & retrieval |
| **PII Detection** | spaCy NER + Regex | Privacy protection |
| **LLM** | Ollama (GPT-OSS) | Response generation |
| **API** | FastAPI | REST API |
| **UI** | Streamlit | Web interface |
| **Containerization** | Docker | Deployment |

## 📋 Project Structure

```
LegalGuard_AI/
├── docker-compose.yml              # Multi-service orchestration
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── vectorstore_builder/            # Document processing pipeline
│   ├── create_vector_store.ipynb   # Jupyter notebook for vector store creation
│   ├── requirements.txt            # Dependencies for vector store building
│   ├── legal_docs/                 # Sample legal documents
│   │   ├── contrat_travail_1.pdf
│   │   ├── convention-premium-portage-1.pdf
│   │   ├── contrat_freelance.txt
│   │   └── conditions_generales.txt
│   └── _legal_chroma_db_/          # ChromaDB vector store
│
├── chatbot_api/                    # FastAPI backend service
│   ├── api.py                      # FastAPI application & routes
│   ├── chatbot.py                  # Core chatbot logic with PII protection
│   ├── pii_utils.py                # PII detection & redaction utilities
│   ├── rag_utils.py                # RAG pipeline utilities
│   ├── Dockerfile                  # API container configuration
│   ├── requirements.txt            # API dependencies
│   ├── .env                        # Environment variables
│   └── _legal_chroma_db_/          # ChromaDB vector store (copy)
│
└── streamlit_app/                  # Streamlit frontend service
    ├── app.py                      # Web interface
    ├── Dockerfile                  # UI container configuration
    └── requirements.txt            # UI dependencies
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+ (for local development)
- Ollama account (for cloud LLM)

### Installation & Setup

1. **Clone the repository**
```bash
git clone <repo>
cd LegalGuard_AI
```

2. **Set up environment variables**
```bash
cd chatbot_api
cp .env.example .env
# Edit .env and add your Ollama API key
```

3. **Build and run with Docker Compose**
```bash
docker-compose up --build
```

This will start:
- **Ollama service** (port 11434) - LLM inference
- **Chatbot API** (port 8000) - FastAPI backend
- **Streamlit App** (port 8501) - Web interface

## 📚 Usage

### Via Web Interface (Recommended)
1. Open http://localhost:8501
2. Toggle PII protection on/off
3. Ask questions about legal documents
4. View responses with document references

### Via API
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelles sont les conditions du contrat?",
    "activate_pii_detector": true
  }'
```

### Python Client
```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "What are the contract conditions?",
        "activate_pii_detector": True
    }
)
print(response.json())
```

## 🔍 Features

### Vector Store Creation
- **Document Loading**: Supports PDF and TXT files
- **Text Chunking**: 1000 characters with 200 overlap
- **Embeddings**: Ollama Gemma embeddings
- **Persistent Storage**: ChromaDB vector database

### PII Protection
- **NER Detection**: spaCy models for French/English person names
- **Regex Patterns**: Email, phone, SSN, passport detection
- **Redaction Strategies**: Full redaction or masking
- **Language Detection**: Automatic French/English switching

### RAG Pipeline
- **Semantic Search**: Vector similarity retrieval
- **Context Integration**: Retrieved docs fed to LLM
- **Structured Responses**: Markdown-formatted answers
- **Document References**: Source tracking and metadata

### API Endpoints
- `GET /` - Health check
- `GET /health` - Health status
- `POST /query` - Document query with PII protection

## 🧪 Development Setup

### Local Development

1. **Create vector store** (one-time setup)
```bash
cd vectorstore_builder
pip install -r requirements.txt
jupyter notebook create_vector_store.ipynb
# Run the notebook to build the vector store
```

2. **Run API locally**
```bash
cd chatbot_api
pip install -r requirements.txt
python api.py
```

3. **Run UI locally**
```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

### Testing

```bash
# Run API tests
cd chatbot_api
pytest

# Test PII detection
python -c "from pii_utils import detect_pii; print(detect_pii('John Doe email@example.com'))"
```

## ⚙️ Configuration

### Environment Variables (.env)
```properties
OLLAMA_API_KEY=your_ollama_api_key
OLLAMA_HOST=http://ollama:11434
```

### Vector Store Config
- **Persist Directory**: `_legal_chroma_db_`
- **Embedding Model**: `embeddinggemma`
- **Chunk Size**: 1000 characters
- **Overlap**: 200 characters

## 🐛 Troubleshooting

### "Vector store not found"
- Ensure you've run the vectorstore_builder notebook
- Check that `_legal_chroma_db_` directory exists

### "Ollama connection failed"
- Verify Ollama service is running
- Check API key in `.env`
- Ensure network connectivity to Ollama cloud

### "spaCy model not found"
```bash
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
```

### Container Issues
```bash
# Rebuild containers
docker-compose down
docker-compose up --build

# View logs
docker-compose logs chatbot_api
```

## 📈 Performance

| Component | Time | Notes |
|-----------|------|-------|
| Document Loading | ~500ms | Per document |
| Text Chunking | ~200ms | Per 10K chars |
| Vector Embedding | ~1-2s | Per batch |
| Similarity Search | ~50ms | Top-k retrieval |
| LLM Generation | ~2-3s | API call |
| **Total Query** | **~4-5s** | End-to-end |

## 🔒 Security & Privacy

- **PII Detection**: Automatic redaction of personal information
- **Input Validation**: Pydantic models for API requests
- **CORS Protection**: Configured for allowed origins
- **Environment Secrets**: API keys stored securely
- **Log Sanitization**: PII removed from logs

## 📦 Dependencies

### Core Libraries
- `langchain` - Document processing & RAG
- `chromadb` - Vector database
- `ollama` - LLM integration
- `spacy` - NLP & PII detection
- `fastapi` - REST API framework
- `streamlit` - Web interface

### Development
- `jupyter` - Notebook interface
- `pytest` - Testing framework
- `rich` - Terminal formatting

## 🚢 Deployment

### Docker Compose (Recommended)
```bash
docker-compose up -d --build
```

### Production Checklist
- [ ] Set production Ollama endpoint
- [ ] Configure proper CORS origins
- [ ] Add API rate limiting
- [ ] Enable SSL/TLS
- [ ] Set up monitoring
- [ ] Configure logging aggregation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and test locally
4. Commit changes: `git commit -m 'Add new feature'`
5. Push and create Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 📞 Support

For issues:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review Docker logs: `docker-compose logs`
3. Open GitHub Issue with error details

## 🎯 Future Enhancements

- [ ] Multi-language document support
- [ ] Advanced PII detection models
- [ ] Document upload interface
- [ ] User authentication
- [ ] Query history and analytics
- [ ] Batch document processing
- [ ] Export capabilities

---

**Built with ❤️ by Kawtar RIFI for legal technology**

*Last updated: 2025,*
```

---
