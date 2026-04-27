from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'

    def ready(self):
        import jobs.signals
        self.create_qdrant_collection()

    def create_qdrant_collection(self):
        try:
            from utils.qdrant_client import get_qdrant_client
            from qdrant_client.http import models as qmodels

            client = get_qdrant_client()
            collections = [c.name for c in client.get_collections().collections]

            if "JOBS" not in collections:
                client.create_collection(
                    collection_name="JOBS",
                    vectors_config=qmodels.VectorParams(
                        size=384,  # all-MiniLM-L6-v2 dimension
                        distance=qmodels.Distance.COSINE
                    )
                )
                print("✅ JOBS collection created in Qdrant!")
            else:
                print("✅ JOBS collection already exists!")
        except Exception as e:
            print(f"⚠️ Qdrant collection creation error: {e}")