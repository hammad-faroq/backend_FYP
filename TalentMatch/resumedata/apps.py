from django.apps import AppConfig

class ResumedataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "resumedata"

    def ready(self):
        pass
        # Import here to avoid circular imports
        # try:
        #     from resumedata.qdrant_service import sync_job_descriptions
        #     # Only sync if QDRANT is available and we're not in a management command
        #     import sys
        #     if 'runserver' in sys.argv:
        #         print("🔄 Initializing Qdrant sync...")
        #         sync_job_descriptions()
        # except Exception as e:
        #     print(f"⚠️ Qdrant sync skipped: {e}")