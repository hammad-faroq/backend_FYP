from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Job
from django.conf import settings
from qdrant_client.http import models as qmodels
from utils.qdrant_client import get_qdrant_client
from utils.ml_models import get_sentence_transformer

def get_model():
    return get_sentence_transformer()
def get_client():
    return get_qdrant_client()

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
    model=get_model()
    vector = model.encode(text).tolist()
    client=get_client()

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
    client=get_client()
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(
                points=[instance.id]
            )
        )
    except Exception as e:
        print("Qdrant delete error:", e)