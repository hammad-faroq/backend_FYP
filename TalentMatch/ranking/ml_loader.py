# ranking/ml_loader.py
import os
import joblib
from django.conf import settings
from threading import Lock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "ml_models")

_rank_model = None
_embed_model = None
_lock = Lock()

def _load_rank_model():
    global _rank_model
    if _rank_model is None:
        with _lock:
            if _rank_model is None:
                path = os.path.join(MODEL_DIR, "resume_ranker_model.pkl")
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Ranking model not found at {path}")
                _rank_model = joblib.load(path)
    return _rank_model

def _load_embedding_model():
    global _embed_model
    if _embed_model is None:
        with _lock:
            if _embed_model is None:
                path = os.path.join(MODEL_DIR, "embedding_model.pkl")
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Embedding model not found at {path}")
                _embed_model = joblib.load(path)
    return _embed_model

def get_rank_model():
    return _load_rank_model()

def get_embedding_model():
    return _load_embedding_model()
