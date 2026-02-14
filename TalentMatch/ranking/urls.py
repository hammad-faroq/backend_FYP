from django.urls import path
from .views import run_ranking_for_job

urlpatterns = [
    path('rank/<int:job_id>/', run_ranking_for_job, name='run_ranking_for_job'),
]
