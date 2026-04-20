"""
Knowledge Base Tool — RAG with ChromaDB for persistent local learning.
Uses sentence-transformers for local embedding generation.

Supports:
- Storing arbitrary text (from web scraping, docs, etc.)
- Indexing entire project directories (source code files)
- Semantic search across all stored knowledge
- Topic-based filtering
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool
from config.settings import CHROMA_DB_PATH, EMBEDDING_MODEL

# Lazy-loaded globals
_chroma_client = None
_embedding_fn = None

# File extensions to index when scanning projects
CODE_EXTENSIONS = {
    # Web frontend
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".html", ".css", ".scss", ".sass", ".less",
    # Backend
    ".py", ".go", ".rs", ".java", ".rb", ".php",
    # Config & data
    ".json", ".yaml", ".yml", ".toml", ".env",
    ".xml", ".graphql", ".gql",
    # Documentation
    ".md", ".mdx", ".txt", ".rst",
    # DevOps
    ".dockerfile", ".dockerignore",
    ".gitignore", ".editorconfig",
    # Misc
    ".sql", ".prisma", ".proto",
}

# Directories to skip when indexing
SKIP_DIRS = {
    "node_modules", ".next", ".nuxt", ".output", "dist", "build", "out",
    "__pycache__", ".git", ".svn", ".hg",
    "venv", ".venv", "env", ".env",
    ".idea", ".vscode",
    "vendor", "target", "bin", "obj",
    "coverage", ".nyc_output", ".pytest_cache",
    "chroma_db", ".chroma",
}

# Max file size to index (50KB)
MAX_INDEX_FILE_SIZE = 50_000


def _get_embedding_function():
    """Lazy-load the embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _embedding_fn


def _get_chroma_client():
    """Lazy-load the ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _chroma_client


def _get_collection(name: str = "knowledge"):
    """Get or create a ChromaDB collection."""
    client = _get_chroma_client()
    embed_fn = _get_embedding_function()
    return client.get_or_create_collection(
        name=name,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def _chunk_code(text: str, file_path: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    """
    Split source code into chunks that preserve function/class boundaries where possible.
    Prepends file path context to each chunk for better retrieval.
    """
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0
    file_header = f"[File: {file_path}]\n"

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        current_chunk.append(line)
        current_size += line_len

        if current_size >= chunk_size:
            chunk_text = file_header + "\n".join(current_chunk)
            chunks.append(chunk_text.strip())

            # Keep last few lines for overlap
            overlap_lines = max(2, overlap // 40)
            current_chunk = current_chunk[-overlap_lines:]
            current_size = sum(len(l) + 1 for l in current_chunk)

    # Final chunk
    if current_chunk:
        chunk_text = file_header + "\n".join(current_chunk)
        if chunk_text.strip():
            chunks.append(chunk_text.strip())

    return chunks


def _store_chunks(chunks: list[str], source: str, topic: str,
                  file_type: str = "text", collection=None) -> int:
    """Store a list of text chunks into ChromaDB. Returns count of chunks stored."""
    if collection is None:
        collection = _get_collection()

    if not chunks:
        return 0

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        doc_id = hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest()
        ids.append(doc_id)
        documents.append(chunk)
        metadatas.append({
            "source": source,
            "topic": topic,
            "file_type": file_type,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "stored_at": datetime.now().isoformat(),
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


# =============================================================================
# LangChain Tools (exposed to the agent)
# =============================================================================

@tool
def store_knowledge(content: str, source: str, topic: str = "general") -> str:
    """Store information in the local knowledge base for future retrieval.
    Use this to save useful information from web pages, documentation, or conversations
    so you can recall it later.

    Args:
        content: The text content to store.
        source: Where this content came from (URL, file path, or description).
        topic: A topic/category tag (e.g., 'react', 'nextjs', 'python', 'css').
    """
    try:
        chunks = _chunk_text(content)
        count = _store_chunks(chunks, source, topic, file_type="text")

        if count == 0:
            return "Error: No content to store."

        return (
            f"✅ Stored {count} chunks from '{source}' "
            f"under topic '{topic}' in the knowledge base."
        )
    except Exception as e:
        return f"Error storing knowledge: {str(e)}"


@tool
def index_project(directory_path: str, topic: str = None) -> str:
    """Index an entire project directory into the knowledge base.
    Recursively scans all source code files (JS, TS, Python, Go, CSS, HTML, etc.)
    and stores them for semantic search. This lets you understand and reference
    the project's codebase in future conversations.

    Args:
        directory_path: Path to the project root directory to index.
        topic: Optional topic tag. Defaults to the directory name.
    """
    try:
        path = Path(directory_path).resolve()

        if not path.exists():
            return f"Error: Directory not found: {path}"
        if not path.is_dir():
            return f"Error: Not a directory: {path}"

        if topic is None:
            topic = path.name

        collection = _get_collection()
        total_chunks = 0
        indexed_files = 0
        skipped_files = 0
        errors = []

        for root, dirs, files in os.walk(path):
            # Skip unwanted directories (modify dirs in-place to prevent recursion)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                # Also handle special filenames without extensions
                if ext not in CODE_EXTENSIONS and file.lower() not in (
                    "dockerfile", "makefile", "rakefile", "gemfile",
                    "procfile", ".gitignore", ".env.example",
                ):
                    skipped_files += 1
                    continue

                # Skip files that are too large
                try:
                    size = file_path.stat().st_size
                    if size > MAX_INDEX_FILE_SIZE:
                        skipped_files += 1
                        continue
                    if size == 0:
                        continue
                except OSError:
                    continue

                # Read and index the file
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    rel_path = str(file_path.relative_to(path))
                    chunks = _chunk_code(content, rel_path)
                    count = _store_chunks(
                        chunks,
                        source=rel_path,
                        topic=topic,
                        file_type=ext.lstrip(".") or "text",
                        collection=collection,
                    )
                    total_chunks += count
                    indexed_files += 1

                except Exception as e:
                    errors.append(f"{file_path.name}: {str(e)}")

        result = (
            f"✅ Project indexed: {path.name}\n"
            f"   📁 Files indexed: {indexed_files}\n"
            f"   📦 Total chunks: {total_chunks}\n"
            f"   ⏭️  Files skipped: {skipped_files}\n"
            f"   🏷️  Topic: '{topic}'"
        )

        if errors:
            result += f"\n   ⚠️  Errors: {len(errors)}"
            for err in errors[:5]:
                result += f"\n      - {err}"

        return result

    except Exception as e:
        return f"Error indexing project: {str(e)}"


@tool
def search_knowledge(query: str, topic: str = None, n_results: int = 5) -> str:
    """Search the local knowledge base for previously stored information.
    Use this to recall information from indexed projects, documentation,
    web pages, or past conversations.

    IMPORTANT: Always search the knowledge base FIRST when:
    - The user asks about their project code
    - The user references previously learned documentation
    - You need to understand the codebase structure or patterns

    Args:
        query: What to search for (semantic search).
        topic: Optional topic filter (e.g., 'react', 'nextjs', project name) to narrow results.
        n_results: Maximum number of results to return.
    """
    try:
        collection = _get_collection()

        if collection.count() == 0:
            return "Knowledge base is empty. Use store_knowledge or index_project to add information first."

        where_filter = {"topic": topic} if topic else None

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            where=where_filter,
        )

        if not results["documents"][0]:
            return f"No relevant knowledge found for: {query}"

        output = [f"Found {len(results['documents'][0])} relevant knowledge chunks:\n"]

        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ), 1):
            relevance = max(0, round((1 - dist) * 100, 1))
            source = meta.get("source", "Unknown")
            file_type = meta.get("file_type", "text")
            output.append(
                f"[{i}] Relevance: {relevance}% | "
                f"Topic: {meta.get('topic', 'N/A')} | "
                f"Type: {file_type} | "
                f"Source: {source}\n"
                f"    {doc[:500]}{'...' if len(doc) > 500 else ''}\n"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error searching knowledge: {str(e)}"


@tool
def list_knowledge_topics() -> str:
    """List all topics and sources stored in the knowledge base.
    Use this to see what projects, docs, and information have been indexed.
    """
    try:
        collection = _get_collection()

        if collection.count() == 0:
            return "Knowledge base is empty."

        # Get all metadata
        all_data = collection.get(include=["metadatas"])
        topics = {}

        for meta in all_data["metadatas"]:
            topic = meta.get("topic", "general")
            source = meta.get("source", "unknown")
            file_type = meta.get("file_type", "text")
            if topic not in topics:
                topics[topic] = {"sources": set(), "types": set(), "count": 0}
            topics[topic]["sources"].add(source)
            topics[topic]["types"].add(file_type)
            topics[topic]["count"] += 1

        output = [f"📚 Knowledge Base: {collection.count()} total chunks\n"]
        for topic, info in sorted(topics.items()):
            types_str = ", ".join(sorted(info["types"]))
            output.append(f"  📂 [{topic}] — {info['count']} chunks ({types_str})")
            # Show first 10 sources
            sorted_sources = sorted(info["sources"])
            for src in sorted_sources[:10]:
                output.append(f"      📄 {src}")
            if len(sorted_sources) > 10:
                output.append(f"      ... and {len(sorted_sources) - 10} more files")

        return "\n".join(output)

    except Exception as e:
        return f"Error listing knowledge: {str(e)}"


@tool
def clear_knowledge(topic: str = None) -> str:
    """Clear stored knowledge from the knowledge base.

    Args:
        topic: If provided, only clear knowledge for this specific topic.
               If not provided, clears ALL knowledge.
    """
    try:
        collection = _get_collection()

        if collection.count() == 0:
            return "Knowledge base is already empty."

        if topic:
            # Delete only entries matching this topic
            all_data = collection.get(include=["metadatas"])
            ids_to_delete = [
                id_ for id_, meta in zip(all_data["ids"], all_data["metadatas"])
                if meta.get("topic") == topic
            ]
            if not ids_to_delete:
                return f"No knowledge found for topic '{topic}'."

            collection.delete(ids=ids_to_delete)
            return f"🗑️ Cleared {len(ids_to_delete)} chunks for topic '{topic}'."
        else:
            # Delete entire collection and recreate
            client = _get_chroma_client()
            client.delete_collection("knowledge")
            return "🗑️ Cleared ALL knowledge from the knowledge base."

    except Exception as e:
        return f"Error clearing knowledge: {str(e)}"
