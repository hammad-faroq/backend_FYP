from django.conf import settings
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


# ============================================
# SENTENCE TRANSFORMER (Singleton)
# ============================================
_sentence_transformer = None

def get_sentence_transformer():
    """
    Lazy-loaded singleton SentenceTransformer model.
    Loads 'all-MiniLM-L6-v2' once and reuses across entire application.
    """
    global _sentence_transformer
    if _sentence_transformer is None:
        _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ SentenceTransformer model loaded (all-MiniLM-L6-v2)")
    return _sentence_transformer