from django.contrib import admin
from .models import UserProfile, EmailAddress, UserActivity


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'country', 'job_title', 'is_public')
    list_filter = ('gender', 'country', 'language', 'is_public')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'nick_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'is_primary', 'is_verified', 'created_at')
    list_filter = ('is_primary', 'is_verified')
    search_fields = ('email', 'user__email')
    raw_id_fields = ('user',)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'ip_address', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__email', 'description')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)