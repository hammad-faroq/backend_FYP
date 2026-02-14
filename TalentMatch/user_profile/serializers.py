from datetime import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, EmailAddress, UserActivity

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'full_name',
            'email',
            'nick_name',
            'gender',
            'country',
            'language',
            'time_zone',
            'phone_number',
            'address',
            'city',
            'state',
            'postal_code',
            'job_title',
            'company',
            'industry',
            'years_of_experience',
            'highest_education',
            'university',
            'graduation_year',
            'profile_picture',
            'bio',
            'is_public',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_email(self, obj):
        return obj.email


class EmailAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAddress
        fields = ['id', 'email', 'is_primary', 'is_verified', 'created_at']
        read_only_fields = ['id', 'is_primary', 'is_verified', 'created_at']


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = ['activity_type', 'description', 'ip_address', 'created_at']
        read_only_fields = ['created_at']


class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    nick_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    language = serializers.CharField(max_length=10, required=False)
    time_zone = serializers.CharField(max_length=50, required=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)
    job_title = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)
    industry = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, allow_null=True)
    highest_education = serializers.CharField(required=False, allow_blank=True)
    university = serializers.CharField(required=False, allow_blank=True)
    graduation_year = serializers.IntegerField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    profile_picture_base64 = serializers.CharField(required=False, allow_blank=True)  # For base64 uploads
    
    def validate_language(self, value):
        if value:
            valid_languages = [choice[0] for choice in UserProfile.LANGUAGE_CHOICES]
            if value not in valid_languages:
                raise serializers.ValidationError("Invalid language selection")
        return value
    
    def validate_years_of_experience(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Years of experience cannot be negative")
        return value
    
    def validate_graduation_year(self, value):
        if value is not None:
            current_year = timezone.now().year
            if value < 1900 or value > current_year + 10:
                raise serializers.ValidationError(f"Graduation year must be between 1900 and {current_year + 10}")
        return value