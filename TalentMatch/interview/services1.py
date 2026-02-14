from django.utils import timezone
from .models import CandidateAnswer, InterviewResult

def calculate_interview_result(interview, candidate, hr_user):
    answers = CandidateAnswer.objects.filter(
        question_set__interview=interview,
        candidate=candidate,
        is_submitted=True
    ).select_related(
        'question_set__question',
        'question_set__question__category'
    )

    total_score = 0
    max_score = 0
    category_scores = {}

    for answer in answers:
        question = answer.question_set.question
        category = question.category.name if question.category else "General"

        score = answer.hr_score if answer.hr_score is not None else answer.auto_score
        if score is None:
            continue

        total_score += score
        max_score += question.points

        category_scores.setdefault(category, {"score": 0, "max": 0})
        category_scores[category]["score"] += score
        category_scores[category]["max"] += question.points

    percentage = (total_score / max_score * 100) if max_score else 0

    performance = (
        "Excellent" if percentage >= 80 else
        "Good" if percentage >= 60 else
        "Fair" if percentage >= 40 else
        "Needs Improvement"
    )

    result, _ = InterviewResult.objects.update_or_create(
        interview=interview,
        candidate=candidate,
        defaults={
            "total_score": total_score,
            "max_score": max_score,
            "percentage": round(percentage, 2),
            "category_breakdown": category_scores,
            "performance_level": performance,
            "finalized": True,
            "finalized_at": timezone.now(),
            "finalized_by": hr_user,
        }
    )

    return result
