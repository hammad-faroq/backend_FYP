# ranking/services/ranking_engine.py
import numpy as np
from django.conf import settings
from jobs.models import Job, JobApplication
from resumedata.analyzer import extract_text_from_resume    # reuse your extractor

from ranking.ml_loader import get_rank_model, get_embedding_model

# If you use Qdrant for job embeddings, set connection here (optional)
from utils.qdrant_client import get_qdrant_client
qdrant_client = None
try:
    qdrant_client = get_qdrant_client()
except Exception:
    qdrant_client = None

def embed_text(text: str):
    embed_model = get_embedding_model()
    # Most sentence-transformers have encode() returning array or list
    emb = embed_model.encode([text])
    if isinstance(emb, list) and len(emb) == 1:
        emb = emb[0]
    return np.array(emb, dtype=float)

def get_job_vector_from_qdrant(job_id: int, collection="job_vectors"):
    """Try to retrieve job vector from Qdrant if available."""
    if not qdrant_client:
        return None
    try:
        hits = qdrant_client.retrieve(collection_name=collection, ids=[job_id], with_vectors=True)
        if len(hits) and hasattr(hits[0], "vector") and hits[0].vector:
            return np.array(hits[0].vector, dtype=float)
    except Exception:
        return None
    return None

def cosine_similarity(a, b):
    a = np.squeeze(a)
    b = np.squeeze(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def build_feature_vector(similarity_score: float, llm_rank: float = 0.0, experience_years: float = 0.0, skill_match_count: int = 0, extra: dict = None):
    """
    IMPORTANT: adapt this ordering to the exact features your rank_model expects.
    Example features: [similarity_score, llm_rank, experience_years, skill_match_count]
    """
    features = [
        similarity_score,
        llm_rank,
        experience_years,
        skill_match_count,
    ]
    if extra:
        features.extend([extra.get(k, 0) for k in sorted(extra.keys())])
    return np.array(features, dtype=float).reshape(1, -1)

def predict_rank_from_features(features_vector: np.ndarray):
    model = get_rank_model()
    pred = model.predict(features_vector)
    # If model outputs normalized score, map it as needed
    return float(pred[0])

def rank_applicants_for_job(job_id: int, use_qdrant=True, save_to_db=True):
    """
    Main function: for a given job_id, embed job (via Qdrant or compute from job text),
    iterate applicants, compute feature vector and predict rank, save into JobApplication.rank_score.
    Returns list of dicts: [{'app_id':..., 'score':...}, ...]
    """
    job = Job.objects.get(id=job_id)
    job_text = f"{job.title}. {job.description}. {job.requirements or ''}"

    job_vector = None
    if use_qdrant:
        job_vector = get_job_vector_from_qdrant(job_id)
    if job_vector is None:
        job_vector = embed_text(job_text)

    results = []
    apps = job.applications.all()
    for app in apps:
        # 1) extract resume text
        resume_path = app.resume.path if app.resume else None
        resume_text = ""
        if resume_path:
            resume_text = extract_text_from_resume(resume_path)

        # 2) compute embedding and similarity
        resume_vector = embed_text(resume_text) if resume_text else None
        similarity = cosine_similarity(job_vector, resume_vector)

        # 3) prepare other features
        # NOTE: if you already store experience/skills from Groq or parsing, use them
        try:
            experience_years = float(getattr(app, "total_experience", 0) or 0)
        except Exception:
            experience_years = 0.0

        skill_match_count = len(getattr(app, "skills", []) or [])

        # llm_rank can be present if you still call Groq; default 0
        llm_rank = float(getattr(app, "groq_rank", 0) or 0)

        # Build features (match ordering to training)
        features = build_feature_vector(
            similarity_score=similarity,
            llm_rank=llm_rank,
            experience_years=experience_years,
            skill_match_count=skill_match_count,
        )

        # 4) predict final rank
        predicted_score = predict_rank_from_features(features)

        # 5) save
        if save_to_db:
            app.rank_score = predicted_score
            app.bert_similarity = round(similarity * 100, 2)  # keep percent if desired
            app.save()

        results.append({
            "job_application_id": app.id,
            "candidate_email": app.applicant.email if app.applicant else None,
            "predicted_score": predicted_score,
            "similarity": round(float(similarity * 100), 2)
        })

    # Order by predicted_score desc
    results = sorted(results, key=lambda x: x["predicted_score"], reverse=True)
    return results
