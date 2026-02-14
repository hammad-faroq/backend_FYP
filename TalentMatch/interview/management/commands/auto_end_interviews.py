# interviews/management/commands/auto_end_interviews.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from interview.models import Interview
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Auto-end interviews that have exceeded their duration'

    def handle(self, *args, **options):
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
                
                # Send email notification
                self.send_notification(interview)
                
                ended_count += 1
            
            if ended_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Auto-ended {ended_count} interview(s)')
                )
            else:
                self.stdout.write('No interviews to auto-end')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
    
    def send_notification(self, interview):
        """Send email notification when interview is auto-ended"""
        try:
            subject = f"Interview Auto-Completed: {interview.title}"
            message = f"""
            Dear HR Manager,
            
            The interview has been automatically completed due to time limit.
            
            Interview Details:
            - Title: {interview.title}
            - Interview ID: {interview.id}
            - Candidate: {interview.candidate.email}
            - Completed At: {interview.completed_at}
            
            Please review the candidate's answers when convenient.
            
            Best regards,
            Interview Platform
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[interview.hr_user.email],
                fail_silently=True,
            )
            
        except Exception as e:
            self.stdout.write(f"Failed to send notification: {str(e)}")