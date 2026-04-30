from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.api_login, name='api_login'),
    path('dashboard/', views.api_dashboard, name='api_dashboard'),
    path('logout/', views.api_logout, name='api_logout'),
    path('register/',views.api_register, name='api_register'),
    path('google-auth/', views.google_auth, name='google_auth'),
    # Password reset URLs
    path('password-reset/', views.api_password_reset_request, name='api_password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', views.api_password_reset_confirm, name='api_password_reset_confirm'),
    
    # Task 1.7: Account status check - FIXED URL
    path('account-status/', views.api_check_account_status, name='api_check_account_status'),

    path('change-password/', views.api_change_password, name='api_change_password'),
    path('send-otp/',       views.api_send_otp,              name='api_send_otp'),
    path('verify-otp/',     views.api_verify_otp,            name='api_verify_otp')

]