from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet, NotificationPreferenceViewSet,
    ContactMessageViewSet, AdminNotificationView,
    UserNotificationView
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')
router.register(r'contact-messages', ContactMessageViewSet, basename='contactmessage')

urlpatterns = [
    path('', include(router.urls)),
    
    # Admin notifications dashboard
    path('admin/notifications/', AdminNotificationView.as_view(), name='admin-notifications'),
    
    # User-specific notifications
    path('user/notifications/<str:user_type>/', UserNotificationView.as_view(), name='user-notifications'),
    
    # Mark all as read
    path('notifications/mark-all-read/', 
         NotificationViewSet.as_view({'post': 'mark_all_as_read'}), 
         name='mark-all-read'),
]