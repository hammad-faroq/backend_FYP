from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification, ContactMessage

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences when a new user is created"""
    if created:
        from .models import NotificationPreference
        NotificationPreference.objects.create(user=instance)

@receiver(post_save, sender=ContactMessage)
def send_contact_confirmation(sender, instance, created, **kwargs):
    """Send confirmation notification when contact message is submitted"""
    if created and instance.user:
        Notification.objects.create(
            title="Contact Message Received",
            message=f"Thank you for contacting us. We'll respond to '{instance.subject}' soon.",
            notification_type="success",
            category="contact",
            recipient_type="specific",
            recipient=instance.user,
            data={
                "contact_id": instance.id,
                "subject": instance.subject
            }
        )

@receiver(post_save, sender=User)
def send_welcome_notification(sender, instance, created, **kwargs):
    """Send welcome notification to new users"""
    if created:
        # Determine user type from role field
        user_type = 'all'
        user_role = getattr(instance, 'role', None)
        
        if user_role == 'hr':
            user_type = 'hr'
        elif user_role == 'job_seeker':
            user_type = 'job_seeker'
        elif instance.is_staff or instance.is_superuser:
            user_type = 'admin'
        
        Notification.objects.create(
            title="Welcome to TalentMatch AI!",
            message="Thank you for joining TalentMatch AI. We're excited to have you on board!",
            notification_type="success",
            category="system",
            recipient_type="specific",
            recipient=instance,
            data={
                "welcome": True,
                "user_type": user_type
            }
        )