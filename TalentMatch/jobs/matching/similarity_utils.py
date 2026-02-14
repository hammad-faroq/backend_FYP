"""
Similarity Calculation Utilities
=================================
Helper functions for calculating similarity scores between embeddings.

Author: Abdul Munaf (BSDSF22A007)
Task: 3.5 - Backend job matching API
"""

import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vector_a: First embedding vector
        vector_b: Second embedding vector
        
    Returns:
        Similarity score between -1 and 1
        
    Formula: cos(θ) = (A · B) / (||A|| × ||B||)
    """
    try:
        vec_a = np.array(vector_a)
        vec_b = np.array(vector_b)
        
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        similarity = dot_product / (norm_a * norm_b)
        return float(similarity)
        
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {str(e)}")
        return 0.0


def normalize_score(score: float, min_val: float = -1, max_val: float = 1) -> float:
    """
    Normalize similarity score to 0-100 range.
    
    Args:
        score: Raw similarity score
        min_val: Minimum possible value
        max_val: Maximum possible value
        
    Returns:
        Normalized score (0-100)
    """
    try:
        normalized = ((score - min_val) / (max_val - min_val)) * 100
        return max(0, min(100, normalized))
    except Exception as e:
        logger.error(f"Error normalizing score: {str(e)}")
        return 0.0


def euclidean_distance(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Calculate Euclidean distance between two vectors.
    
    Args:
        vector_a: First embedding vector
        vector_b: Second embedding vector
        
    Returns:
        Distance value (lower means more similar)
    """
    try:
        vec_a = np.array(vector_a)
        vec_b = np.array(vector_b)
        
        distance = np.linalg.norm(vec_a - vec_b)
        return float(distance)
        
    except Exception as e:
        logger.error(f"Error calculating Euclidean distance: {str(e)}")
        return float('inf')


def calculate_weighted_similarity(
    embeddings_similarity: float,
    skill_match_score: float,
    experience_match_score: float,
    weights: dict = None
) -> float:
    """
    Calculate weighted similarity score considering multiple factors.
    
    Args:
        embeddings_similarity: Semantic similarity score
        skill_match_score: Skill matching score
        experience_match_score: Experience matching score
        weights: Dictionary of weights for each factor
        
    Returns:
        Weighted combined score (0-100)
    """
    if weights is None:
        weights = {
            'embeddings': 0.5,
            'skills': 0.3,
            'experience': 0.2
        }
    
    try:
        weighted_score = (
            embeddings_similarity * weights['embeddings'] +
            skill_match_score * weights['skills'] +
            experience_match_score * weights['experience']
        )
        
        return max(0, min(100, weighted_score))
        
    except Exception as e:
        logger.error(f"Error calculating weighted similarity: {str(e)}")
        return 0.0


def batch_cosine_similarity(
    query_vector: List[float],
    candidate_vectors: List[List[float]]
) -> List[float]:
    """
    Calculate cosine similarity between one query and multiple candidates.
    
    Args:
        query_vector: Single query embedding
        candidate_vectors: List of candidate embeddings
        
    Returns:
        List of similarity scores
    """
    try:
        query = np.array(query_vector)
        candidates = np.array(candidate_vectors)
        
        # Normalize query vector
        query_norm = query / np.linalg.norm(query)
        
        # Normalize candidate vectors
        candidates_norm = candidates / np.linalg.norm(candidates, axis=1, keepdims=True)
        
        # Calculate dot products
        similarities = np.dot(candidates_norm, query_norm)
        
        return similarities.tolist()
        
    except Exception as e:
        logger.error(f"Error in batch cosine similarity: {str(e)}")
        return [0.0] * len(candidate_vectors)