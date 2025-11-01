from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader

def load_text_from_file(path: Path) -> str:
    """Load text from file using LangChain loaders for better handling"""
    if path.suffix.lower() == ".pdf":
        try:
            # Use LangChain PyPDFLoader for better PDF handling
            loader = PyPDFLoader(str(path))
            docs = loader.load()
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"[Loader] Error loading PDF {path}: {e}")
            return ""
    elif path.suffix.lower() == ".txt":
        try:
            # Use LangChain TextLoader for text files
            loader = TextLoader(str(path), encoding="utf-8")
            docs = loader.load()
            return "\n\n".join([doc.page_content for doc in docs])
        except Exception:
            # Fallback to simple read
            return path.read_text(encoding="utf-8", errors="ignore")
    elif path.suffix.lower() == ".md":
        # For markdown, use simple read (UnstructuredMarkdownLoader requires extra dependencies)
        # The RecursiveCharacterTextSplitter will still handle markdown better during chunking
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""  # ignore unknown types

def iter_kb_files(kb_dir: str):
    root = Path(kb_dir)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".pdf"}:
            yield p
