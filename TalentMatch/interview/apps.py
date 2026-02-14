# interviews/apps.py
from django.apps import AppConfig

class InterviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'interview'
    
    def ready(self):
        # Import signals
        # import interview.signals
        # Import error handlers
        import interview.middleware
        # Import services
        import interview.services.interview_service
        import interview.services.evaluation_service
        
        # Initialize default data
        self.initialize_default_data()
    
    def initialize_default_data(self):
        """Initialize default interview categories and question types"""
        from django.db.utils import ProgrammingError
        from .models import QuestionType, InterviewCategory
        
        try:
            # Create default question types
            default_types = [
                ('MCQ', 'Multiple Choice', True),
                ('DESC', 'Descriptive', True),
                ('CODE', 'Coding Problem', True),
                ('CASE', 'Case Study', True),
                ('BEHAV', 'Behavioral', True),
            ]
            
            for code, name, requires_key in default_types:
                QuestionType.objects.get_or_create(
                    code=code,
                    defaults={'name': name, 'requires_answer_key': requires_key}
                )
            
            # Create default categories (if none exist)
            if not InterviewCategory.objects.exists():
                default_categories = [
                    ('Technical', 'Programming, algorithms, system design'),
                    ('Behavioral', 'Soft skills, teamwork, communication'),
                    ('System Design', 'Architecture, scalability, design patterns'),
                    ('Problem Solving', 'Analytical thinking, algorithms'),
                    ('Domain Knowledge', 'Industry-specific knowledge'),
                    ('Leadership', 'Management, decision-making'),
                ]
                
                from accounts.models import User
                admin = User.objects.filter(is_superuser=True).first()
                
                if admin:
                    for name, description in default_categories:
                        InterviewCategory.objects.create(
                            name=name,
                            description=description,
                            created_by=admin
                        )
        
        except ProgrammingError:
            # Database tables don't exist yet (during migration)
            pass