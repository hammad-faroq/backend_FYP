import os
import joblib
import pickle
from django.conf import settings
from .analyzer import extract_text_from_resume

resume_ranker_model = None
embedding_model = None


def load_model_safe(path):
    try:
        return joblib.load(path)
    except KeyError:
        # fallback for cross-Python-version pickle issues
        with open(path, 'rb') as f:
            return pickle.load(f, encoding='latin-1')


def load_models():
    global resume_ranker_model, embedding_model
    print("MODEL PATH:", settings.RESUME_RANKER_MODEL_PATH)
    print("FILE EXISTS:", os.path.exists(settings.RESUME_RANKER_MODEL_PATH))

    if resume_ranker_model is None:
        resume_ranker_model = load_model_safe(settings.RESUME_RANKER_MODEL_PATH)

    if embedding_model is None:
        embedding_model = load_model_safe(settings.EMBEDDING_MODEL_PATH)
        


def predict_resume_score(resume_path, job_description):
    load_models()

    resume_text = extract_text_from_resume(resume_path)
    if not resume_text:
        return 0.0

    resume_vec = embedding_model.encode([resume_text])[0]
    features = resume_vec.reshape(1, -1)
    score = resume_ranker_model.predict(features)[0]

    return round(float(score), 2)