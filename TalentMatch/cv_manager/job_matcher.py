import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from cv_manager.models import ParsedResume, JobMatch
from jobs.models import Job
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ----------------- Settings -----------------
QDRANT_HOST = getattr(settings, "QDRANT_HOST", "localhost")
QDRANT_PORT = getattr(settings, "QDRANT_PORT", 6333)
JOB_COLLECTION = "final_job"

# GROQ settings
GROQ_API_KEY = getattr(settings, "GROQ_API_KEY", None)
GROQ_URL = "https://api.groq.ai/v1/embeddings"

# BERT model as fallback
bert_model = SentenceTransformer("all-MiniLM-L6-v2")

# Similarity threshold
SIMILARITY_THRESHOLD = 0.2  # Tune as needed


def get_groq_embedding(text: str) -> list:
    """Generate vector using Groq API. Returns a list of floats."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in settings.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"text": text}

    response = requests.post(GROQ_URL, json=data, headers=headers, timeout=15)
    if response.status_code != 200:
        raise ValueError(f"Groq API error: {response.text}")

    result = response.json()
    vector = result.get("embedding")
    if not vector:
        raise ValueError("No embedding returned from Groq API")
    return vector


def find_similar_jobs(user, limit=5, use_groq=False, save_to_db=True):
    """
    Finds similar jobs for the user's resume, optionally saves results in DB.
    Returns a dict with success, message, and matched_jobs list.
    """
    try:
        resume = ParsedResume.objects.filter(user=user).first()
        if not resume or not resume.raw_text.strip():
            return {"success": False, "message": "No resume uploaded or resume has no text.", "matched_jobs": []}

        # ---------------- Generate embedding ----------------
        try:
            if use_groq:
                resume_vector = get_groq_embedding(resume.raw_text)
                source = "Groq"
                if len(resume_vector) != 384:  # Fallback to BERT if Groq dimension mismatch
                    logger.warning("Groq embedding dimension mismatch. Falling back to BERT.")
                    resume_vector = bert_model.encode(resume.raw_text).tolist()
                    source = "BERT"
            else:
                resume_vector = bert_model.encode(resume.raw_text).tolist()
                source = "BERT"
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return {"success": False, "message": f"Embedding generation failed: {e}", "matched_jobs": []}

        if not resume_vector:
            return {"success": False, "message": "Embedding returned empty.", "matched_jobs": []}

        # ---------------- Connect to Qdrant ----------------
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Filter only open jobs
        today = datetime.now().date()
        open_jobs = Job.objects.filter(application_deadline__gte=today)
        open_job_ids = set(open_jobs.values_list("id", flat=True))
        if not open_job_ids:
            return {"success": True, "message": "No open job postings.", "matched_jobs": []}

        # Fetch extra results to filter later
        results = client.search(
            collection_name=JOB_COLLECTION,
            query_vector=resume_vector,
            limit=limit * 3,  # Fetch more to filter by threshold and open jobs
            with_payload=True
        )
        logger.info(f"Fetched {len(results)} results from Qdrant")

        # ---------------- Filter and format matches ----------------
        matched_jobs = []
        for r in results:
            payload = getattr(r, "payload", {})
            if not payload:
                continue

            job_id = payload.get("job_id")
            if not job_id or job_id not in open_job_ids:
                continue

            # Calculate similarity (supports cosine distance)
            similarity = float(r.score)
            similarity = max(0.0, min(1.0, similarity))  # Clamp between 0-1

            # If your collection uses distance instead of similarity:
            # similarity = 1 - similarity

            if similarity < SIMILARITY_THRESHOLD:
                continue

            matched_jobs.append({
                "job_id": job_id,
                "title": payload.get("title", "Unknown Title"),
                "company": payload.get("company", ""),
                "location": payload.get("location", ""),
                "score": round(similarity, 4),
                "source": source
            })

            if len(matched_jobs) >= limit:
                break

        logger.info(f"Matched {len(matched_jobs)} jobs above threshold")

        # ---------------- Save matched jobs to DB ----------------
        if save_to_db and matched_jobs:
            JobMatch.objects.filter(user=user).delete()
            JobMatch.objects.bulk_create([
                JobMatch(
                    user=user,
                    job_id=job["job_id"],
                    title=job["title"],
                    company=job.get("company", ""),
                    location=job.get("location", ""),
                    score=job["score"],
                    source=job["source"]
                ) for job in matched_jobs
            ])

        return {"success": True, "message": "Matching jobs found successfully.", "matched_jobs": matched_jobs}

    except Exception as e:
        logger.error(f"Unexpected error in find_similar_jobs: {e}", exc_info=True)
        return {"success": False, "message": f"Failed to find similar jobs: {e}", "matched_jobs": []}
