from django.urls import path
from . import views
from .views import ResumeUploadView, find_similar_jobs

urlpatterns = [
    # 🧩 Resume Template & Generation Routes
    path('', views.select_template, name='select_template'),
    path('resume/input/', views.resume_input, name='resume_input'),
    path('resume/<str:template>/<int:resume_id>/', views.resume_output, name="resume_output"),
    path('resume/template1/<int:pk>/pdf/', views.resume_pdf1, name='resume_pdf1'),
    path('resume/template2/<int:pk>/pdf/', views.resume_pdf2, name='resume_pdf2'),

    # 📤 Resume Upload Endpoints
    path('resume/upload/', ResumeUploadView.as_view(), name='resume_upload'),
    path('resume/success/', views.upload_success, name='upload_success'),

    # 🔍 Job Matching Endpoint (for frontend MatchesPage)
    # The user ID will be extracted automatically from the authenticated user.
    # Example: GET /api/cv_manager/similar-jobs/
    # path("similar-jobs/", find_similar_jobs, name="get_similar_jobs"),
    path("similar-jobs/", views.find_similar_jobs_view, name="get_similar_jobs"),
    #####
    ##### New things
    #####
    # path('api/upload-enhanced/', views.EnhancedResumeUploadView.as_view(), name='resume-upload-enhanced'),
    path('api/stored-career-insights/', views.get_stored_career_insights, name='stored-career-insights'),
    path('api/stored-certifications/', views.get_stored_certifications, name='stored-certifications'),
    path('api/stored-learning-path/', views.get_stored_learning_path, name='stored-learning-path'),
    path('api/stored-job-matches/', views.get_stored_job_matches, name='stored-job-matches'),
    path("resume-analysis/", views.get_resume_analysis, name="resume-analysis"),
    path('api/check-application-status/<int:job_id>/', views.check_application_status, name='check_application_status'),

]
