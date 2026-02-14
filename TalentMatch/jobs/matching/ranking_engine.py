"""
Ranking Engine
==============
Advanced ranking logic for job recommendations.

Author: Abdul Munaf (BSDSF22A007)
Task: 3.5 - Backend job matching API
"""

from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class JobRankingEngine:
    """
    Ranks job matches using multiple criteria and weighted scoring.
    """
    
    DEFAULT_WEIGHTS = {
        'similarity_score': 0.40,      # Semantic similarity
        'skill_match': 0.25,            # Skill match percentage
        'experience_match': 0.15,       # Experience alignment
        'recency': 0.10,                # How recent the posting is
        'deadline_proximity': 0.10      # Time until deadline
    }
    
    def __init__(self, weights: Dict = None):
        """
        Initialize ranking engine with custom weights.
        
        Args:
            weights: Custom weight configuration
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        logger.info(f"JobRankingEngine initialized with weights: {self.weights}")
    
    def calculate_composite_score(self, match: Dict) -> float:
        """
        Calculate weighted composite score for a job match.
        
        Args:
            match: Job match dictionary with various scores
            
        Returns:
            Composite score (0-100)
        """
        try:
            # Extract individual scores
            similarity = match.get('similarity_score', 0)
            skill_match = match.get('skill_match_percentage', 0)
            experience = self._calculate_experience_score(match)
            recency = self._calculate_recency_score(match)
            deadline = self._calculate_deadline_score(match)
            
            # Calculate weighted sum
            composite = (
                similarity * self.weights['similarity_score'] +
                skill_match * self.weights['skill_match'] +
                experience * self.weights['experience_match'] +
                recency * self.weights['recency'] +
                deadline * self.weights['deadline_proximity']
            )
            
            return min(100, max(0, composite))
            
        except Exception as e:
            logger.error(f"Error calculating composite score: {str(e)}")
            return 0.0
    
    def _calculate_experience_score(self, match: Dict) -> float:
        """
        Calculate experience match score.
        
        Args:
            match: Job match with experience data
            
        Returns:
            Score (0-100)
            
        TODO: Implement proper experience comparison
        """
        # Placeholder logic
        exp_match = match.get('experience_match_score', 50.0)
        return exp_match
    
    def _calculate_recency_score(self, match: Dict) -> float:
        """
        Calculate score based on posting recency.
        
        Args:
            match: Job match with posted_date
            
        Returns:
            Score (0-100) - higher for more recent postings
            
        TODO: Implement datetime comparison
        """
        posted_date = match.get('posted_date')
        
        if not posted_date:
            return 50.0  # Neutral score if no date
        
        # TODO: Calculate days since posting
        # More recent = higher score
        # Example: 0-7 days = 100, 8-30 days = 75, 31+ days = 50
        
        return 75.0  # Placeholder
    
    def _calculate_deadline_score(self, match: Dict) -> float:
        """
        Calculate score based on deadline proximity.
        
        Args:
            match: Job match with application_deadline
            
        Returns:
            Score (0-100) - higher for deadlines further away
            
        TODO: Implement deadline calculation
        """
        deadline = match.get('application_deadline')
        
        if not deadline:
            return 100.0  # No deadline = maximum time
        
        # TODO: Calculate days until deadline
        # More time = higher score
        # Example: 30+ days = 100, 15-29 days = 75, 7-14 days = 50, <7 days = 25
        
        return 75.0  # Placeholder
    
    def rank_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Rank all job matches by composite score.
        
        Args:
            matches: List of job matches
            
        Returns:
            Sorted list (highest score first)
        """
        logger.info(f"Ranking {len(matches)} job matches")
        
        # Calculate composite score for each match
        for match in matches:
            match['composite_score'] = self.calculate_composite_score(match)
        
        # Sort by composite score (descending)
        ranked = sorted(
            matches,
            key=lambda x: x.get('composite_score', 0),
            reverse=True
        )
        
        # Add rank position
        for idx, match in enumerate(ranked, 1):
            match['rank'] = idx
        
        logger.info(f"Ranking complete. Top score: {ranked[0].get('composite_score', 0):.2f}")
        
        return ranked
    
    def get_top_n_matches(
        self,
        matches: List[Dict],
        n: int = 10
    ) -> List[Dict]:
        """
        Get top N ranked matches.
        
        Args:
            matches: List of job matches
            n: Number of top matches to return
            
        Returns:
            Top N matches
        """
        ranked_matches = self.rank_matches(matches)
        return ranked_matches[:n]
    
    def add_match_insights(self, match: Dict) -> Dict:
        """
        Add human-readable insights to a match.
        
        Args:
            match: Job match dictionary
            
        Returns:
            Match with added insights
        """
        insights = []
        
        # Similarity insight
        sim_score = match.get('similarity_score', 0)
        if sim_score >= 80:
            insights.append("Excellent match based on your profile")
        elif sim_score >= 60:
            insights.append("Good match for your skills")
        else:
            insights.append("Potential opportunity to explore new areas")
        
        # Skill match insight
        skill_match = match.get('skill_match_percentage', 0)
        if skill_match >= 75:
            insights.append("You have most required skills")
        elif skill_match >= 50:
            insights.append("You meet many skill requirements")
        else:
            missing = len(match.get('missing_skills', []))
            if missing > 0:
                insights.append(f"Consider learning {missing} additional skills")
        
        # Deadline insight
        deadline = match.get('application_deadline')
        if deadline:
            insights.append("Application deadline applies - apply soon!")
        
        match['insights'] = insights
        return match
    
    def generate_ranking_report(self, matches: List[Dict]) -> Dict:
        """
        Generate a summary report of the ranking results.
        
        Args:
            matches: Ranked job matches
            
        Returns:
            Report dictionary
        """
        if not matches:
            return {
                'total_matches': 0,
                'message': 'No matches found'
            }
        
        ranked = self.rank_matches(matches)
        
        report = {
            'total_matches': len(ranked),
            'top_score': ranked[0].get('composite_score', 0),
            'average_score': sum(m.get('composite_score', 0) for m in ranked) / len(ranked),
            'excellent_matches': len([m for m in ranked if m.get('composite_score', 0) >= 80]),
            'good_matches': len([m for m in ranked if 60 <= m.get('composite_score', 0) < 80]),
            'fair_matches': len([m for m in ranked if m.get('composite_score', 0) < 60]),
            'top_3_jobs': [
                {
                    'title': m.get('job_title'),
                    'score': m.get('composite_score'),
                    'rank': m.get('rank')
                }
                for m in ranked[:3]
            ]
        }
        
        return report