import os
from pathlib import Path
from app.core.logger import get_logger
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = get_logger(__name__)

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "operations_runbooks"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_embeddings():
    logger.info("Loading embedding model")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

def get_vector_store():
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    return vector_store

def retrieve_context(query: str, k: int = 3) -> str:
    try:
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(query, k=k)
        if not docs:
            return ""
        context = "\n\n".join([
            f"[Runbook: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}"
            for doc in docs
        ])
        logger.info(
            f"RAG retrieved {len(docs)} relevant documents for query: "
            f"{query[:50]}"
        )
        return context
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return ""