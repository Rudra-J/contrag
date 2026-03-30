import json, os, pytest
import glossary_engine

glossary_engine.GLOSSARY_PATH = "tests/tmp_glossary.json"

def setup_function():
    with open("tests/tmp_glossary.json", "w") as f:
        json.dump({}, f)

def teardown_function():
    if os.path.exists("tests/tmp_glossary.json"):
        os.remove("tests/tmp_glossary.json")

def test_load_glossary_empty():
    g = glossary_engine.load_glossary()
    assert g == {}

def test_save_and_load_term():
    entry = {
        "legal": "Force majeure refers to...",
        "layman": "An act of God clause...",
        "example": "If a hurricane destroys...",
        "sources": [{"file": "contract_a.pdf", "chunk": "Force majeure events include...", "chunk_index": 3}]
    }
    glossary_engine.save_term("force majeure", entry)
    g = glossary_engine.load_glossary()
    assert "force majeure" in g
    assert g["force majeure"]["legal"] == "Force majeure refers to..."

def test_merge_source_does_not_duplicate():
    entry = {
        "legal": "Indemnity means...",
        "layman": "Protection from loss...",
        "example": "Company A agrees to cover...",
        "sources": [{"file": "a.pdf", "chunk": "indemnify and hold harmless", "chunk_index": 1}]
    }
    glossary_engine.save_term("indemnity", entry)
    # Save same term again with same source — should not duplicate
    glossary_engine.save_term("indemnity", entry)
    g = glossary_engine.load_glossary()
    assert len(g["indemnity"]["sources"]) == 1
