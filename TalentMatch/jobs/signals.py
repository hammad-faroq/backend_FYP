from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Job
from django.conf import settings
from qdrant_client.http import models as qmodels

COLLECTION_NAME = "JOBS"


_model = None

from utils.qdrant_client import get_qdrant_client

def get_client():
    return get_qdrant_client()

def get_model():
    global _model
    if _model is None:
        from utils.ml_models import get_sentence_transformer
        _model = get_sentence_transformer()  # uses cached version
    return _model

@receiver(post_save, sender=Job)
def job_saved(sender, instance, created, **kwargs):
    print("NEW JOB INDEXED" if created else "JOB UPDATED - REINDEXING")
    text = f"""
Title: {instance.title}
Company: {instance.company_name}
Location: {instance.location}
Description: {instance.description}
Requirements: {instance.requirements}
"""
    try:
        vector = get_model().encode(text).tolist()
        get_client().upsert(
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
        get_client().delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.PointIdsList(points=[instance.id])
        )
    except Exception as e:
        print("Qdrant delete error:", e)