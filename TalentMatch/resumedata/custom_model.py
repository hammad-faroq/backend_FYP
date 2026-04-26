import os
from sentence_transformers import SentenceTransformer, util
from .analyzer import extract_text_from_resume

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def predict_resume_score(resume_path, job_description):
    model = get_embedding_model()
    
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text:
        return 0.0

    resume_vec = model.encode(resume_text, convert_to_tensor=True)
    job_vec = model.encode(job_description, convert_to_tensor=True)
    
    score = util.cos_sim(resume_vec, job_vec).item()
    
    # convert to 0-100
    score = round((score + 1) / 2 * 100, 2)
    return score