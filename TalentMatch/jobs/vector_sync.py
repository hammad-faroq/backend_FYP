from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer
from jobs.models import Job
import os
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def sync_jobs_to_qdrant():
    client =  QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    jobs = Job.objects.all()
    print(f"Found {jobs.count()} jobs to sync...")

    vectors = []
    payloads = []
    ids = []

    for job in jobs:
        text = f"{job.title}. {job.description}. {job.company_name}"
        vector = model.encode(text).tolist()

        vectors.append(vector)
        payloads.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company_name,
        })
        ids.append(job.id)

    client.upsert(
        collection_name="final_job",
        points=qmodels.Batch(
            ids=ids,
            vectors=vectors,
            payloads=payloads
        )
    )

    print(f"✅ Uploaded {len(jobs)} jobs to Qdrant!")
