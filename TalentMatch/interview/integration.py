# interviews/integration.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

@receiver(post_save, sender='jobs.JobApplication')
def create_interview_on_shortlist(sender, instance, created, **kwargs):
    """
    When HR shortlists a candidate (updates rank_score), 
    optionally create an interview draft
    """
    if not created and instance.rank_score >= 70:  # Shortlist threshold
        # Check if interview already exists
        from .models import Interview
        existing = Interview.objects.filter(
            job=instance.job,
            candidate=instance.applicant,
            status__in=['draft', 'scheduled']
        ).exists()
        
        if not existing:
            # Create draft interview
            Interview.objects.create(
                job=instance.job,
                hr_user=instance.job.created_by,
                candidate=instance.applicant,
                title=f"Draft: Interview for {instance.job.title}",
                status='draft',
                scheduled_date=timezone.now() + timezone.timedelta(days=3)
            )

@receiver(m2m_changed, sender='interviews.Interview.categories.through')
def update_preparation_modules(sender, instance, action, **kwargs):
    """
    When interview categories are updated, 
    update candidate's preparation recommendations
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Invalidate preparation cache for this candidate
        from django.core.cache import cache
        cache_key = f"preparation_recommendations_{instance.candidate.id}"
        cache.delete(cache_key)

@receiver(post_save, sender='interviews.Interview')
def notify_on_interview_status_change(sender, instance, created, **kwargs):
    """
    Send notifications on interview status changes
    """
    if not created:  # Only on updates
        from notifications.models import Notification
        
        # Determine notification message
        if instance.status == 'scheduled':
            message = f"Interview scheduled for {instance.job.title}"
            notification_type = 'info'
        elif instance.status == 'in_progress':
            message = f"Interview for {instance.job.title} has started"
            notification_type = 'warning'
        elif instance.status == 'completed':
            message = f"Interview for {instance.job.title} completed"
            notification_type = 'success'
        elif instance.status == 'cancelled':
            message = f"Interview for {instance.job.title} cancelled"
            notification_type = 'error'
        else:
            return
        
        # Notify candidate
        Notification.objects.create(
            title="Interview Update",
            message=message,
            notification_type=notification_type,
            category="interview",
            recipient_type="specific",
            recipient=instance.candidate,
            data={
                "interview_id": str(instance.id),
                "job_title": instance.job.title,
                "status": instance.status
            },
            action_url=f"/interviews/{instance.id}/"
        )
        
        # Notify HR (except for candidate actions)
        if instance.status != 'in_progress':  # Don't notify HR when candidate starts
            Notification.objects.create(
                title="Interview Update",
                message=f"Interview with {instance.candidate.email} is now {instance.status}",
                notification_type=notification_type,
                category="interview",
                recipient_type="specific",
                recipient=instance.hr_user,
                data={
                    "interview_id": str(instance.id),
                    "candidate_name": f"{instance.candidate.first_name} {instance.candidate.last_name}",
                    "status": instance.status
                }
            )