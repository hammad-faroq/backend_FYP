# interviews/security.py
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from interview.middleware import AnswerAlreadySubmitted, InterviewExpired, InterviewNotStarted
from .models import Interview, CandidateAnswer

class InterviewSecurity:
    """Security checks for interview system"""
    
    @staticmethod
    def check_hr_access(hr_user, interview):
        """Verify HR has access to interview"""
        if hr_user != interview.hr_user:
            raise PermissionDenied("You are not the HR for this interview")
        return True
    
    @staticmethod
    def check_candidate_access(candidate, interview):
        """Verify candidate has access to interview"""
        if candidate != interview.candidate:
            raise PermissionDenied("You are not the candidate for this interview")
        return True
    
    @staticmethod
    def check_interview_in_progress(interview):
        """Verify interview is in progress"""
        if interview.status != 'in_progress':
            raise InterviewNotStarted("Interview is not in progress")
        
        # Check time limits
        if interview.started_at:
            elapsed = timezone.now() - interview.started_at
            if elapsed.total_seconds() > (interview.duration_minutes * 60):
                raise InterviewExpired("Interview time has expired")
        
        return True
    
    @staticmethod
    def check_answer_not_submitted(answer):
        """Verify answer hasn't been submitted"""
        if answer.is_submitted:
            raise AnswerAlreadySubmitted("Answer already submitted")
        return True
    
    @staticmethod
    def sanitize_answer_data(answer_data, question_type):
        """Sanitize answer data to prevent XSS and other attacks"""
        import html
        
        sanitized = answer_data.copy()
        
        if 'answer_text' in sanitized:
            # Escape HTML but preserve line breaks
            text = sanitized['answer_text']
            text = html.escape(text)
            text = text.replace('\n', '<br>')
            sanitized['answer_text'] = text
        
        if 'code_snippet' in sanitized:
            # For code, remove dangerous patterns
            code = sanitized['code_snippet']
            dangerous_patterns = [
                r'<script.*?>.*?</script>',
                r'on\w+=".*?"',
                r'javascript:',
                r'data:text/html',
            ]
            
            import re
            for pattern in dangerous_patterns:
                code = re.sub(pattern, '[REMOVED]', code, flags=re.IGNORECASE)
            
            sanitized['code_snippet'] = code
        
        return sanitized
    
    @staticmethod
    def mask_hr_answers_for_candidate(questions_data):
        """Remove HR answers from questions sent to candidate"""
        masked = []
        for question in questions_data:
            masked_question = question.copy()
            
            # Remove HR answers and notes
            masked_question.pop('hr_answer', None)
            masked_question.pop('hr_answer_notes', None)
            
            # For MCQ, remove is_correct flags but keep options
            if 'options' in masked_question:
                for option in masked_question['options']:
                    option.pop('is_correct', None)
            
            masked.append(masked_question)
        
        return masked