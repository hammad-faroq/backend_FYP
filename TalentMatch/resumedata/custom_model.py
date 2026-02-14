import os
import joblib
import numpy as np
from django.conf import settings
from .analyzer import extract_text_from_resume

# Lazy-loaded models
_resume_ranker_model = None
_embedding_model = None

def get_resume_ranker_model():
    global _resume_ranker_model
    if _resume_ranker_model is None:
        if not os.path.exists(settings.RESUME_RANKER_MODEL_PATH):
            raise FileNotFoundError(f"❌ Model not found at: {settings.RESUME_RANKER_MODEL_PATH}")
        _resume_ranker_model = joblib.load(settings.RESUME_RANKER_MODEL_PATH)
    return _resume_ranker_model

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        if not os.path.exists(settings.EMBEDDING_MODEL_PATH):
            raise FileNotFoundError(f"❌ Embedding model not found at: {settings.EMBEDDING_MODEL_PATH}")
        _embedding_model = joblib.load(settings.EMBEDDING_MODEL_PATH)
    return _embedding_model

def predict_resume_score(resume_path, job_description):
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text:
        return 0.0

    embedding_model = get_embedding_model()
    resume_vec = embedding_model.encode([resume_text])[0]  # 384 dims
    features = resume_vec.reshape(1, -1)
    score = get_resume_ranker_model().predict(features)[0]
    return round(float(score), 2)
