"""
Job Matching Module
===================
This module handles semantic job-candidate matching using vector embeddings.

Components:
- embeddings.py: Sentence-BERT model for generating embeddings (Task 3.4)
- recommender.py: Job recommendation engine (Task 3.5)

Author: Abdul Munaf (BSDSF22A007)
Sprint: 3 - Job Posting & Semantic Job Matching
Task: 3.5 - Backend job matching API
"""

from .recommender import JobRecommender

__all__ = ['JobRecommender']