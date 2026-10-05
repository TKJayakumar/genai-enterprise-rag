"""
File storage backing for uploaded documents.

Uses Azure Data Lake Storage Gen2 when AZURE_STORAGE_ACCOUNT_NAME /
AZURE_STORAGE_ACCOUNT_KEY are configured. ADLS Gen2 exposes a
blob-compatible API, so the standard azure-storage-blob SDK is used
directly against it (no separate ADLS SDK needed) — this stores the raw
uploaded file (PDF/DOCX/TXT/MD) as a blob in the configured container.

Falls back to local disk (backend/data/uploads/) when Azure Storage isn't
configured, so uploads still work with zero cloud setup.
"""
import os
import config

_client = None
if config.AZURE_STORAGE_CONFIGURED:
    from azure.storage.blob import BlobServiceClient

    _account_url = f"https://{config.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    _client = BlobServiceClient(account_url=_account_url, credential=config.AZURE_STORAGE_ACCOUNT_KEY)
    try:
        _client.create_container(config.AZURE_STORAGE_CONTAINER)
    except Exception:
        pass  # container already exists — fine

_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(_LOCAL_DIR, exist_ok=True)


def is_cloud_configured() -> bool:
    return _client is not None


def backend_name() -> str:
    return "Azure Data Lake Storage Gen2" if _client is not None else "local disk"


def save_file(blob_name: str, raw: bytes) -> str:
    """
    Persist the raw file bytes to ADLS (if configured) or local disk.
    Returns a locator string that delete_file() can later use to remove it:
      - "adls://<container>/<blob_name>" for ADLS Gen2
      - an absolute local path for local disk
    """
    if _client is not None:
        blob_client = _client.get_blob_client(container=config.AZURE_STORAGE_CONTAINER, blob=blob_name)
        blob_client.upload_blob(raw, overwrite=True)
        return f"adls://{config.AZURE_STORAGE_CONTAINER}/{blob_name}"

    path = os.path.join(_LOCAL_DIR, blob_name)
    with open(path, "wb") as f:
        f.write(raw)
    return path


def delete_file(locator: str) -> None:
    if not locator:
        return
    if locator.startswith("adls://"):
        if _client is None:
            return
        _, rest = locator.split("adls://", 1)
        container, blob_name = rest.split("/", 1)
        try:
            _client.get_blob_client(container=container, blob=blob_name).delete_blob()
        except Exception:
            pass
    elif os.path.exists(locator):
        os.remove(locator)
