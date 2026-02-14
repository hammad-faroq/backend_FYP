from django.contrib import admin
from django.utils import timezone
from .models import Notification, NotificationPreference, ContactMessage

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient_type', 'category', 'recipient_email', 'read', 'created_at']
    list_filter = ['recipient_type', 'category', 'notification_type', 'read', 'created_at']
    search_fields = ['title', 'message', 'recipient__email']
    readonly_fields = ['created_at', 'read_at']
    actions = ['mark_as_read', 'mark_as_unread']
    
    # Add this method to display recipient email
    def recipient_email(self, obj):
        return obj.recipient.email if obj.recipient else "No recipient"
    recipient_email.short_description = 'Recipient Email'
    
    # Override save_model to handle recipient_type based on recipient's role
    def save_model(self, request, obj, form, change):
        if obj.recipient:
            # Determine recipient_type based on user's role
            if hasattr(obj.recipient, 'role'):
                if obj.recipient.role == 'hr':
                    obj.recipient_type = 'hr'  # Use lowercase to match model choices
                elif obj.recipient.role == 'job_seeker':
                    obj.recipient_type = 'job_seeker'  # Use lowercase to match model choices
                else:
                    # Check what choices are available in your model
                    # If 'all' is not an option, use the first available choice
                    obj.recipient_type = 'hr'  # Default to hr or whatever is available
            else:
                # Check for HR-specific fields or groups
                if hasattr(obj.recipient, 'is_hr') and obj.recipient.is_hr:
                    obj.recipient_type = 'hr'
                elif hasattr(obj.recipient, 'is_job_seeker') and obj.recipient.is_job_seeker:
                    obj.recipient_type = 'job_seeker'
                else:
                    obj.recipient_type = 'hr'  # Default value
        super().save_model(request, obj, form, change)
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(read=True, read_at=timezone.now())
        self.message_user(request, f"{updated} notifications marked as read.")
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(read=False, read_at=None)
        self.message_user(request, f"{updated} notifications marked as unread.")
    mark_as_unread.short_description = "Mark selected notifications as unread"

    # Custom form to use only available choices
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "recipient_type":
            # Get the actual choices from the model field
            field = self.model._meta.get_field('recipient_type')
            kwargs['choices'] = field.choices
        return super().formfield_for_choice_field(db_field, request, **kwargs)

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_role', 'email_notifications', 'inapp_notifications', 'updated_at']
    # Only include fields that actually exist in your model
    # If you're not sure, use an empty list or just 'updated_at'
    list_filter = ['updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    
    # Add this to show user role
    def user_role(self, obj):
        if hasattr(obj.user, 'role'):
            return obj.user.role
        return 'N/A'
    user_role.short_description = 'User Role'
    
    def email_notifications(self, obj):
        # Check which notification types are enabled for email
        # Use getattr with default False to handle missing fields
        return any([
            getattr(obj, 'email_contact_messages', False),
            getattr(obj, 'email_job_alerts', False),
            getattr(obj, 'email_application_updates', False),
        ])
    email_notifications.boolean = True
    email_notifications.short_description = 'Email Enabled'
    
    def inapp_notifications(self, obj):
        # Check which notification types are enabled for in-app
        return any([
            getattr(obj, 'inapp_contact_messages', False),
            getattr(obj, 'inapp_job_alerts', False),
            getattr(obj, 'inapp_application_updates', False),
        ])
    inapp_notifications.boolean = True
    inapp_notifications.short_description = 'In-App Enabled'

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'name', 'email', 'status', 'created_at', 'assigned_to']
    list_filter = ['status', 'user_type', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at', 'ip_address', 'user_agent']
    actions = ['mark_as_reviewed', 'mark_as_responded']
    
    fieldsets = (
        ('Message Details', {
            'fields': ('name', 'email', 'phone', 'subject', 'message')
        }),
        ('User Information', {
            'fields': ('user', 'user_type'),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': ('status', 'assigned_to', 'admin_response', 'responded_by', 'responded_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(status='reviewed')
        self.message_user(request, f"{updated} messages marked as reviewed.")
    mark_as_reviewed.short_description = "Mark selected messages as reviewed"
    
    def mark_as_responded(self, request, queryset):
        updated = queryset.update(status='responded', responded_by=request.user, responded_at=timezone.now())
        self.message_user(request, f"{updated} messages marked as responded.")
    mark_as_responded.short_description = "Mark selected messages as responded"