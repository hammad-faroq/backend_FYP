# ranking/management/commands/rank_applicants.py
from django.core.management.base import BaseCommand
from ranking.services.ranking_engine import rank_applicants_for_job

class Command(BaseCommand):
    help = "Rank applicants for a job_id: usage --job_id=<id>"

    def add_arguments(self, parser):
        parser.add_argument('--job_id', type=int, required=True)

    def handle(self, *args, **options):
        job_id = options['job_id']
        results = rank_applicants_for_job(job_id, use_qdrant=True, save_to_db=True)
        for r in results:
            self.stdout.write(f"{r['job_application_id']} -> {r['predicted_score']}")
        self.stdout.write(self.style.SUCCESS("Ranking complete."))
