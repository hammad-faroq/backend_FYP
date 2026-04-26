"""
Unit Tests for Job Matching Module
===================================
Test cases for job recommendation and matching logic.

Author: Abdul Munaf (BSDSF22A007)
Task: 3.5 - Backend job matching API
"""

from django.test import TestCase
from jobs.matching.similarity_utils import (
    cosine_similarity,
    normalize_score,
    calculate_weighted_similarity
)
from jobs.matching.match_filters import JobMatchFilter
from jobs.matching.ranking_engine import JobRankingEngine


class SimilarityUtilsTestCase(TestCase):
    """Test cases for similarity calculation utilities."""
    
    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity with identical vectors."""
        vec_a = [1.0, 2.0, 3.0]
        vec_b = [1.0, 2.0, 3.0]
        
        similarity = cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(similarity, 1.0, places=5)
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity with orthogonal vectors."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        
        similarity = cosine_similarity(vec_a, vec_b)
        self.assertAlmostEqual(similarity, 0.0, places=5)
    
    def test_normalize_score(self):
        """Test score normalization to 0-100 range."""
        score = normalize_score(0.5, min_val=-1, max_val=1)
        self.assertAlmostEqual(score, 75.0, places=1)
    
    def test_weighted_similarity_calculation(self):
        """Test weighted similarity with multiple factors."""
        result = calculate_weighted_similarity(
            embeddings_similarity=80.0,
            skill_match_score=70.0,
            experience_match_score=60.0
        )
        
        # Should be between 60 and 80
        self.assertGreaterEqual(result, 60.0)
        self.assertLessEqual(result, 80.0)


class MatchFilterTestCase(TestCase):
    """Test cases for job match filtering."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_matches = [
            {
                'job_id': 1,
                'job_title': 'Python Developer',
                'required_skills': ['Python', 'Django', 'PostgreSQL'],
                'experience_required': 'Mid-level (2-4 years)',
                'location': 'Lahore, Pakistan',
                'application_deadline': None
            },
        ]