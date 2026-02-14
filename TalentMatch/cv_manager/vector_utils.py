from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from django.conf import settings
import uuid
import os

# Initialize Qdrant and SentenceTransformer
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")

COLLECTION_NAME = "final_resume"

# Ensure collection exists
def ensure_collection():
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
    )

# Add resume to Qdrant
def add_resume_to_qdrant(user_id, resume_text,resume_Data=None):
    ensure_collection()
    embedding = model.encode(resume_text).tolist()
    point_id = str(uuid.uuid4())

    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "text": resume_text,
                },
            )
        ],
    )
    return point_id
