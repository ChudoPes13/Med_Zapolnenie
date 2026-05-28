import os
from pathlib import Path

os.environ.setdefault("MEDJARVIS_GPU_REQUIRED", "0")
os.environ.setdefault("MEDJARVIS_REQUIRE_LLM", "0")
os.environ.setdefault("MEDJARVIS_DATABASE_URL", "sqlite:///data/test_medjarvis.db")

db_path = Path("data/test_medjarvis.db")
if db_path.exists():
    db_path.unlink()
