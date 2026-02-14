from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.api_login, name='api_login'),
    path('dashboard/', views.api_dashboard, name='api_dashboard'),
    path('logout/', views.api_logout, name='api_logout'),
    path('register/',views.api_register, name='api_register'),

    # Password reset URLs
    path('password-reset/', views.api_password_reset_request, name='api_password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', views.api_password_reset_confirm, name='api_password_reset_confirm'),
    
    # Task 1.7: Account status check - FIXED URL
    path('account-status/', views.api_check_account_status, name='api_check_account_status'),

    #path('check-status/', views.api_check_account_status, name='check_account_status'),
    # Task 1.7: Account status check
    # path('check-account-status/', views.api_check_account_status, name='api_check_account_status'),

]