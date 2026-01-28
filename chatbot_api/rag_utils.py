from langchain_ollama import OllamaEmbeddings
# from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
import os
import dotenv
dotenv.load_dotenv()

ollama_llm = ChatOllama(
    model="gpt-oss:120b-cloud",
    base_url="https://ollama.com",  # Point to the cloud endpoint
    headers={"Authorization": f"Bearer {os.environ.get('OLLAMA_API_KEY')}"},
    timeout=30,
)

def load_existing_vectorstore(persist_directory="chatbot_api\chatbot.py_legal_chroma_db_"):
    """Load an existing vectorstore"""
    embeddings = OllamaEmbeddings(
        model="embeddinggemma",
    )
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vectorstore














