import os, json, shutil
from datetime import datetime

UPLOAD_DIR = "uploads"
META_PATH = "data/files_meta.json"

def _load_meta():
    if not os.path.exists(META_PATH):
        return []
    with open(META_PATH) as f:
        return json.load(f)

def _save_meta(meta):
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

def save_file(filename: str, content: bytes) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    meta = _load_meta()
    meta = [m for m in meta if m["name"] != filename]  # replace if exists
    meta.append({
        "name": filename,
        "path": path,
        "uploaded_at": datetime.now().isoformat(),
        "size_kb": round(len(content) / 1024, 2)
    })
    _save_meta(meta)
    return path

def remove_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    meta = _load_meta()
    _save_meta([m for m in meta if m["name"] != filename])

def list_files():
    return _load_meta()

def get_file_path(filename: str) -> str:
    return os.path.join(UPLOAD_DIR, filename)
