"""
Chroma vector database integration for semantic search
Manages embeddings, similarity search, and retrieval-augmented generation
"""

import os
import logging
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma vector database wrapper for semantic search"""
    
    def __init__(self):
        """Initialize Chroma client and collections"""
        self.data_dir = os.path.join(settings.data_dir, "chroma")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize Chroma with persistent storage
        chroma_settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.data_dir,
            anonymized_telemetry=False,
        )
        
        self.client = chromadb.Client(chroma_settings)
        
        # Create or get collections
        self._init_collections()
    
    def _init_collections(self):
        """Initialize collection structure"""
        try:
            self.code_collection = self.client.get_or_create_collection(
                name="code_snippets",
                metadata={"description": "Indexed code snippets for RAG"}
            )
            
            self.documentation_collection = self.client.get_or_create_collection(
                name="documentation",
                metadata={"description": "Project documentation and API docs"}
            )
            
            self.conversation_collection = self.client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Conversation history for context"}
            )
            
            self.best_practices_collection = self.client.get_or_create_collection(
                name="best_practices",
                metadata={"description": "Code patterns and best practices"}
            )
            
            logger.info("Chroma collections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma collections: {e}")
            raise
    
    async def add_code_snippet(
        self,
        code: str,
        build_id: str,
        file_path: str,
        language: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a code snippet to the vector store
        
        Args:
            code: Source code content
            build_id: Associated build ID
            file_path: Original file path
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            Document ID in Chroma
        """
        try:
            doc_id = f"{build_id}_{file_path}"
            
            meta = {
                "build_id": build_id,
                "file_path": file_path,
                "language": language,
                "type": "code"
            }
            if metadata:
                meta.update(metadata)
            
            self.code_collection.add(
                ids=[doc_id],
                documents=[code],
                metadatas=[meta]
            )
            
            logger.debug(f"Added code snippet: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to add code snippet: {e}")
            raise
    
    async def add_documentation(
        self,
        content: str,
        build_id: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add documentation to vector store"""
        try:
            doc_id = f"{build_id}_doc_{doc_type}"
            
            meta = {
                "build_id": build_id,
                "doc_type": doc_type,
                "type": "documentation"
            }
            if metadata:
                meta.update(metadata)
            
            self.documentation_collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta]
            )
            
            logger.debug(f"Added documentation: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to add documentation: {e}")
            raise
    
    async def search_similar_code(
        self,
        query: str,
        n_results: int = 5,
        build_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets
        
        Args:
            query: Query code or description
            n_results: Number of results to return
            build_id: Filter by specific build
            
        Returns:
            List of similar code snippets with metadata
        """
        try:
            where_filter = None
            if build_id:
                where_filter = {"build_id": {"$eq": build_id}}
            
            results = self.code_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for idx, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "code": results["documents"][0][idx],
                        "distance": results["distances"][0][idx],
                        "metadata": results["metadatas"][0][idx]
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Code search failed: {e}")
            raise
    
    async def search_documentation(
        self,
        query: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Search documentation for relevant information"""
        try:
            results = self.documentation_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for idx, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "content": results["documents"][0][idx],
                        "distance": results["distances"][0][idx],
                        "metadata": results["metadatas"][0][idx]
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Documentation search failed: {e}")
            raise
    
    async def get_build_context(
        self,
        build_id: str,
        query: Optional[str] = None,
        n_snippets: int = 5
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for a build
        
        Returns code snippets, docs, and previous analysis
        """
        try:
            context = {
                "build_id": build_id,
                "code_snippets": [],
                "documentation": [],
                "related_builds": []
            }
            
            # Get relevant code snippets
            if query:
                context["code_snippets"] = await self.search_similar_code(
                    query, n_results=n_snippets, build_id=build_id
                )
                context["documentation"] = await self.search_documentation(
                    query, n_results=3
                )
            else:
                # Get all snippets for this build
                results = self.code_collection.get(
                    where={"build_id": {"$eq": build_id}}
                )
                if results["ids"]:
                    context["code_snippets"] = [
                        {
                            "id": results["ids"][idx],
                            "code": results["documents"][idx],
                            "metadata": results["metadatas"][idx]
                        }
                        for idx in range(len(results["ids"]))
                    ]
            
            return context
        except Exception as e:
            logger.error(f"Failed to get build context: {e}")
            raise
    
    async def delete_build_vectors(self, build_id: str):
        """Clean up vectors when build is deleted"""
        try:
            # Delete from code collection
            self.code_collection.delete(
                where={"build_id": {"$eq": build_id}}
            )
            
            # Delete from documentation collection
            self.documentation_collection.delete(
                where={"build_id": {"$eq": build_id}}
            )
            
            logger.info(f"Deleted vectors for build: {build_id}")
        except Exception as e:
            logger.error(f"Failed to delete build vectors: {e}")
            raise
    
    async def persist(self):
        """Persist Chroma data to disk"""
        try:
            self.client.persist()
            logger.info("Chroma data persisted")
        except Exception as e:
            logger.warning(f"Chroma persist failed: {e}")


# Global vector store instance
_vector_store: Optional[VectorStore] = None


async def get_vector_store() -> VectorStore:
    """Get or initialize global vector store"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


async def init_vector_store():
    """Initialize vector store on startup"""
    try:
        await get_vector_store()
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error(f"Vector store initialization failed: {e}")
        raise


async def close_vector_store():
    """Close vector store on shutdown"""
    global _vector_store
    if _vector_store:
        try:
            await _vector_store.persist()
            _vector_store = None
            logger.info("Vector store closed")
        except Exception as e:
            logger.warning(f"Vector store close failed: {e}")
