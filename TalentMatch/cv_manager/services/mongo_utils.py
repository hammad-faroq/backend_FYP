from pymongo import MongoClient
from django.conf import settings
import datetime
import logging

logger = logging.getLogger(__name__)

# Example: configure MongoDB URI in settings.py
# MONGO_URI = "mongodb://localhost:27017"
# MONGO_DB_NAME = "resume_db"

def get_mongo_client():
    return MongoClient(settings.MONGO_URI)

def store_parsed_resume_mongo(user_id, uploaded_resume_id, resume_text, metadata=None):
    """
    Store parsed resume text into MongoDB.
    """
    try:
        client = get_mongo_client()
        db = client[settings.MONGO_DB_NAME]
        collection = db["parsed_resumes"]

        document = {
            "user_id": user_id,
            "uploaded_resume_id": uploaded_resume_id,
            "resume_text": resume_text,
            "metadata": metadata or {},
            "stored_at": datetime.datetime.utcnow()
        }

        result = collection.insert_one(document)
        logger.info(f"Resume stored in MongoDB with id: {result.inserted_id}")
        return str(result.inserted_id)

    except Exception as e:
        logger.error(f"Failed to store resume in MongoDB: {e}")
        return None
