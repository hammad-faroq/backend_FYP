# cv_manager/vector_sync_jobs.py
from datetime import datetime
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from jobs.models import Job
from django.conf import settings
import os
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# 1️⃣ Connect to Qdrant
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# 2️⃣ Load sentence transformer
model = SentenceTransformer("all-MiniLM-L6-v2")  # Must match resume embeddings

# 3️⃣ Ensure collection exists
COLLECTION_NAME = "final_job"
# qdrant.recreate_collection(
#     collection_name=COLLECTION_NAME,
#     vectors_config=models.VectorParams(
#         size=384,
#         distance=models.Distance.COSINE,
#     ),
# )

# 4️⃣ Fetch all open jobs
jobs = Job.objects.filter(application_deadline__gte=datetime.now().date())
print(f"Found {jobs.count()} open jobs to sync...")

points = []
for job in jobs:
    vector = model.encode(job.title + " " + job.description).tolist()
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

# 5️⃣ Upload in batch
if points:
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅ Uploaded {len(points)} jobs to Qdrant!")
else:
    print("⚠️ No open jobs to upload.")
