"""
Match Filters
=============
Filtering logic for refining job-candidate matches.

Author: Abdul Munaf (BSDSF22A007)
Task: 3.5 - Backend job matching API
"""

from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class JobMatchFilter:
    """
    Applies various filters to job matches based on candidate profile.
    """
    
    @staticmethod
    def filter_by_required_skills(
        matches: List[Dict],
        candidate_skills: Set[str],
        min_match_percentage: float = 50.0
    ) -> List[Dict]:
        """
        Filter jobs based on required skills match.
        
        Args:
            matches: List of job matches
            candidate_skills: Set of candidate's skills
            min_match_percentage: Minimum required skill match %
            
        Returns:
            Filtered job list
            
        TODO: Integrate with actual candidate profile from cv_manager
        """
        logger.info(f"Filtering by skills (min {min_match_percentage}%)")
        
        filtered_matches = []
        
        for match in matches:
            required_skills = set(match.get('required_skills', []))
            
            if not required_skills:
                filtered_matches.append(match)
                continue
            
            # Calculate skill match percentage
            matched_skills = candidate_skills.intersection(required_skills)
            match_percentage = (len(matched_skills) / len(required_skills)) * 100
            
            if match_percentage >= min_match_percentage:
                match['skill_match_percentage'] = match_percentage
                match['matched_skills'] = list(matched_skills)
                match['missing_skills'] = list(required_skills - candidate_skills)
                filtered_matches.append(match)
        
        return filtered_matches
    
    @staticmethod
    def filter_by_experience(
        matches: List[Dict],
        candidate_experience_years: int
    ) -> List[Dict]:
        """
        Filter jobs based on experience requirements.
        
        Args:
            matches: List of job matches
            candidate_experience_years: Candidate's years of experience
            
        Returns:
            Filtered matches
            
        TODO: Parse experience requirements properly
        Examples: "2-4 years", "5+ years", "Entry level"
        """
        logger.info(f"Filtering by experience ({candidate_experience_years} years)")
        
        filtered_matches = []
        
        for match in matches:
            exp_required = match.get('experience_required', '').lower()
            
            # Simple filtering logic (needs improvement)
            if 'entry' in exp_required or 'junior' in exp_required:
                if candidate_experience_years <= 2:
                    filtered_matches.append(match)
            elif 'senior' in exp_required or 'lead' in exp_required:
                if candidate_experience_years >= 5:
                    filtered_matches.append(match)
            else:
                # Default: include if not explicitly filtered
                filtered_matches.append(match)
        
        return filtered_matches
    
    @staticmethod
    def filter_by_location(
        matches: List[Dict],
        preferred_locations: List[str],
        include_remote: bool = True
    ) -> List[Dict]:
        """
        Filter jobs by location preference.
        
        Args:
            matches: List of job matches
            preferred_locations: Candidate's preferred locations
            include_remote: Include remote jobs
            
        Returns:
            Filtered matches
        """
        logger.info(f"Filtering by location: {preferred_locations}")
        
        filtered_matches = []
        
        for match in matches:
            job_location = match.get('location', '').lower()
            
            # Include remote jobs if enabled
            if include_remote and ('remote' in job_location or 'anywhere' in job_location):
                match['is_remote'] = True
                filtered_matches.append(match)
                continue
            
            # Check if job location matches preferences
            for pref_loc in preferred_locations:
                if pref_loc.lower() in job_location:
                    match['is_remote'] = False
                    filtered_matches.append(match)
                    break
        
        return filtered_matches
    
    @staticmethod
    def filter_by_deadline(
        matches: List[Dict],
        include_expired: bool = False
    ) -> List[Dict]:
        """
        Filter jobs based on application deadline.
        
        Args:
            matches: List of job matches
            include_expired: Include jobs with passed deadlines
            
        Returns:
            Filtered matches
            
        TODO: Implement proper datetime comparison
        """
        from datetime import datetime
        
        logger.info("Filtering by application deadline")
        
        if include_expired:
            return matches
        
        filtered_matches = []
        current_date = datetime.now()
        
        for match in matches:
            deadline = match.get('application_deadline')
            
            # If no deadline, include the job
            if not deadline:
                filtered_matches.append(match)
                continue
            
            # TODO: Convert deadline string to datetime and compare
            # For now, include all jobs
            filtered_matches.append(match)
        
        return filtered_matches
    
    @staticmethod
    def apply_all_filters(
        matches: List[Dict],
        candidate_profile: Dict,
        filter_config: Dict = None
    ) -> List[Dict]:
        """
        Apply all configured filters in sequence.
        
        Args:
            matches: Original job matches
            candidate_profile: Complete candidate profile
            filter_config: Filter configuration settings
            
        Returns:
            Fully filtered matches
            
        Example candidate_profile:
        {
            'skills': ['Python', 'Django', 'React'],
            'experience_years': 3,
            'preferred_locations': ['Lahore', 'Islamabad'],
            'include_remote': True
        }
        """
        if filter_config is None:
            filter_config = {
                'min_skill_match': 50.0,
                'filter_by_experience': True,
                'filter_by_location': True,
                'include_expired_jobs': False
            }
        
        logger.info("Applying all filters")
        
        filtered = matches
        
        # Apply skill filter
        if 'skills' in candidate_profile:
            filtered = JobMatchFilter.filter_by_required_skills(
                filtered,
                set(candidate_profile['skills']),
                filter_config.get('min_skill_match', 50.0)
            )
        
        # Apply experience filter
        if filter_config.get('filter_by_experience') and 'experience_years' in candidate_profile:
            filtered = JobMatchFilter.filter_by_experience(
                filtered,
                candidate_profile['experience_years']
            )
        
        # Apply location filter
        if filter_config.get('filter_by_location') and 'preferred_locations' in candidate_profile:
            filtered = JobMatchFilter.filter_by_location(
                filtered,
                candidate_profile['preferred_locations'],
                candidate_profile.get('include_remote', True)
            )
        
        # Apply deadline filter
        filtered = JobMatchFilter.filter_by_deadline(
            filtered,
            filter_config.get('include_expired_jobs', False)
        )
        
        logger.info(f"Filters applied: {len(matches)} -> {len(filtered)} matches")
        
        return filtered