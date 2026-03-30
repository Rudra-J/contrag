import os, json, pytest, shutil
from pathlib import Path

# Patch paths before import
import file_manager
file_manager.UPLOAD_DIR = "tests/tmp_uploads"
file_manager.META_PATH = "tests/tmp_meta.json"

def setup_function():
    os.makedirs("tests/tmp_uploads", exist_ok=True)
    with open("tests/tmp_meta.json", "w") as f:
        json.dump([], f)

def teardown_function():
    shutil.rmtree("tests/tmp_uploads", ignore_errors=True)
    if os.path.exists("tests/tmp_meta.json"):
        os.remove("tests/tmp_meta.json")

def test_save_file_creates_file_and_meta():
    dummy = b"PDF content"
    path = file_manager.save_file("contract_a.pdf", dummy)
    assert os.path.exists(path)
    meta = file_manager.list_files()
    assert len(meta) == 1
    assert meta[0]["name"] == "contract_a.pdf"

def test_remove_file_deletes_file_and_meta():
    file_manager.save_file("contract_b.pdf", b"content")
    file_manager.remove_file("contract_b.pdf")
    assert not os.path.exists(os.path.join("tests/tmp_uploads", "contract_b.pdf"))
    assert len(file_manager.list_files()) == 0

def test_list_files_returns_metadata():
    file_manager.save_file("c.pdf", b"x")
    files = file_manager.list_files()
    assert "uploaded_at" in files[0]
    assert "size_kb" in files[0]
    assert "path" in files[0]
