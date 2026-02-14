from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from django.conf import settings

client = QdrantClient(
    host=getattr(settings, "QDRANT_HOST", "localhost"),
    port=getattr(settings, "QDRANT_PORT", 6333),
)

COLLECTION_NAME = "job_embeddings"

def create_collection():
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=768,
            distance=qmodels.Distance.COSINE,
        ),
    )
