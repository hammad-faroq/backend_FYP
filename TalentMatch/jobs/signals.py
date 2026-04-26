from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Job
from qdrant_client import QdrantClient
from django.conf import settings
from sentence_transformers import SentenceTransformer
from qdrant_client.http import models as qmodels

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)
model = SentenceTransformer("all-MiniLM-L6-v2")

COLLECTION_NAME = "JOBS"

@receiver(post_save, sender=Job)
def job_saved(sender, instance, created, **kwargs):
    if created:
        print("NEW JOB INDEXED")
    else:
        print("JOB UPDATED - REINDEXING")

    text = f"""
Title: {instance.title}
Company: {instance.company_name}
Location: {instance.location}
Description: {instance.description}
Requirements: {instance.requirements}
"""
    vector = model.encode(text).tolist()

    try:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qmodels.PointStruct(
                    id=instance.id,
                    vector=vector,
                    payload={
                        "job_id": instance.id,
                        "title": instance.title,
                        "company": instance.company_name,
                        "location": instance.location,
                    }
                )
            ]
        )
    except Exception as e:
        print("Qdrant upsert error:", e)

@receiver(post_delete, sender=Job)
def job_deleted(sender, instance, **kwargs):
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(
                points=[instance.id]
            )
        )
    except Exception as e:
        print("Qdrant delete error:", e)