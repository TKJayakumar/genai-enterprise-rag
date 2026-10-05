import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large")

# If no Azure credentials are supplied, the app runs in local demo mode:
# retrieval falls back to TF-IDF and generation falls back to a templated
# extractive response, so the full pipeline (and every node in the graph)
# is still runnable and demonstrable without any cloud cost.
AZURE_CONFIGURED = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)

# Azure Data Lake Storage Gen2 (optional). ADLS Gen2 exposes a fully
# blob-compatible API, so the azure-storage-blob SDK talks to it directly —
# no separate ADLS-specific SDK is required. If these are left blank,
# uploaded files are stored on local disk instead (see storage.py).
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "documents")
AZURE_STORAGE_CONFIGURED = bool(AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY)

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
TOP_K = int(os.getenv("TOP_K", "3"))

# Below this cosine-similarity score, a "match" is treated as noise (e.g. a
# single incidental shared word) rather than a genuine relevant document, so
# it doesn't get pulled into the retrieved set. Only applies to the local
# TF-IDF fallback; Azure embeddings are far less prone to this kind of
# spurious keyword overlap.
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.08"))
