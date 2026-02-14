from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('message', 'Message'),
    )
    
    RECIPIENT_TYPES = (
        ('all', 'All Users'),
        ('admin', 'Admin'),
        ('hr', 'HR'),
        ('job_seeker', 'Job Seeker'),
        ('specific', 'Specific User'),
    )
    
    CATEGORIES = (
        ('contact', 'Contact Form'),
        ('application', 'Job Application'),
        ('shortlist', 'Shortlist Update'),
        ('interview', 'Interview'),
        ('message', 'Direct Message'),
        ('system', 'System Update'),
        ('security', 'Security Alert'),
    )
    
    # Basic fields
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='system')
    
    # Recipient information
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES, default='all')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                                  related_name='notifications')
    
    # Sender information (if applicable)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='sent_notifications')
    
    # Status tracking
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)  # For storing extra info like job_id, etc.
    action_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read', 'created_at']),
            models.Index(fields=['recipient_type', 'created_at']),
        ]
    
    def __str__(self):
        if self.recipient:
            return f"{self.title} - {self.recipient.email}"
        return f"{self.title} - {self.recipient_type}"
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_icon(self):
        icons = {
            'info': 'information-circle',
            'success': 'check-circle',
            'warning': 'exclamation-triangle',
            'error': 'x-circle',
            'message': 'chat-bubble-left-right',
        }
        return icons.get(self.notification_type, 'bell')
    
    def save(self, *args, **kwargs):
        # Ensure recipient is None if recipient_type is not 'specific'
        if self.recipient_type != 'specific':
            self.recipient = None
        super().save(*args, **kwargs)


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_contact_messages = models.BooleanField(default=True)
    email_job_alerts = models.BooleanField(default=True)
    email_application_updates = models.BooleanField(default=True)
    email_security_alerts = models.BooleanField(default=True)
    
    # In-app notification preferences
    inapp_contact_messages = models.BooleanField(default=True)
    inapp_job_alerts = models.BooleanField(default=True)
    inapp_application_updates = models.BooleanField(default=True)
    inapp_interview_invites = models.BooleanField(default=True)
    inapp_shortlist_updates = models.BooleanField(default=True)
    
    # Push notification preferences
    push_notifications = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(default='22:00:00')
    quiet_hours_end = models.TimeField(default='08:00:00')
    
    # Mute specific categories
    muted_categories = models.JSONField(default=list, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.email}"

class ContactMessage(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    )
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # User info if logged in
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=20, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='assigned_contacts')
    
    # Response tracking
    admin_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='responded_contacts')
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    def create_notification_for_admins(self):
        """Create notification for all admins when a new contact message is received"""
        from django.db.models import Q
        admin_users = User.objects.filter(
            Q(is_staff=True) | Q(is_superuser=True) | Q(groups__name='Admin')
        ).distinct()
        
        for admin in admin_users:
            Notification.objects.create(
                title="New Contact Message",
                message=f"New message from {self.name}: {self.subject}",
                notification_type="message",
                category="contact",
                recipient_type="specific",
                recipient=admin,
                data={
                    "contact_id": self.id,
                    "sender_name": self.name,
                    "sender_email": self.email,
                    "message_preview": self.message[:100] + "..." if len(self.message) > 100 else self.message
                },
                action_url=f"/admin/contact/{self.id}/"
            )
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.create_notification_for_admins()