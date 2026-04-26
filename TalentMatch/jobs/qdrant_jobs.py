from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from jobs.models import Job
from django.conf import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)
model = SentenceTransformer("all-MiniLM-L6-v2")

COLLECTION_NAME = "JOBS"

def sync_jobs_to_qdrant():
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