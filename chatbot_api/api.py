from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

# Import your existing chatbot functionality
from chatbot import answer_query, create_agent_with_pii_option, redact_pii, detect_pii

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Changed from INFO to WARNING to reduce logs
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Reduce httpx logging (the HTTP request logs)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize FastAPI app
app = FastAPI(
    title="LegalGuard AI API",
    description="AI-powered legal document analysis with PII protection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str = Field(..., description="The question to ask about legal documents")
    activate_pii_detector: bool = Field(
        default=True, 
        description="Enable PII protection and redaction"
    )

class DocumentInfo(BaseModel):
    document_id: str
    source: str
    document_type: str
    pages: str
    pii_status: str

class PIIEntity(BaseModel):
    label: str
    text: str
    start: int
    end: int

class QueryResponse(BaseModel):
    answer: str
    query_time: str
    pii_detected: List[PIIEntity]
    documents_used: List[DocumentInfo]
    processing_time: float
    pii_protection_enabled: bool

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str

def process_query_for_api(
    query: str, 
    activate_pii_detector: bool = True
) -> Dict[str, Any]:
    """
    Process a query and return structured data for API response.
    This captures the output instead of printing to console.
    """
    start_time = datetime.now()
    
    # Apply PII protection
    pii_entities = []
    if activate_pii_detector:
        safe_query, pii_entities = redact_pii(query, strategy="redact")
    else:
        safe_query = query
        # Still detect for reporting
        pii_entities = detect_pii(query)
    
    # Create agent and get response
    try:
        agent = create_agent_with_pii_option(activate_pii_detector)
        
        # Collect all events to capture the final answer
        final_answer = None
        documents_used = []
        
        for event in agent.stream(
            {"messages": [{"role": "user", "content": safe_query}]},
            stream_mode="values",
        ):
            message = event["messages"][-1]
            
            if hasattr(message, 'type'):
                if message.type == 'ai' and not (hasattr(message, 'tool_calls') and message.tool_calls):
                    # This is the final answer
                    final_answer = message.content
                
                elif message.type == 'tool' and message.name == 'retrieve_context':
                    # Extract document information from tool results
                    try:
                        _, docs = message.content
                        for doc in docs:
                            source = doc['metadata'].get('source', 'Unknown')
                            doc_type = "PDF" if source.endswith('.pdf') else "Text"
                            pages = f"{doc['metadata'].get('page', 0) + 1}/{doc['metadata'].get('total_pages', 1)}"
                            
                            documents_used.append({
                                "document_id": str(len(documents_used) + 1),
                                "source": source.split('/')[-1] if '/' in source else source,
                                "document_type": doc_type,
                                "pages": pages,
                                "pii_status": "protected" if activate_pii_detector else "visible"
                            })
                    except (ValueError, TypeError):
                        # Fallback if content structure is different
                        pass
        
        if not final_answer:
            final_answer = "I couldn't generate a response based on the available documents."
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "answer": final_answer,
            "query_time": start_time.isoformat(),
            "pii_detected": [
                {
                    "label": entity['label'],
                    "text": entity['text'],
                    "start": entity['start'],
                    "end": entity['end']
                }
                for entity in pii_entities
            ],
            "documents_used": documents_used,
            "processing_time": round(processing_time, 2),
            "pii_protection_enabled": activate_pii_detector
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise

# API Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

@app.post("/query", response_model=QueryResponse)
async def query_legal_documents(request: QueryRequest):
    """
    Query the LegalGuard AI system about legal documents.
    
    - **query**: Your question about the legal documents
    - **activate_pii_detector**: Enable/disable PII protection (default: True)
    """
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        
        result = process_query_for_api(
            query=request.query,
            activate_pii_detector=request.activate_pii_detector
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info"
    )
