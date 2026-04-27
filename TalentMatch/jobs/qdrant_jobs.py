from qdrant_client.http import models
from jobs.models import Job
from django.conf import settings
from utils.qdrant_client import get_qdrant_client

from utils.ml_models import get_sentence_transformer

def get_model():
    return get_sentence_transformer()
def get_client():
    return get_qdrant_client()

COLLECTION_NAME = "JOBS"


def sync_jobs_to_qdrant():
    client = get_client()
    # create collection only if not exists
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
            ),
        )

    jobs = Job.objects.all()
    print(f"Syncing {jobs.count()} jobs")

    points = []
    model = get_model()

    for job in jobs:
        text = f"{job.title}. {job.description}. {job.company_name}"
        vector = model.encode(text).tolist()

        points.append(
            models.PointStruct(
                id=job.id,
                vector=vector,
                payload={
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company_name,
                    "location": job.location,
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    print("✅ Jobs synced successfully")