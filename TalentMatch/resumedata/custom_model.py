import os
from sentence_transformers import  util
from .analyzer import extract_text_from_resume

from utils.ml_models import get_sentence_transformer

def get_embedding_model():
    return get_sentence_transformer()

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