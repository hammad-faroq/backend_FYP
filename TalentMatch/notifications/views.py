from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from .models import Notification, NotificationPreference, ContactMessage
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, ContactMessageSerializer,
    ContactMessageResponseSerializer
)

User = get_user_model()

class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission to only allow owners or admins to access."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # For notifications, check if user is recipient
        if hasattr(obj, 'recipient'):
            return obj.recipient == request.user
        
        # For preferences, check if user is owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['read', 'notification_type', 'category']
    
    def get_queryset(self):
        """Return notifications for the current user based on their role"""
        user = self.request.user
        
        # # DEBUG: Print user info
        # print(f"\n{'='*50}")
        # # print(f"DEBUG: User: {user.username}")
        # print(f"DEBUG: User ID: {user.id}")
        # print(f"DEBUG: Email: {user.email}")
        # print(f"DEBUG: User has 'role' attribute: {hasattr(user, 'role')}")
        # if hasattr(user, 'role'):
        #     print(f"DEBUG: User role value: '{user.role}'")
        # print(f"DEBUG: is_staff: {user.is_staff}")
        # print(f"DEBUG: is_superuser: {user.is_superuser}")
        # print(f"DEBUG: Groups: {[g.name for g in user.groups.all()]}")
        
        # Get user role
        user_role = getattr(user, 'role', None)
        
        # Start with empty queryset
        queryset = Notification.objects.none()
        
        # CRITICAL FIX: Build the query correctly
        # First, always include specific notifications for this user
        specific_notifications = Notification.objects.filter(
            recipient_type='specific',
            recipient=user
        )
        # print(f"DEBUG: Specific notifications count: {specific_notifications.count()}")
        
        # Get role-based notifications
        role_based_notifications = Notification.objects.filter(
            Q(recipient_type='all')  # All users get 'all' notifications
        )
        
        # Add role-specific notifications
        if user_role == 'hr' or user.groups.filter(name='HR').exists():
            # print(f"DEBUG: Detected as HR user")
            role_based_notifications = role_based_notifications | Notification.objects.filter(
                recipient_type='hr'
            )
        
        elif user_role == 'job_seeker' or user.groups.filter(name__icontains='job').exists():
            # print(f"DEBUG: Detected as Job Seeker user")
            role_based_notifications = role_based_notifications | Notification.objects.filter(
                recipient_type='job_seeker'
            )
        
        # Admin users get admin notifications
        if user.is_staff or user.is_superuser or user_role == 'admin':
            # print(f"DEBUG: Detected as Admin user")
            role_based_notifications = role_based_notifications | Notification.objects.filter(
                recipient_type='admin'
            )
        
        # Exclude specific user notifications from role-based (since they're already in specific_notifications)
        role_based_notifications = role_based_notifications.exclude(recipient_type='specific')
        
        # print(f"DEBUG: Role-based notifications count: {role_based_notifications.count()}")
        
        # Combine both querysets
        queryset = specific_notifications | role_based_notifications
        
        # Exclude expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        # print(f"DEBUG: Final query count: {queryset.count()}")
        # print(f"DEBUG: Final SQL query: {str(queryset.query)}")
        # print(f"{'='*50}\n")
        
        return queryset.order_by('-created_at').distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(read=False).count()
        return Response({'count': count})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        notifications = self.get_queryset().filter(read=False)
        count = notifications.count()
        notifications.update(read=True, read_at=timezone.now())
        return Response({'status': 'all marked as read', 'count': count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'unread': queryset.filter(read=False).count(),
            'by_type': queryset.values('notification_type').annotate(count=Count('id')),
            'by_category': queryset.values('category').annotate(count=Count('id')),
            'recent': NotificationSerializer(
                queryset[:10], many=True, context={'request': request}
            ).data
        }
        
        return Response(stats)
    
    def create(self, request, *args, **kwargs):
        """Override create to handle permission checking"""
        # Only allow staff/superusers to create notifications
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Only administrators can create notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)

# ... rest of the views remain the same ...

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for notification preferences"""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put'])
    def my_preferences(self, request):
        """Get or update current user's preferences"""
        pref, created = NotificationPreference.objects.get_or_create(
            user=request.user,
            defaults={
                'email_contact_messages': True,
                'email_job_alerts': True,
                # ... other defaults
            }
        )
        
        if request.method == 'GET':
            serializer = self.get_serializer(pref)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            serializer = self.get_serializer(pref, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContactMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for contact messages"""
    
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to submit contact form
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'user_type']
    
    def get_permissions(self):
        """Only allow authenticated users to list/view contact messages"""
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        """Return queryset based on user role"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            # Admins can see all contact messages
            return ContactMessage.objects.all()
        
        # Check user role for HR
        user_role = getattr(user, 'role', None)
        if user_role == 'hr' or user.groups.filter(name='HR').exists():
            # HR can see messages assigned to them or general HR inquiries
            return ContactMessage.objects.filter(
                Q(assigned_to=user) | Q(user_type='HR') | Q(subject__icontains='job')
            )
        else:
            # Regular users can only see their own messages
            return ContactMessage.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ContactMessageResponseSerializer
        return ContactMessageSerializer
    
    def perform_create(self, serializer):
        """Create contact message and send notifications"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def assign_to_me(self, request, pk=None):
        """Assign a contact message to the current user"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff members can assign messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        contact_message = self.get_object()
        contact_message.assigned_to = request.user
        contact_message.save()
        
        # Create notification for the assignee
        Notification.objects.create(
            title="Contact Message Assigned",
            message=f"You have been assigned a contact message: {contact_message.subject}",
            notification_type="info",
            category="contact",
            recipient_type="specific",
            recipient=request.user,
            data={
                "contact_id": contact_message.id,
                "sender_name": contact_message.name,
                "subject": contact_message.subject
            },
            action_url=f"/admin/contact/{contact_message.id}/"
        )
        
        serializer = self.get_serializer(contact_message)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for contact messages"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff members can view dashboard stats'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total = ContactMessage.objects.count()
        pending = ContactMessage.objects.filter(status='pending').count()
        responded = ContactMessage.objects.filter(status='responded').count()
        
        stats = {
            'total': total,
            'pending': pending,
            'responded': responded,
            'response_rate': (responded / total * 100) if total > 0 else 0,
            'by_user_type': ContactMessage.objects.values('user_type').annotate(
                count=Count('id')
            ),
            'recent_messages': ContactMessageSerializer(
                ContactMessage.objects.order_by('-created_at')[:5], many=True,
                context={'request': request}
            ).data
        }
        
        return Response(stats)

class AdminNotificationView(generics.ListAPIView):
    """View for admin notifications dashboard"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Get notifications for admin dashboard"""
        return Notification.objects.filter(
            Q(recipient_type='admin') | Q(recipient_type='all')
        ).exclude(recipient__isnull=False).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """Return notifications grouped by category"""
        queryset = self.get_queryset()
        
        # Group notifications by category
        categories = {
            'contact': queryset.filter(category='contact'),
            'application': queryset.filter(category='application'),
            'system': queryset.filter(category='system'),
            'security': queryset.filter(category='security'),
        }
        
        response_data = {}
        for category, qs in categories.items():
            response_data[category] = {
                'count': qs.count(),
                'unread': qs.filter(read=False).count(),
                'notifications': self.get_serializer(qs[:10], many=True).data
            }
        
        return Response(response_data)

class UserNotificationView(generics.ListAPIView):
    """View for user-specific notifications"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        user_type = self.kwargs.get('user_type', 'all')
        
        # Base queryset
        if user_type == 'specific':
            queryset = Notification.objects.filter(recipient=user)
        else:
            # Get user role
            user_role = getattr(user, 'role', None)
            
            # Get notifications for user's type
            if user_role == 'hr' or user.groups.filter(name='HR').exists():
                queryset = Notification.objects.filter(
                    Q(recipient_type='hr') | Q(recipient_type='all')
                )
            elif user_role == 'job_seeker' or user.groups.filter(name__icontains='job').exists():
                queryset = Notification.objects.filter(
                    Q(recipient_type='job_seeker') | Q(recipient_type='all')
                )
            else:
                queryset = Notification.objects.filter(recipient_type='all')
            
            # Exclude specific user notifications
            queryset = queryset.exclude(recipient__isnull=False)
        
        return queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).order_by('-created_at')