# ============================================================
#  ALTROS Module: Knowledge (Phase 1)
#  Books aur PDFs padhne ki ability — RAG system.
#  
#  Usage:
#    python main.py --add-book "path/to/book.pdf"
#    ALTROS: "Atomic Habits ka main idea kya hai?"
# ============================================================

import os
from modules.base import BaseModule
from config import CHROMA_PERSIST_DIR, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RESULTS

# Keywords jo indicate karte hain user kuch puchh raha hai knowledge se
KNOWLEDGE_TRIGGERS = [
    "book", "kitab", "chapter", "explain", "batao", "kya hai",
    "define", "meaning", "concept", "theory", "summary", "samjhao",
    "padha", "likha", "mentioned", "according", "author", "likhte"
]


class KnowledgeModule(BaseModule):
    name = "knowledge"
    description = "Book and document Q&A using RAG"

    def __init__(self):
        self._ready = False
        self._collection = None

    def on_enable(self):
        try:
            import chromadb
            from chromadb.config import Settings
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self._collection = client.get_or_create_collection(
                name="altros_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            self._ready = True
            count = self._collection.count()
            print(f"     📚 Knowledge base ready — {count} chunks loaded")
        except ImportError:
            print("     ⚠️  chromadb not installed. Run: pip install chromadb")
        except Exception as e:
            print(f"     ⚠️  Knowledge module error: {e}")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready or self._collection.count() == 0:
            return False
        q_lower = query.lower()
        return any(trigger in q_lower for trigger in KNOWLEDGE_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        """
        Relevant chunks retrieve karo aur context ke roop mein return karo.
        Brain in chunks ko use karke answer generate karega.
        """
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(TOP_K_RESULTS, self._collection.count()),
            )
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]

            if not docs:
                return ""

            context_parts = []
            for doc, meta in zip(docs, metas):
                source = meta.get("source", "Unknown")
                context_parts.append(f"[From: {source}]\n{doc}")

            return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            return ""

    # ── Book ingestion (call this separately) ─────────────────

    def add_document(self, file_path: str) -> int:
        """
        PDF ya text file ko knowledge base mein add karo.
        pypdf directly use karta hai — langchain loader nahi.
        Returns: number of chunks added
        """
        if not self._ready:
            print("Knowledge module ready nahi hai.")
            return 0

        print(f"📖 Reading: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()

        # --- Extract raw text ---
        raw_text = ""
        if ext == ".pdf":
            try:
                import pypdf
            except ImportError:
                print("Install karo: pip install pypdf")
                return 0
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    raw_text += t + "\n"
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()

        if not raw_text.strip():
            print("⚠️  File mein koi readable text nahi mila.")
            return 0

        # --- Split into chunks manually ---
        chunks = []
        start = 0
        text_len = len(raw_text)
        while start < text_len:
            end = min(start + CHUNK_SIZE, text_len)
            chunk = raw_text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start += CHUNK_SIZE - CHUNK_OVERLAP

        source_name = os.path.basename(file_path)
        ids, texts, metas = [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{source_name}_{i}")
            texts.append(chunk)
            metas.append({"source": source_name, "page": i})

        self._collection.upsert(ids=ids, documents=texts, metadatas=metas)
        print(f"✅ Added {len(chunks)} chunks from '{source_name}'")
        return len(chunks)