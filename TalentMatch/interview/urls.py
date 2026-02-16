from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .bulk_views import BulkInterviewQuestionCreateView

router = DefaultRouter()
router.register(r'categories', views.InterviewCategoryViewSet, basename='category')
router.register(r'questions', views.InterviewQuestionViewSet, basename='question')
router.register(r'interviews', views.InterviewViewSet, basename='interview')
router.register(r'preparation-modules', views.PreparationModuleViewSet, basename='preparation-module')

urlpatterns = [
    path("questions/bulk/", BulkInterviewQuestionCreateView.as_view()),
    
    # ✅ FIRST: Put all specific UUID patterns BEFORE include(router.urls)
    # ================= CANDIDATE ENDPOINTS =================
    path('candidate/upcoming-interviews/', views.CandidateUpcomingInterviewsView.as_view(), name='upcoming-interviews'),
    path('candidate/interview/<uuid:interview_id>/start/', views.CandidateStartInterviewView.as_view(), name='candidate-start-interview'),
    path('candidate/interview/<uuid:interview_id>/questions/', views.GetInterviewQuestionsView.as_view(), name='get-interview-questions'),
    path('candidate/interview/<uuid:interview_id>/submit-answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('candidate/interview/<uuid:interview_id>/submit-all/', views.SubmitAllAnswersView.as_view(), name='submit-all-answers'),
    path('candidate/interview/<uuid:interview_id>/result/', views.GetInterviewResultView.as_view(), name='get-interview-result'),
    
    # ✅ Candidate interview detail endpoints (specific)
    path('candidate/interviews/<uuid:interview_id>/', views.GetCandidateInterviewDetailView.as_view(), name='candidate-interview-detail'),
    path('interviews/candidate/<uuid:interview_id>/', views.GetCandidateInterviewDetailView.as_view(), name='candidate-interview-detail-alt'),

    # ================= HR ENDPOINTS =================
    path('hr/dashboard/', views.HRDashboardView.as_view(), name='hr-dashboard'),
    path('hr/schedule-interview/', views.ScheduleInterviewView.as_view(), name='schedule-interview'),
    path('hr/interview/<uuid:interview_id>/questions/', views.ManageInterviewQuestionsView.as_view(), name='manage-interview-questions'),
    path('hr/interview/<uuid:interview_id>/start/', views.StartInterviewView.as_view(), name='start-interview'),
    path('hr/interview/<uuid:interview_id>/answers/<uuid:answer_id>/', views.ReviewCandidateAnswersView.as_view(), name='review-single-answer'),
    path('hr/interview/<uuid:interview_id>/answers/', views.ReviewCandidateAnswersView.as_view(), name='review-answers'),
    path('hr/interview/<uuid:interview_id>/result/', views.InterviewResultView.as_view(), name='interview-result'),
    path('hr/interview/<uuid:interview_id>/finalize/', views.FinalizeInterviewView.as_view(), name='finalize-interview'),
    path('hr/answer/<uuid:answer_id>/grade/', views.GradeCandidateAnswerView.as_view(), name='grade-answer'),
    
    path('hr/interview/<uuid:interview_id>/results/',views.HRInterviewResultsView.as_view(),name='hr-interview-results'),

    # ================= PREPARATION =================
    path('candidate/preparation-recommendations/', views.PreparationRecommendationsView.as_view()),
    path('candidate/preparation/<int:module_id>/start/', views.StartPreparationModuleView.as_view()),
    path('candidate/preparation/<int:module_id>/complete/', views.CompletePreparationModuleView.as_view()),
    path('candidate/preparation/progress/', views.PreparationProgressView.as_view()),
    #### For interview Preparation of the Candidate w.r.t Job Description####
    path("candidate/interview-preparation/",views.CandidateInterviewPreparationView.as_view(),name="candidate-interview-preparation"),
    path("candidate/interview-preparation/generate-more/",views.GenerateMoreInterviewQuestionsView.as_view(),name="generate-more-questions"),
    path("candidate/interview-chat/",views.InterviewChatView.as_view(),name="interview-chat"),
    path("candidate/mock-interview/",views. MockInterviewSessionView.as_view(), name="mock-interview"),
    path('progress/<int:job_id>/', views.MockInterviewProgressView.as_view(), name='mock_interview_progress'),
    # ================= AVAILABILITY =================
    path('availability/', views.ManageAvailabilityView.as_view()),
    path('availability/check-conflicts/', views.CheckSchedulingConflictsView.as_view()),

    # ================= ADMIN =================
    path('admin/question-import/', views.ImportQuestionsView.as_view()),
    path('admin/analytics/', views.InterviewAnalyticsView.as_view()),
    path('', include(router.urls)),
    # ✅ NOW: Generic UUID pattern (LAST, after all specific ones)
    path('<uuid:interview_id>/', views.GetInterviewDetailView.as_view(), name='interview-detail'),
    
    # ✅ FINALLY: Include router URLs (they have their own patterns)
    
]