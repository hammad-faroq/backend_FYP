from django.core.management.base import BaseCommand
from jobs.qdrant_utils import sync_jobs_to_qdrant

class Command(BaseCommand):
    help = "Sync jobs to Qdrant"

    def handle(self, *args, **kwargs):
        sync_jobs_to_qdrant()
