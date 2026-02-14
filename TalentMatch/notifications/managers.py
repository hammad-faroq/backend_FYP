from django.db import models
from django.db.models import Q

class NotificationManager(models.Manager):
    def for_user(self, user):
        """
        Get notifications for a specific user based on their role
        """
        if not user.is_authenticated:
            return self.none()
        
        user_role = getattr(user, 'role', None)
        
        # Base query - notifications that should be visible to this user
        query = Q(recipient_type='all')
        
        # Add role-specific notifications
        if user_role:
            query = query | Q(recipient_type=user_role)
        
        # Add superuser/admin specific
        if user.is_superuser or user.is_staff:
            query = query | Q(recipient_type='admin')
        
        # Add specific user notifications (if your model has user field)
        if hasattr(self.model, 'user'):
            query = query | Q(user=user)
        
        return self.filter(query).order_by('-created_at')