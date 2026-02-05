import re
import requests
from typing import List, Dict


def extract_id_from_share_url(url: str) -> str:
    m = re.search(r"(?:/d/|id=)([A-Za-z0-9_-]{10,})", url)
    if m:
        return m.group(1)
    # last path segment (folder/file) as fallback
    parts = url.rstrip('/').split('/')
    return parts[-1]


def download_public_file(file_id: str) -> bytes:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    r.raise_for_status()
    return r.content


def list_folder_files(folder_id: str, api_key: str) -> List[Dict]:
    """List files in a public folder using a Google API key (optional).
    Returns list of items with `id` and `name`.
    """
    if not api_key:
        raise ValueError("API key required to list folder contents via Drive API")
    url = (
        "https://www.googleapis.com/drive/v3/files"
        f"?q='{folder_id}'+in+parents&fields=files(id,name,mimeType)&key={api_key}"
    )
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data.get("files", [])
