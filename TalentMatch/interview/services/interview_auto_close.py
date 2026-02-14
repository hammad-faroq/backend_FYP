# interviews/services/interview_auto_close.py

from django.utils import timezone
from interview.models import Interview, CandidateAnswer, InterviewResult

def auto_close_interview(interview):
    if interview.status != "in_progress":
        return None

    if not interview.has_time_expired():
        return None

    answers = CandidateAnswer.objects.filter(
        question_set__interview=interview
    ).select_related("question_set__question")

    total_score = 0
    max_score = 0

    for answer in answers:
        question = answer.question_set.question
        points = question.points or 10
        max_score += points

        # Auto score if not already done
        if answer.auto_score is None:
            answer.auto_score = answer.calculate_auto_score()
            answer.submitted_at = answer.submitted_at or timezone.now()
            answer.is_submitted = True
            answer.save(update_fields=[
                "auto_score", "submitted_at", "is_submitted"
            ])

        score = answer.hr_score if answer.hr_score is not None else (answer.auto_score or 0)
        total_score += score

    percentage = round((total_score / max_score * 100), 2) if max_score else 0

    result, _ = InterviewResult.objects.update_or_create(
        interview=interview,
        candidate=interview.candidate,
        defaults={
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage,
            "finalized": True,
            "finalized_at": timezone.now(),
            "performance_level": _performance_level(percentage),
        }
    )

    interview.status = "completed"
    interview.completed_at = timezone.now()
    interview.save(update_fields=["status", "completed_at"])

    return result


def _performance_level(p):
    if p >= 90:
        return "Excellent"
    if p >= 80:
        return "Very Good"
    if p >= 70:
        return "Good"
    if p >= 60:
        return "Average"
    if p >= 50:
        return "Below Average"
    return "Poor"
