from django.contrib import admin
from .models import (
    InterviewCategory,
    QuestionType,
    InterviewQuestion,
    Interview,
    InterviewQuestionSet,
    CandidateAnswer,
    PreparationModule,
    UserPreparationProgress,
    AvailabilitySlot,
    InterviewResult,
    AIPreparationSession,
    InterviewPreparation,
    InterviewQuestionGeneration,
    InterviewChatSession,
    InterviewChatMessage,
    MockInterviewSession,
    MockInterviewAnswer
)

admin.site.register(InterviewCategory)
admin.site.register(QuestionType)
admin.site.register(InterviewQuestion)
admin.site.register(Interview)
admin.site.register(InterviewQuestionSet)
admin.site.register(CandidateAnswer)
admin.site.register(PreparationModule)
admin.site.register(UserPreparationProgress)
admin.site.register(AvailabilitySlot)
admin.site.register(InterviewResult)
admin.site.register(AIPreparationSession)
admin.site.register(InterviewPreparation)
admin.site.register(InterviewQuestionGeneration)
admin.site.register(InterviewChatSession)
admin.site.register(InterviewChatMessage)
admin.site.register(MockInterviewSession)
admin.site.register(MockInterviewAnswer)