from django.core.management.base import BaseCommand
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from jobs.models import Job
from django.conf import settings

COLLECTION = "job_vectors"
VECTOR_SIZE = 384

class Command(BaseCommand):
    help = "Initialize Qdrant job_vectors collection"

    def handle(self, *args, **kwargs):
        client = QdrantClient(
            host=getattr(settings, "QDRANT_HOST", "localhost"),
            port=getattr(settings, "QDRANT_PORT", 6333)
        )

        collections = [c.name for c in client.get_collections().collections]

        if COLLECTION not in collections:
            self.stdout.write("📦 Creating job_vectors collection...")

            client.create_collection(
                collection_name=COLLECTION,
                vectors_config={
                    "size": VECTOR_SIZE,
                    "distance": "Cosine"
                }
            )

        self.stdout.write("🚀 Syncing jobs to Qdrant...")

        model = SentenceTransformer("all-MiniLM-L6-v2")

        points = []
        for job in Job.objects.all():
            vector = model.encode(job.description).tolist()

            points.append({
                "id": job.id,
                "vector": vector,
                "payload": {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company_name,
                    "location": job.location,
                }
            })

        client.upsert(
            collection_name=COLLECTION,
            points=points
        )

        self.stdout.write(self.style.SUCCESS("✅ Qdrant initialized successfully"))
