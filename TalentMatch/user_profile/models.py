from django.db import models
from django.conf import settings
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extended profile information for users
    """
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    )
    
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('zh', 'Chinese'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('ur', 'Urdu'),
    )
    
    TIMEZONE_CHOICES = (
        ('UTC', 'UTC'),
        ('PKT', 'Pakistan Standard Time'),
        ('EST', 'Eastern Time'),
        ('PST', 'Pacific Time'),
        ('CST', 'Central Time'),
        ('GMT', 'Greenwich Mean Time'),
        ('CET', 'Central European Time'),
        ('IST', 'Indian Standard Time'),
        
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Basic Information
    nick_name = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    country = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    time_zone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='UTC')
    
    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Professional Information (for Job Seekers)
    job_title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    
    # Educational Background (for Job Seekers)
    highest_education = models.CharField(max_length=200, blank=True)
    university = models.CharField(max_length=200, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    
    # Profile Settings
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    bio = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    @property
    def email(self):
        return self.user.email
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class EmailAddress(models.Model):
    """
    Additional email addresses for users
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='additional_emails'
    )
    email = models.EmailField()
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Additional Email"
        verbose_name_plural = "Additional Emails"
        unique_together = ['user', 'email']
    
    def __str__(self):
        return self.email


class UserActivity(models.Model):
    """
    Track user activities on the platform
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=50)  # login, profile_update, etc.
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type} at {self.created_at}"