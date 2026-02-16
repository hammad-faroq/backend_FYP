import os
import joblib
import numpy as np
from django.conf import settings
from .analyzer import extract_text_from_resume
import logging

logger = logging.getLogger(__name__)

# ------------------------------
# Lazy-loaded models with error handling
# ------------------------------
_resume_ranker_model = None
_embedding_model = None
_model_load_attempted = False


def get_resume_ranker_model():
    """
    Lazy load the resume ranker model with error handling
    Returns None if model fails to load
    """
    global _resume_ranker_model, _model_load_attempted
    
    if _model_load_attempted and _resume_ranker_model is None:
        return None  # Already tried and failed
    
    if _resume_ranker_model is None:
        _model_load_attempted = True
        try:
            if not os.path.exists(settings.RESUME_RANKER_MODEL_PATH):
                logger.warning(f"⚠️ Model not found at: {settings.RESUME_RANKER_MODEL_PATH}")
                return None
            
            _resume_ranker_model = joblib.load(settings.RESUME_RANKER_MODEL_PATH)
            logger.info("✅ Resume ranker model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load resume ranker model: {e}")
            _resume_ranker_model = None
    
    return _resume_ranker_model


def get_embedding_model():
    """
    Lazy load the embedding model with error handling
    Falls back to sentence-transformers if pickle fails
    """
    global _embedding_model
    
    if _embedding_model is not None:
        return _embedding_model
    
    # Try loading from pickle first
    try:
        if os.path.exists(settings.EMBEDDING_MODEL_PATH):
            _embedding_model = joblib.load(settings.EMBEDDING_MODEL_PATH)
            logger.info("✅ Embedding model loaded from pickle")
            return _embedding_model
    except Exception as e:
        logger.warning(f"⚠️ Failed to load embedding model from pickle: {e}")
    
    # Fallback: Load sentence-transformers directly
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("📦 Loading sentence-transformers model as fallback...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Sentence-transformers model loaded successfully")
        return _embedding_model
    except Exception as fallback_error:
        logger.error(f"❌ Fallback sentence-transformers also failed: {fallback_error}")
        _embedding_model = None
    
    return _embedding_model


# ------------------------------
# Predict score
# ------------------------------
def predict_resume_score(resume_path, job_description):
    """
    Predict resume score for a given job description
    Returns a default score if models are unavailable
    """
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text.strip():
        logger.warning("⚠️ Empty resume text")
        return 0.0

    logger.info(f"📄 Extracted resume length: {len(resume_text)} chars")

    # Get models (with fallback handling)
    embedding_model = get_embedding_model()
    ranker_model = get_resume_ranker_model()
    
    # If embedding model failed, return default score
    if embedding_model is None:
        logger.warning("⚠️ Embedding model unavailable, returning default score")
        return 50.0  # Default middle score
    
    try:
        # Embed resume
        resume_vec = embedding_model.encode([resume_text])[0]  # 384 dims
        features = resume_vec.reshape(1, -1)
        
        # If ranker model is available, use it
        if ranker_model is not None:
            score = ranker_model.predict(features)[0]
            # Convert to percentage if model predicts 0–1
            score_pct = float(score) * 100
            logger.info(f"🤖 Custom ML raw score: {score}, scaled: {score_pct}")
            return round(score_pct, 2)
        else:
            # Fallback: Use simple text similarity
            logger.warning("⚠️ Ranker model unavailable, using basic similarity")
            from sklearn.metrics.pairwise import cosine_similarity
            
            job_vec = embedding_model.encode([job_description])[0]
            similarity = cosine_similarity([resume_vec], [job_vec])[0][0]
            score_pct = float(similarity) * 100
            logger.info(f"📊 Similarity score: {score_pct}")
            return round(score_pct, 2)
            
    except Exception as e:
        logger.error(f"❌ Error during prediction: {e}")
        return 50.0  # Default score on error


# ------------------------------
# Initialize models on import (optional)
# ------------------------------
# Uncomment below if you want to load models at startup
# But this might cause the KeyError 118 during deployment
# get_embedding_model()
# get_resume_ranker_model()