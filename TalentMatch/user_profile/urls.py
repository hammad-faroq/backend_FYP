from django.urls import path
from . import views

urlpatterns = [
    # Profile endpoints
    path('', views.profile_detail, name='profile_detail'),
    path('json-update/', views.profile_update, name='profile_update_json'),
    path('summary/', views.profile_summary, name='profile_summary'),
    path('public/<int:user_id>/', views.public_profile, name='public_profile'),
    path('public/', views.public_profile, name='my_public_profile'),
    
    # Email management endpoints
    path('emails/', views.email_addresses, name='email_addresses'),
    path('emails/<int:email_id>/delete/', views.delete_email_address, name='delete_email'),
    path('emails/<int:email_id>/set-primary/', views.set_primary_email, name='set_primary_email'),
    path('emails/<int:email_id>/verify/', views.verify_email, name='verify_email'),
    
    # Activity endpoints
    path('activities/', views.user_activities, name='user_activities'),
]