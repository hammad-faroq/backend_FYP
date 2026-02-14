from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_job, name='create_job'),
    path('list/', views.list_jobs, name='list_jobs'),
    path('<int:job_id>/', views.job_detail, name='job_detail'),
    path('update/<int:job_id>/', views.update_job, name='update_job'),
    path('delete/<int:job_id>/', views.delete_job, name='delete_job'),
    path('<int:job_id>/apply/', views.apply_to_job, name='apply_to_job'),
    path("applied/", views.list_applied_jobs, name="list_applied_jobs"),
    path('resume/', views.resume_view, name='resume_view'),
    path('<int:job_id>/applications/', views.list_job_applications, name='job_applications'),
    # path('similar-jobs/<int:user_id>/', views.similar_jobs, name='similar_jobs'),
]
