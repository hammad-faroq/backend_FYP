import os
import joblib
import numpy as np
from django.conf import settings
from .analyzer import extract_text_from_resume

# ------------------------------
# Load models ONCE at startup
# ------------------------------
if not os.path.exists(settings.RESUME_RANKER_MODEL_PATH):
    raise FileNotFoundError(f"❌ Model not found at: {settings.RESUME_RANKER_MODEL_PATH}")

if not os.path.exists(settings.EMBEDDING_MODEL_PATH):
    raise FileNotFoundError(f"❌ Embedding model not found at: {settings.EMBEDDING_MODEL_PATH}")

resume_ranker_model = joblib.load(settings.RESUME_RANKER_MODEL_PATH)
embedding_model = joblib.load(settings.EMBEDDING_MODEL_PATH)

print("✅ Custom model & embedding model loaded successfully")


# ------------------------------
# Predict score
# ------------------------------
def predict_resume_score(resume_path, job_description):
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text:
        return 0.0

    resume_vec = embedding_model.encode([resume_text])[0]  # 384 dims
    features = resume_vec.reshape(1, -1)
    score = resume_ranker_model.predict(features)[0]
    return round(float(score), 2)
