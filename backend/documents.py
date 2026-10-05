"""
Document store backing the Knowledge Retrieval node.

Holds two kinds of documents, merged into one in-memory list:
  1. Sample documents shipped with the app (data/documents.json).
  2. User-uploaded documents (PDF / DOCX / TXT / MD), parsed to text,
     chunked, tagged with a department + access roles at upload time,
     and persisted to data/uploaded_documents.json so they survive a
     server restart. The original file bytes are saved via storage.py —
     Azure Data Lake Storage Gen2 when configured, local disk otherwise.

Any code that needs "all documents" should call list_documents() rather
than reading a JSON file directly, so uploads are picked up everywhere
(retrieval, classifier, access control, dashboard).
"""
import json
import os
import uuid

import storage

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_SAMPLE_DOCS_PATH = os.path.join(_DATA_DIR, "documents.json")
_UPLOADED_DOCS_PATH = os.path.join(_DATA_DIR, "uploaded_documents.json")

CHUNK_SIZE = 900       # characters per chunk
CHUNK_OVERLAP = 150    # characters of overlap between chunks

KNOWN_DEPARTMENTS = ["hr", "finance", "legal", "engineering", "general"]
KNOWN_ROLES = ["hr", "finance", "legal", "engineering", "exec", "guest", "all-staff"]


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


with open(_SAMPLE_DOCS_PATH, "r", encoding="utf-8") as f:
    _SAMPLE_DOCS = json.load(f)
    for d in _SAMPLE_DOCS:
        d["source"] = "sample"

_UPLOADED_DOCS = _load_json(_UPLOADED_DOCS_PATH, [])


def list_documents():
    """All documents currently in the knowledge base (sample + uploaded)."""
    return _SAMPLE_DOCS + _UPLOADED_DOCS


def list_uploads():
    """Metadata about uploaded source files, grouped (not chunk-level)."""
    grouped = {}
    for d in _UPLOADED_DOCS:
        key = d.get("upload_id", d["id"])
        if key not in grouped:
            grouped[key] = {
                "upload_id": key,
                "title": d["title"],
                "department": d["department"],
                "access_roles": d["access_roles"],
                "chunks": 0,
                "uploaded_at": d.get("uploaded_at"),
                "storage_backend": d.get("storage_backend", "local disk"),
            }
        grouped[key]["chunks"] += 1
    return list(grouped.values())


def _extract_text(filename: str, raw: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if ext == ".docx":
        import docx
        import io
        d = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in d.paragraphs)

    if ext in (".txt", ".md"):
        return raw.decode("utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type '{ext}'. Supported: .pdf, .docx, .txt, .md")


def _chunk_text(text: str):
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def add_upload(filename: str, raw: bytes, department: str, access_roles: list, uploaded_at: str):
    """
    Parse an uploaded file, chunk it, and add it to the knowledge base.
    The original file is saved via storage.py — Azure Data Lake Storage
    Gen2 when configured, local disk otherwise. Returns the list of newly
    created document chunk records.
    """
    text = _extract_text(filename, raw)
    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("No extractable text found in this file.")

    upload_id = uuid.uuid4().hex[:12]
    storage_path = storage.save_file(f"{upload_id}_{filename}", raw)

    new_docs = []
    for i, chunk in enumerate(chunks):
        new_docs.append({
            "id": f"upload-{upload_id}-{i+1}",
            "upload_id": upload_id,
            "title": filename,
            "department": department,
            "access_roles": access_roles,
            "text": chunk,
            "source": "uploaded",
            "uploaded_at": uploaded_at,
            "storage_path": storage_path,
            "storage_backend": storage.backend_name(),
        })

    _UPLOADED_DOCS.extend(new_docs)
    _save_json(_UPLOADED_DOCS_PATH, _UPLOADED_DOCS)

    import retrieval
    retrieval.invalidate_cache()

    return new_docs


def delete_upload(upload_id: str) -> bool:
    """Remove all chunks belonging to an uploaded file, and delete the
    original file from wherever storage.py put it (ADLS Gen2 or local)."""
    global _UPLOADED_DOCS
    to_remove = [d for d in _UPLOADED_DOCS if d.get("upload_id") == upload_id]
    if not to_remove:
        return False

    storage_path = to_remove[0].get("storage_path")
    storage.delete_file(storage_path)

    _UPLOADED_DOCS = [d for d in _UPLOADED_DOCS if d.get("upload_id") != upload_id]
    _save_json(_UPLOADED_DOCS_PATH, _UPLOADED_DOCS)

    import retrieval
    retrieval.invalidate_cache()
    return True
