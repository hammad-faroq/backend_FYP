from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer
from jobs.models import Job
import os
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def sync_jobs_to_qdrant():
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    collection_name = "final_job"

    try:
        client.delete_collection(collection_name=collection_name)
        print(f"🗑️ Deleted old collection '{collection_name}'")
    except Exception as e:
        print(f"⚠️ Collection '{collection_name}' does not exist or could not be deleted: {e}")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"🏗️ Created collection '{collection_name}'")

    jobs = Job.objects.all()
    print(f"Found {jobs.count()} jobs to sync...")

    vectors, payloads, ids = [], [], []

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
        collection_name=collection_name,
        points=qmodels.Batch(ids=ids, vectors=vectors, payloads=payloads)
    )

    count = client.count(collection_name=collection_name)
    print(f"✅ Uploaded {len(jobs)} jobs to Qdrant! Total points in collection: {count.count}")
