"""Rebuild BM25 storage from canonical cards only."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import build_index

if __name__ == '__main__':
    print(json.dumps(build_index(), indent=2))
