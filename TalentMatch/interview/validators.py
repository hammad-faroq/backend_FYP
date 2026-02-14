# interviews/validators.py
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

class InterviewValidator:
    """Validation rules for interview system"""
    
    @staticmethod
    def validate_question_data(question_data):
        """Validate question creation/update data"""
        errors = {}
        
        # Required fields
        required_fields = ['question_text', 'question_type', 'category_id', 'difficulty']
        for field in required_fields:
            if not question_data.get(field):
                errors[field] = f"{field.replace('_', ' ').title()} is required"
        
        # Question text validation
        question_text = question_data.get('question_text', '').strip()
        if len(question_text) < 10:
            errors['question_text'] = "Question must be at least 10 characters"
        if len(question_text) > 2000:
            errors['question_text'] = "Question cannot exceed 2000 characters"
        
        # MCQ validation
        if question_data.get('question_type') == 'MCQ':
            options = question_data.get('options', [])
            if len(options) < 2:
                errors['options'] = "MCQ must have at least 2 options"
            else:
                correct_options = sum(1 for opt in options if opt.get('is_correct', False))
                if correct_options == 0:
                    errors['options'] = "At least one option must be marked correct"
        
        # HR answer validation for non-MCQ
        if question_data.get('question_type') != 'MCQ' and not question_data.get('hr_answer'):
            errors['hr_answer'] = "HR answer is required for non-MCQ questions"
        
        if errors:
            raise ValidationError(errors)
        
        return True
    
    @staticmethod
    def validate_interview_schedule(scheduled_date, duration_minutes, hr_user, candidate):
        """Validate interview scheduling"""
        errors = {}
        
        # Date validation
        if scheduled_date < timezone.now() + timezone.timedelta(hours=1):
            errors['scheduled_date'] = "Interview must be scheduled at least 1 hour in advance"
        
        if scheduled_date > timezone.now() + timezone.timedelta(days=30):
            errors['scheduled_date'] = "Interview cannot be scheduled more than 30 days in advance"
        
        # Duration validation
        if duration_minutes < 15:
            errors['duration_minutes'] = "Interview must be at least 15 minutes"
        if duration_minutes > 240:
            errors['duration_minutes'] = "Interview cannot exceed 4 hours"
        
        # Participant validation
        if hr_user == candidate:
            errors['participants'] = "HR and candidate cannot be the same user"
        
        # Business hours validation (9 AM - 6 PM)
        hour = scheduled_date.hour
        if hour < 9 or hour >= 18:
            errors['scheduled_date'] = "Interviews should be scheduled between 9 AM and 6 PM"
        
        # Check for existing interviews at same time
        from .models import Interview
        end_time = scheduled_date + timezone.timedelta(minutes=duration_minutes)
        
        hr_conflicts = Interview.objects.filter(
            hr_user=hr_user,
            scheduled_date__lt=end_time,
            scheduled_date__gt=scheduled_date - timezone.timedelta(hours=1),
            status__in=['scheduled', 'in_progress']
        ).exists()
        
        if hr_conflicts:
            errors['hr_user'] = "HR has another interview scheduled around this time"
        
        candidate_conflicts = Interview.objects.filter(
            candidate=candidate,
            scheduled_date__lt=end_time,
            scheduled_date__gt=scheduled_date - timezone.timedelta(hours=1),
            status__in=['scheduled', 'in_progress']
        ).exists()
        
        if candidate_conflicts:
            errors['candidate'] = "Candidate has another interview scheduled around this time"
        
        if errors:
            raise ValidationError(errors)
        
        return True
    
    @staticmethod
    def validate_interview_questions(interview_id):
        """Validate interview has all required questions"""
        from .models import Interview, InterviewQuestionSet
        
        try:
            interview = Interview.objects.get(id=interview_id)
        except Interview.DoesNotExist:
            raise ValidationError("Interview not found")
        
        # Check minimum questions
        total_questions = interview.question_sets.count()
        if total_questions == 0:
            raise ValidationError("Interview must have at least one question")
        
        # Check per-category questions
        categories = interview.categories.all()
        for category in categories:
            category_questions = interview.question_sets.filter(
                question__category=category
            ).count()
            
            if category_questions == 0:
                raise ValidationError(f"No questions for category: {category.name}")
        
        # Check time allocation
        total_time = sum(
            qs.question.time_limit_minutes 
            for qs in interview.question_sets.all()
        )
        
        if total_time > interview.duration_minutes:
            raise ValidationError(
                f"Total question time ({total_time}min) exceeds interview duration ({interview.duration_minutes}min)"
            )
        
        return True
    
    @staticmethod
    def validate_candidate_answer(answer_data, question_type):
        """Validate candidate answer submission"""
        errors = {}
        
        if question_type == 'MCQ':
            selected_options = answer_data.get('selected_options', [])
            if not isinstance(selected_options, list):
                errors['selected_options'] = "Selected options must be a list"
            elif len(selected_options) == 0:
                errors['selected_options'] = "At least one option must be selected"
        
        elif question_type == 'DESC':
            answer_text = answer_data.get('answer_text', '').strip()
            if len(answer_text) < 10:
                errors['answer_text'] = "Answer must be at least 10 characters"
            if len(answer_text) > 5000:
                errors['answer_text'] = "Answer cannot exceed 5000 characters"
        
        elif question_type == 'CODE':
            code_snippet = answer_data.get('code_snippet', '').strip()
            if len(code_snippet) < 5:
                errors['code_snippet'] = "Code snippet must be at least 5 characters"
            if len(code_snippet) > 10000:
                errors['code_snippet'] = "Code snippet cannot exceed 10000 characters"
            
            # Check for malicious code patterns
            dangerous_patterns = [
                r'import\s+os',
                r'import\s+subprocess',
                r'__import__',
                r'eval\(',
                r'exec\(',
                r'open\(',
                r'rm\s+-rf',
                r'delete\s+from',
                r'drop\s+table',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, code_snippet, re.IGNORECASE):
                    errors['code_snippet'] = "Code contains potentially dangerous operations"
                    break
        
        if errors:
            raise ValidationError(errors)
        
        return True