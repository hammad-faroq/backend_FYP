from datetime import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationPreference, ContactMessage

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']

class NotificationSerializer(serializers.ModelSerializer):
    sender_info = UserSerializer(source='sender', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'category',
            'recipient_type', 'recipient', 'sender', 'sender_info',
            'read', 'read_at', 'data', 'action_url',
            'created_at', 'expires_at', 'time_ago'
        ]
        read_only_fields = ['created_at', 'expires_at']
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        if not obj.created_at:
            return ""
        
        return timesince(obj.created_at, timezone.now()) + " ago"

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'title', 'message', 'notification_type', 'category',
            'recipient_type', 'recipient', 'data', 'action_url', 'expires_at'
        ]
    
    def validate(self, attrs):
        recipient_type = attrs.get('recipient_type')
        recipient = attrs.get('recipient')
        
        if recipient_type == 'specific' and not recipient:
            raise serializers.ValidationError({
                'recipient': 'Recipient is required for specific notifications'
            })
        
        return attrs

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_contact_messages', 'email_job_alerts',
            'email_application_updates', 'email_security_alerts',
            'inapp_contact_messages', 'inapp_job_alerts',
            'inapp_application_updates', 'inapp_interview_invites',
            'inapp_shortlist_updates', 'push_notifications',
            'quiet_hours_start', 'quiet_hours_end',
            'muted_categories', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']

class ContactMessageSerializer(serializers.ModelSerializer):
    user_info = UserSerializer(source='user', read_only=True)
    assigned_to_info = UserSerializer(source='assigned_to', read_only=True)
    responded_by_info = UserSerializer(source='responded_by', read_only=True)
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'user', 'user_info', 'user_type', 'status',
            'assigned_to', 'assigned_to_info', 'admin_response',
            'responded_by', 'responded_by_info', 'responded_at',
            'ip_address', 'user_agent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
            validated_data['user_type'] = request.user.groups.first().name if request.user.groups.exists() else ''
        
        # Get IP address and user agent
        if request:
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)

class ContactMessageResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['admin_response', 'status']
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            instance.responded_by = request.user
            instance.responded_at = timezone.now()
        
        return super().update(instance, validated_data)