# interviews/tasks.py
from talentmatch_ai.celery import shared_task
from django.utils import timezone
from .models import Interview, CandidateAnswer
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def auto_end_interviews():
    """Celery task to auto-end interviews that have exceeded duration"""
    try:
        interviews_to_end = Interview.objects.filter(
            status='in_progress',
            auto_end_at__lte=timezone.now()
        )
        
        ended_count = 0
        
        for interview in interviews_to_end:
            # Update interview status
            interview.status = 'completed'
            interview.completed_at = interview.auto_end_at
            interview.is_auto_ended = True
            interview.save()
            
            # Count answers submitted
            submitted_answers = CandidateAnswer.objects.filter(
                question_set__interview=interview,
                is_submitted=True
            ).count()
            
            # Send notification email to HR
            send_auto_end_notification.delay(
                interview_id=str(interview.id),
                hr_email=interview.hr_user.email,
                candidate_email=interview.candidate.email,
                interview_title=interview.title,
                submitted_answers=submitted_answers
            )
            
            ended_count += 1
        
        return f"Auto-ended {ended_count} interview(s)"
    
    except Exception as e:
        return f"Error in auto_end_interviews: {str(e)}"

@shared_task
def cleanup_old_interviews():
    """Cleanup completed interviews older than 90 days"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        old_interviews = Interview.objects.filter(
            status='completed',
            completed_at__lte=cutoff_date
        )
        
        deleted_count = old_interviews.count()
        old_interviews.delete()
        
        return f"Cleaned up {deleted_count} old interviews"
    
    except Exception as e:
        return f"Error in cleanup_old_interviews: {str(e)}"

@shared_task
def send_auto_end_notification(interview_id, hr_email, candidate_email, interview_title, submitted_answers):
    """Send email notification when interview is auto-ended"""
    try:
        subject = f"Interview Auto-Completed: {interview_title}"
        message = f"""
        Dear HR Manager,
        
        The interview has been automatically completed due to time limit.
        
        Interview Details:
        - Title: {interview_title}
        - Interview ID: {interview_id}
        - Candidate: {candidate_email}
        - Answers Submitted: {submitted_answers}
        - Completed At: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Please review the candidate's answers when convenient.
        
        Best regards,
        Interview Platform
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[hr_email],
            fail_silently=False,
        )
        
        return f"Auto-end notification sent to {hr_email}"
    
    except Exception as e:
        return f"Error sending notification: {str(e)}"