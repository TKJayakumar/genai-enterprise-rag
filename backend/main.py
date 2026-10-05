import os
import sqlite3
import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import pipeline
import config
import documents as doc_store
import storage
from access_control import USERS

app = FastAPI(title="Enterprise RAG Platform - Local Build")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    import traceback
    from fastapi.responses import JSONResponse
    traceback.print_exc()
    detail = f"{type(exc).__name__}: {exc}"
    if "multipart" in detail.lower():
        detail += (
            " — this usually means the 'python-multipart' package isn't installed. "
            "Run: pip install -r requirements.txt"
        )
    return JSONResponse(status_code=500, content={"detail": detail})


MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

DB_PATH = os.path.join(os.path.dirname(__file__), "audit_log.sqlite3")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_id TEXT,
            role TEXT,
            query TEXT,
            status TEXT,
            num_citations INTEGER
        )
    """)
    conn.commit()
    conn.close()


_init_db()


class QueryRequest(BaseModel):
    user_id: str
    query: str


@app.get("/api/users")
def list_users():
    return [{"id": uid, **info} for uid, info in USERS.items()]


@app.get("/api/config")
def get_config():
    llm_mode = "Azure OpenAI" if config.AZURE_CONFIGURED else "Local demo mode (TF-IDF + templated generation)"
    storage_mode = storage.backend_name()
    return {
        "azure_configured": config.AZURE_CONFIGURED,
        "storage_configured": storage.is_cloud_configured(),
        "mode": f"{llm_mode} | Storage: {storage_mode}",
    }


@app.post("/api/query")
def query(req: QueryRequest):
    result = pipeline.run_pipeline(req.user_id, req.query)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO audit_log (timestamp, user_id, role, query, status, num_citations) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            req.user_id,
            USERS.get(req.user_id, {}).get("role", "guest"),
            req.query,
            result["status"],
            len(result["citations"]),
        ),
    )
    conn.commit()
    conn.close()

    return result


@app.get("/api/departments-roles")
def departments_roles():
    return {"departments": doc_store.KNOWN_DEPARTMENTS, "roles": doc_store.KNOWN_ROLES}


@app.get("/api/documents")
def list_documents():
    return doc_store.list_uploads()


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    access_roles: str = Form(...),  # comma-separated, e.g. "hr,all-staff"
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 15 MB upload limit.")

    roles = [r.strip() for r in access_roles.split(",") if r.strip()]
    if not roles:
        raise HTTPException(status_code=400, detail="At least one access role is required.")

    try:
        new_chunks = doc_store.add_upload(
            filename=file.filename,
            raw=raw,
            department=department,
            access_roles=roles,
            uploaded_at=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catches things like a missing pypdf/python-docx dependency, a
        # corrupt file, etc. Logged server-side and surfaced to the UI
        # instead of failing silently as a generic 500.
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {type(e).__name__}: {e}")

    return {
        "title": file.filename,
        "department": department,
        "access_roles": roles,
        "chunks_indexed": len(new_chunks),
    }


@app.delete("/api/documents/{upload_id}")
def delete_document(upload_id: str):
    ok = doc_store.delete_upload(upload_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return {"deleted": upload_id}


@app.get("/api/audit-log")
def audit_log(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Serve the frontend ----
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
