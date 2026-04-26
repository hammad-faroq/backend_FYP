from django.conf import settings
from qdrant_client import QdrantClient
import logging

logger = logging.getLogger(__name__)

_qdrant_client = None

def get_qdrant_client():
    """
    Lazy-loaded singleton Qdrant client.
    Reuses the same connection across the entire application.
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        logger.info("✅ Qdrant client connected")
    return _qdrant_client