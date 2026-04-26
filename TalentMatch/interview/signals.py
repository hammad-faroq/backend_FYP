# interview/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def initialize_default_data(sender, **kwargs):
    from django.db.utils import ProgrammingError
    from .models import QuestionType, InterviewCategory

    try:
        # Default question types
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
                defaults={
                    'name': name,
                    'requires_answer_key': requires_key
                }
            )

        # Default categories
        if not InterviewCategory.objects.exists():
            default_categories = [
                ('Technical', 'Programming, algorithms, system design'),
                ('Behavioral', 'Soft skills, teamwork, communication'),
                ('System Design', 'Architecture, scalability'),
                ('Problem Solving', 'Analytical thinking'),
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

        print("✅ Default interview data initialized")

    except ProgrammingError:
        pass