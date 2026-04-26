import requests
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from cv_manager.models import ParsedResume, JobMatch
from jobs.models import Job
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

JOB_COLLECTION = "JOBS"
# BERT model as fallback
bert_model = SentenceTransformer("all-MiniLM-L6-v2")

# Similarity threshold
SIMILARITY_THRESHOLD = 0.15  # Tune as needed

def find_similar_jobs(user, limit=5, save_to_db=True):
    """
    Finds similar jobs for the user's resume using ONLY SentenceTransformer embeddings.
    """

    try:
        resume = ParsedResume.objects.filter(user=user).first()

        if not resume or not resume.raw_text or not resume.raw_text.strip():
            return {
                "success": True,
                "message": "No resume found. Please upload your resume.",
                "matched_jobs": []
            }

        # ---------------- Generate embedding (ONLY BERT) ----------------
        resume_vector = bert_model.encode(resume.raw_text).tolist()
        source = "BERT"

        if not resume_vector:
            return {
                "success": False,
                "message": "Embedding generation failed.",
                "matched_jobs": []
            }

        # ---------------- Connect to Qdrant ----------------
        client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )

        today = datetime.now().date()
        open_jobs = Job.objects.filter(application_deadline__gte=today)#deu to this line
        open_job_ids = set(open_jobs.values_list("id", flat=True))

        if not open_job_ids:
            return {
                "success": True,
                "message": "No open job postings.",
                "matched_jobs": []
            }

        # ---------------- Search Qdrant ----------------
        results = client.search(
            collection_name=JOB_COLLECTION,
            query_vector=resume_vector,
            limit=limit * 3,
            with_payload=True
        )

        matched_jobs = []

        for r in results:
            payload = r.payload or {}

            job_id = payload.get("job_id")
            if not job_id or job_id not in open_job_ids:
                continue

            similarity = float(r.score)
            similarity = max(0.0, min(1.0, similarity))

            if similarity < SIMILARITY_THRESHOLD:
                continue

            job = Job.objects.filter(id=job_id).first()
            if not job:
                continue

            matched_jobs.append({
                "job_id": job.id,
                "title": job.title,
                "location": job.location,
                "score": round(similarity, 4),
                "source": source
            })

            if len(matched_jobs) >= limit:
                break

        # ---------------- Save results ----------------
        if save_to_db and matched_jobs:
            JobMatch.objects.filter(user=user).delete()
            JobMatch.objects.bulk_create([
                JobMatch(
                    user=user,
                    job_id=j["job_id"],
                    title=j["title"],
                    company="",
                    location=j["location"],
                    score=j["score"],
                    source=j["source"]
                )
                for j in matched_jobs
            ])

        if not matched_jobs:
            return {
                "success": True,
                "message": "No matching jobs found.",
                "matched_jobs": []
            }

        return {
            "success": True,
            "message": "Matching jobs found successfully.",
            "matched_jobs": matched_jobs
        }

    except Exception as e:
        logger.error(f"Error in find_similar_jobs: {e}", exc_info=True)
        return {
            "success": False,
            "message": str(e),
            "matched_jobs": []
        }
