from pathlib import Path
from pypdf import PdfReader

def load_text_from_file(path: Path) -> str:
    if path.suffix.lower() in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return ""  # ignore unknown types

def iter_kb_files(kb_dir: str):
    root = Path(kb_dir)
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".pdf"}:
            yield p
