from django.core.management.base import BaseCommand
from jobs.matching.vector_store import create_collection

class Command(BaseCommand):
    help = "Initialize Qdrant collections"

    def handle(self, *args, **options):
        create_collection()
        self.stdout.write(self.style.SUCCESS("Qdrant collection created"))
