from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from django.conf import settings
import os
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "job_embeddings"

def create_collection():
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=768,
            distance=qmodels.Distance.COSINE,
        ),
    )
