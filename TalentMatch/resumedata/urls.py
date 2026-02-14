
from django.urls import path
from .views import AnalyzeResumeAPI  # ✅ Only import what's defined

urlpatterns = [
    path('analyze/', AnalyzeResumeAPI.as_view(), name='analyze_resume'),
]
