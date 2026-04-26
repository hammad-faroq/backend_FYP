from django.urls import path
from .views import run_ranking_for_job
from .views import cv_job_match
urlpatterns = [
    path('rank/<int:job_id>/', run_ranking_for_job, name='run_ranking_for_job'),
    # path("cv-job-match/", cv_job_match, name="cv-job-match"),
]
