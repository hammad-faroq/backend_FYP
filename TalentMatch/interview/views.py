# interviews/views.py
from uuid import UUID
from django.utils import timezone
from neo4j import Transaction
from rest_framework import viewsets, status, permissions, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Avg, Sum  # FIXED: Changed from sympy import Sum
from django_filters.rest_framework import DjangoFilterBackend

from jobs.models import Job

from .models import (
    Interview, InterviewQuestion, InterviewCategory, 
    CandidateAnswer, PreparationModule, UserPreparationProgress,
    InterviewQuestionSet, AvailabilitySlot, QuestionType  # FIXED: Changed from UserAvailability to AvailabilitySlot
)
from .serializers import (
    CandidateAnswerReviewSerializer, InterviewSerializer, InterviewQuestionSerializer,
    InterviewCategorySerializer, CandidateAnswerSerializer,
    PreparationModuleSerializer, UserPreparationProgressSerializer,
    InterviewQuestionSetSerializer,  # REMOVED: UserAvailabilitySerializer
    InterviewDetailSerializer
)
# REMOVED: Services that don't exist yet - uncomment when you create them
# from .services.interview_service import InterviewService, PreparationService
# from .validators import InterviewValidator
from .permissions import IsHRUser, IsCandidate
from .filters import InterviewFilter, InterviewQuestionFilter
#
# ==================== VIEWSETS ====================

class InterviewCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for interview categories"""
    queryset = InterviewCategory.objects.filter(is_active=True)
    serializer_class = InterviewCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        """Filter categories by user role"""
        user = self.request.user
        if user.is_hr():
            return InterviewCategory.objects.filter(
                Q(created_by=user) | Q(is_active=True)
            )
        return InterviewCategory.objects.filter(is_active=True)

class InterviewQuestionViewSet(viewsets.ModelViewSet):
    """CRUD for interview questions"""
    queryset = InterviewQuestion.objects.filter(is_active=True)
    serializer_class = InterviewQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InterviewQuestionFilter
    search_fields = ['question_text', 'category__name']
    ordering_fields = ['difficulty', 'created_at', 'points']
    
    def get_queryset(self):
        """Filter questions by user role"""
        user = self.request.user
        if user.is_hr():
            return InterviewQuestion.objects.filter(
                Q(created_by=user) | Q(is_active=True)
            )
        return InterviewQuestion.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def bulk_assign(self, request, pk=None):
        """Assign this question to multiple interviews"""
        interview_ids = request.data.get('interview_ids', [])
        try:
            question = self.get_object()
            # Simplified version since InterviewService doesn't exist yet
            assigned_count = 0
            for interview_id in interview_ids:
                try:
                    interview = Interview.objects.get(id=interview_id, hr_user=request.user)
                    InterviewQuestionSet.objects.get_or_create(
                        interview=interview,
                        question=question,
                        defaults={'order': InterviewQuestionSet.objects.filter(interview=interview).count()}
                    )
                    assigned_count += 1
                except Interview.DoesNotExist:
                    continue
            
            return Response({
                'success': True,
                'message': f'Question assigned to {assigned_count} interviews',
                'assigned_count': assigned_count
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class InterviewViewSet(viewsets.ModelViewSet):
    """CRUD for interviews"""
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InterviewFilter
    search_fields = ['title', 'job__title', 'candidate__email']
    ordering_fields = ['scheduled_date', 'created_at', 'status']
    
    def get_serializer_class(self):
        """Use detail serializer for retrieve"""
        if self.action == 'retrieve':
            return InterviewDetailSerializer
        return InterviewSerializer
    
    def get_queryset(self):
        """Filter interviews by user role"""
        user = self.request.user
        
        if user.is_hr():
            return Interview.objects.filter(hr_user=user)
        elif user.is_job_seeker():
            return Interview.objects.filter(candidate=user)
        else:
            return Interview.objects.none()
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an interview"""
        interview = self.get_object()
        if interview.status != 'scheduled':
            return Response(
                {'error': 'Only scheduled interviews can be cancelled'},
                status=400
            )
        
        interview.status = 'cancelled'
        interview.completed_at = timezone.now()  # Use completed_at since cancelled_at doesn't exist
        interview.save()
        
        return Response({
            'success': True,
            'message': 'Interview cancelled successfully',
            'interview': InterviewSerializer(interview).data
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for an interview"""
        interview = self.get_object()
        
        # Get answers statistics
        answers = CandidateAnswer.objects.filter(
            question_set__interview=interview
        )
        
        total_questions = answers.count()
        submitted_answers = answers.filter(is_submitted=True).count()
        auto_graded = answers.filter(auto_score__gt=0).count()  # FIXED: auto_score > 0, not null
        hr_graded = answers.filter(hr_score__isnull=False).count()
        
        avg_auto_score = answers.filter(auto_score__gt=0).aggregate(
            avg=Avg('auto_score')
        )['avg'] or 0
        
        avg_hr_score = answers.filter(hr_score__isnull=False).aggregate(
            avg=Avg('hr_score')
        )['avg'] or 0
        
        return Response({
            'total_questions': total_questions,
            'submitted_answers': submitted_answers,
            'submission_rate': (submitted_answers / total_questions * 100) if total_questions > 0 else 0,
            'auto_graded': auto_graded,
            'hr_graded': hr_graded,
            'avg_auto_score': avg_auto_score,
            'avg_hr_score': avg_hr_score,
            'completion_status': interview.status
        })

class PreparationModuleViewSet(viewsets.ModelViewSet):
    """CRUD for preparation modules"""
    queryset = PreparationModule.objects.filter(is_active=True)
    serializer_class = PreparationModuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['difficulty', 'estimated_time_minutes', 'created_at']  # FIXED: field names
    
    def get_queryset(self):
        """Show only active modules"""
        return PreparationModule.objects.filter(is_active=True)
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for a preparation module"""
        module = self.get_object()
        # Modules don't have direct questions - they're related through category
        questions = InterviewQuestion.objects.filter(
            category=module.category,
            is_active=True
        )[:10]  # Limit to 10 questions
        serializer = InterviewQuestionSerializer(questions, many=True)
        return Response(serializer.data)

# ==================== API VIEWS ====================

class HRDashboardView(APIView):
    """HR Dashboard for managing interviews"""
    permission_classes = [permissions.IsAuthenticated, IsHRUser]
    
    def get(self, request):
        # Get HR's interviews
        interviews = Interview.objects.filter(
            hr_user=request.user
        ).select_related('job', 'candidate')
        
        # Statistics
        total_interviews = interviews.count()
        scheduled_interviews = interviews.filter(status='scheduled').count()
        in_progress_interviews = interviews.filter(status='in_progress').count()
        completed_interviews = interviews.filter(status='completed').count()
        
        # Upcoming interviews (next 7 days)
        upcoming = interviews.filter(
            status='scheduled',
            scheduled_date__range=[
                timezone.now(),
                timezone.now() + timezone.timedelta(days=7)
            ]
        ).order_by('scheduled_date')[:5]
        
        # Questions needing review
        needs_review = CandidateAnswer.objects.filter(
            question_set__interview__hr_user=request.user,
            hr_score__isnull=True,
            is_submitted=True
        ).count()
        
        return Response({
            'statistics': {
                'total_interviews': total_interviews,
                'scheduled': scheduled_interviews,
                'in_progress': in_progress_interviews,
                'completed': completed_interviews,
                'needs_review': needs_review
            },
            'upcoming_interviews': InterviewSerializer(upcoming, many=True).data,
            'quick_actions': [
                {
                    'name': 'Schedule Interview',
                    'url': '/hr/schedule-interview/',
                    'icon': 'calendar-plus'
                },
                {
                    'name': 'Review Answers',
                    'url': '/hr/review-answers/',
                    'icon': 'clipboard-check',
                    'badge': needs_review if needs_review > 0 else None
                },
                {
                    'name': 'Manage Questions',
                    'url': '/hr/questions/',
                    'icon': 'question-circle'
                }
            ]
        })

class ScheduleInterviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def post(self, request):
        try:
            data = request.data

            required_fields = [
                'candidate_email',
                'scheduled_date',
                'duration_minutes',
                'title',
                'job_id'
            ]

            for field in required_fields:
                if not data.get(field):
                    return Response({'error': f'{field} is required'}, status=400)

            # ✅ Candidate by EMAIL
            from accounts.models import User
            try:
                candidate = User.objects.get(
                    email=data['candidate_email'],
                    role='job_seeker',
                    is_active=True
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Candidate not found or not a job seeker'},
                    status=404
                )

            # ✅ Job
            from jobs.models import Job
            try:
                job = Job.objects.get(id=data['job_id'])
            except Job.DoesNotExist:
                return Response({'error': 'Job not found'}, status=404)

            # ✅ Parse date
            from django.utils.dateparse import parse_datetime
            scheduled_date = parse_datetime(data['scheduled_date'])
            if not scheduled_date:
                return Response({'error': 'Invalid scheduled_date format'}, status=400)

            # ✅ Create interview directly (no candidate_id anymore)
            interview = Interview.objects.create(
                title=data['title'],
                candidate=candidate,
                job=job,
                scheduled_date=scheduled_date,
                duration_minutes=int(data['duration_minutes']),
                interview_type=data.get('interview_type', 'mixed'),
                description=data.get('description', ''),
                timezone=data.get('timezone', 'UTC'),
                status='scheduled',
                hr_user=request.user
            )

            # ✅ Categories
            if data.get('categories'):
                from .models import InterviewCategory
                categories = InterviewCategory.objects.filter(id__in=data['categories'])
                interview.categories.set(categories)

            return Response({
                'success': True,
                'interview': InterviewSerializer(
                    interview,
                    context={'request': request}
                ).data
            }, status=201)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=400)



from uuid import UUID
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

class ManageInterviewQuestionsView(APIView):
    """Manage questions for a specific interview"""
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def get(self, request, interview_id):
        interview = get_object_or_404(
            Interview,
            id=interview_id,
            hr_user=request.user
        )

        question_sets = InterviewQuestionSet.objects.filter(
            interview=interview
        ).select_related(
            'question',
            'question__category'
        ).order_by('order')

        available_questions = InterviewQuestion.objects.filter(
            Q(created_by=request.user) | Q(is_active=True),
            category__in=interview.categories.all()
        ).exclude(
            id__in=question_sets.values_list('question_id', flat=True)
        )

        return Response({
            "interview": {
                "id": str(interview.id),
                "title": interview.title,
                "categories": [c.name for c in interview.categories.all()]
            },
            "assigned_questions": InterviewQuestionSetSerializer(
                question_sets, many=True
            ).data,
            "available_questions": InterviewQuestionSerializer(
                available_questions, many=True
            ).data,
        })

    def put(self, request, interview_id):
        interview = get_object_or_404(
            Interview,
            id=interview_id,
            hr_user=request.user
        )

        questions_data = request.data.get("questions")
        if not isinstance(questions_data, list) or not questions_data:
            return Response(
                {"error": "'questions' must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        mode = request.data.get("mode", "replace")  # replace | append

        parsed_questions = []
        question_ids = []

        for item in questions_data:
            if isinstance(item, dict):
                qid = item.get("question_id")
            else:
                qid = item

            if not qid:
                return Response(
                    {"error": "Each question must include 'question_id'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                q_uuid = UUID(str(qid))
            except ValueError:
                return Response(
                    {"error": f"Invalid question UUID: {qid}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            parsed_questions.append({**(item if isinstance(item, dict) else {}), "question_id": q_uuid})
            question_ids.append(q_uuid)

        questions = InterviewQuestion.objects.filter(
            id__in=question_ids,
            category__id__in=interview.categories.values_list("id", flat=True)
        ).filter(
            Q(created_by=request.user) | Q(is_active=True)
        )

        found_ids = set(q.id for q in questions)
        missing_ids = set(question_ids) - found_ids

        if missing_ids:
            return Response(
                {
                    "error": "Some questions are invalid or not accessible",
                    "missing_question_ids": [str(q) for q in missing_ids]
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        question_map = {q.id: q for q in questions}

        with transaction.atomic():
            if mode == "replace":
                InterviewQuestionSet.objects.filter(interview=interview).delete()
                start_order = 0
            else:
                start_order = InterviewQuestionSet.objects.filter(interview=interview).count()

            created = []

            for index, q_data in enumerate(parsed_questions):
                question = question_map[q_data["question_id"]]

                qs = InterviewQuestionSet.objects.create(
                    interview=interview,
                    question=question,
                    order=start_order + index,
                    required=True,
                    expected_answer_text=q_data.get("expected_answer_text"),
                    expected_keywords=q_data.get("expected_keywords"),
                    auto_score_enabled=bool(
                        q_data.get("expected_answer_text") or q_data.get("expected_keywords")
                    ),
                )
                created.append(qs.id)

        return Response(
            {
                "success": True,
                "mode": mode,
                "interview_id": str(interview.id),
                "assigned_count": len(created),
                "assigned_questions": [str(q["question_id"]) for q in parsed_questions],
            },
            status=status.HTTP_200_OK
        )



class StartInterviewView(APIView):
    """HR starts an interview"""
    permission_classes = [permissions.IsAuthenticated, IsHRUser]
    
    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                hr_user=request.user
            )
            
            if interview.status != 'scheduled':
                return Response(
                    {'error': f'Interview is already {interview.status}'},
                    status=400
                )
            
            # Start interview
            interview.status = 'in_progress'
            interview.started_at = timezone.now()
            interview.save()
            
            return Response({
                'success': True,
                'message': 'Interview started successfully',
                'interview': InterviewSerializer(interview).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class ReviewCandidateAnswersView(APIView):
    """HR interface for reviewing candidate answers"""
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def get(self, request, interview_id):
        try:
            interview = get_object_or_404(Interview, id=interview_id, hr_user=request.user)

            # Get all answers
            answers = CandidateAnswer.objects.filter(
                question_set__interview=interview,
                is_submitted=True
            ).select_related(
                'question_set__question',
                'question_set__question__category',
                'question_set__question__question_type'
            ).order_by('question_set__order')

            # Organize by category
            organized_answers = {}
            for answer in answers:
                question = answer.question_set.question
                category_name = question.category.name if question.category else "Uncategorized"

                if category_name not in organized_answers:
                    organized_answers[category_name] = []

                # Safe access to question type
                question_type = question.question_type
                q_type_code = question_type.code if question_type else None
                q_type_name = question_type.name if question_type else None

                organized_answers[category_name].append({
                    'answer_id': answer.id,
                    'question_text': question.question_text,
                    'question_type': {
                        'name': q_type_name,
                        'code': q_type_code
                    },
                    'candidate_answer': {
                        'text': answer.answer_text,
                        'selected_options': answer.selected_options,
                        'code_snippet': answer.code_snippet,
                        'file_url': answer.file_upload.url if answer.file_upload else None
                    },
                    'auto_score': getattr(answer, 'auto_score', None),
                    'hr_score': answer.hr_score,
                    'hr_feedback': answer.hr_feedback,
                    'time_taken': answer.time_taken_seconds,
                    'needs_review': answer.hr_score is None and q_type_code != 'MCQ'
                })

            return Response({
                'interview': {
                    'id': str(interview.id),
                    'title': interview.title,
                    'candidate_name': f"{interview.candidate.first_name} {interview.candidate.last_name}",
                    'candidate_email': interview.candidate.email,
                    'status': interview.status
                },
                'answers_by_category': organized_answers
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)

    
    def post(self, request, interview_id, answer_id=None):
        """Submit HR evaluation for an answer"""
        try:
            if answer_id:
                # Single answer evaluation
                answer = get_object_or_404(
                    CandidateAnswer,
                    id=answer_id,
                    question_set__interview__hr_user=request.user,
                    is_submitted=True
                )
                
                data = request.data
                
                # Validate HR score
                hr_score = data.get('hr_score')
                if hr_score is not None:
                    max_points = answer.question_set.question.points
                    if hr_score < 0 or hr_score > max_points:
                        return Response(
                            {'error': f'Score must be between 0 and {max_points}'},
                            status=400
                        )
                    
                    answer.hr_score = hr_score
                
                # Update feedback
                answer.hr_feedback = data.get('hr_feedback', '')
                answer.graded_by = request.user
                answer.graded_at = timezone.now()
                answer.save()
                
                return Response({
                    'success': True,
                    'message': 'Evaluation submitted',
                    'answer': CandidateAnswerSerializer(answer).data
                })
            else:
                # Bulk evaluation
                evaluations = request.data.get('evaluations', [])
                updated_count = 0
                
                for eval_data in evaluations:
                    answer_id = eval_data.get('answer_id')
                    hr_score = eval_data.get('hr_score')
                    hr_feedback = eval_data.get('hr_feedback', '')
                    
                    try:
                        answer = CandidateAnswer.objects.get(
                            id=answer_id,
                            question_set__interview__hr_user=request.user,
                            is_submitted=True
                        )
                        
                        if hr_score is not None:
                            max_points = answer.question_set.question.points
                            if 0 <= hr_score <= max_points:
                                answer.hr_score = hr_score
                                answer.hr_feedback = hr_feedback
                                answer.graded_by = request.user
                                answer.graded_at = timezone.now()
                                answer.save()
                                updated_count += 1
                    except CandidateAnswer.DoesNotExist:
                        continue
                
                return Response({
                    'success': True,
                    'message': f'{updated_count} answers evaluated',
                    'updated_count': updated_count
                })
                
        except Exception as e:
            return Response({'error': str(e)}, status=400)

# views.py - Update the FinalizeInterviewView

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class FinalizeInterviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview,
                id=interview_id,
                hr_user=request.user
            )

            # Interview must be running
            if interview.status != 'in_progress':
                return Response(
                    {'error': 'Interview is not in progress'},
                    status=400
                )

            # ❗ Do NOT allow finalize before time ends
            if not interview.has_time_expired():
                return Response(
                    {'error': 'Interview duration has not ended yet'},
                    status=400
                )

            with transaction.atomic():

                # ✅ Auto-submit all unanswered / unsubmitted answers
                self.auto_submit_missing_answers(interview)

                # Fetch all answers
                answers = CandidateAnswer.objects.filter(
                    question_set__interview=interview
                ).select_related(
                    'question_set__question',
                    'question_set__question__category'
                )

                total_score = 0
                max_score = 0

                for answer in answers:
                    question = answer.question_set.question
                    points = question.points or 10
                    max_score += points

                    if answer.hr_score is not None:
                        total_score += answer.hr_score
                    elif answer.auto_score is not None:
                        total_score += answer.auto_score
                    # else score = 0 (implicit)

                percentage = (
                    round((total_score / max_score) * 100, 2)
                    if max_score > 0 else 0
                )

                # Create or update result
                result, _ = InterviewResult.objects.update_or_create(
                    interview=interview,
                    candidate=interview.candidate,
                    defaults={
                        'total_score': total_score,
                        'max_score': max_score,
                        'percentage': percentage,
                        'finalized': True,
                        'finalized_at': timezone.now(),
                        'finalized_by': request.user,
                        'performance_level': self.get_performance_level(percentage),
                        'category_breakdown': self.calculate_category_breakdown(answers)
                    }
                )

                # ✅ End interview safely
                interview.end_interview()

            return Response({
                'success': True,
                'message': 'Interview finalized successfully',
                'result': {
                    'id': result.id,
                    'total_score': result.total_score,
                    'max_score': result.max_score,
                    'percentage': result.percentage,
                    'performance_level': result.performance_level,
                    'finalized_at': result.finalized_at,
                    'finalized_by': result.finalized_by.username
                }
            })

        except Exception as e:
            return Response(
                {'error': f'Failed to finalize interview: {str(e)}'},
                status=500
            )

    # -------------------------------
    # Helpers
    # -------------------------------

    def auto_submit_missing_answers(self, interview):
        """
        Ensure every question has a submitted answer
        """
        question_sets = InterviewQuestionSet.objects.filter(interview=interview)

        for qs in question_sets:
            answer, _ = CandidateAnswer.objects.get_or_create(
                question_set=qs,
                candidate=interview.candidate,
                defaults={
                    'answer_text': '',
                    'selected_options': [],
                    'auto_score': 0
                }
            )

            if not answer.is_submitted:
                answer.is_submitted = True
                answer.submitted_at = timezone.now()
                answer.save(update_fields=['is_submitted', 'submitted_at'])

    def get_performance_level(self, percentage):
        if percentage >= 90:
            return 'Excellent'
        elif percentage >= 80:
            return 'Very Good'
        elif percentage >= 70:
            return 'Good'
        elif percentage >= 60:
            return 'Average'
        elif percentage >= 50:
            return 'Below Average'
        return 'Poor'

    def calculate_category_breakdown(self, answers):
        category_data = {}

        for answer in answers:
            question = answer.question_set.question
            category = question.category.name if question.category else 'Uncategorized'

            if category not in category_data:
                category_data[category] = {
                    'score': 0,
                    'max_score': 0,
                    'count': 0
                }

            points = question.points or 10

            if answer.hr_score is not None:
                score = answer.hr_score
            elif answer.auto_score is not None:
                score = answer.auto_score
            else:
                score = 0

            category_data[category]['score'] += score
            category_data[category]['max_score'] += points
            category_data[category]['count'] += 1

        for data in category_data.values():
            data['percentage'] = (
                round((data['score'] / data['max_score']) * 100, 2)
                if data['max_score'] > 0 else 0
            )

        return category_data


class CandidateUpcomingInterviewsView(APIView):
    """Candidate gets upcoming interviews"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def get(self, request):
        try:
            interviews = Interview.objects.filter(
                candidate=request.user,
                status__in=['scheduled', 'in_progress']
            ).select_related('job', 'hr_user').order_by('scheduled_date')
            
            # Format response
            upcoming = []
            for interview in interviews:
                upcoming.append({
                    'id': str(interview.id),
                    'title': interview.title,
                    'job_title': interview.job.title if interview.job else 'General Interview',
                    'company': interview.job.company_name if interview.job else 'N/A',  # <- fixed
                    'scheduled_date': interview.scheduled_date,
                    'duration_minutes': interview.duration_minutes,
                    'status': interview.status,
                    'interview_type': interview.interview_type,
                    'categories': [cat.name for cat in interview.categories.all()],
                    'time_until': (interview.scheduled_date - timezone.now()).total_seconds() if interview.scheduled_date else None
                })


            
            return Response({
                'upcoming_interviews': upcoming,
                'count': len(upcoming)
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class CandidateStartInterviewView(APIView):
    """Candidate starts an interview"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                candidate=request.user
            )
            
            if interview.status == 'completed':
                return Response(
                    {'error': 'Interview is already completed'},
                    status=400
                )
            
            if interview.status == 'scheduled':
                # Start the interview
                interview.status = 'in_progress'
                interview.started_at = timezone.now()
                interview.save()
            
            # Get first question
            first_question = InterviewQuestionSet.objects.filter(
                interview=interview
            ).order_by('order').first()
            
            return Response({
                'success': True,
                'message': 'Interview started',
                'interview': InterviewSerializer(interview).data,
                'first_question_id': first_question.question.id if first_question else None,
                'total_questions': InterviewQuestionSet.objects.filter(interview=interview).count(),
                'start_time': interview.started_at
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class GetInterviewQuestionsView(APIView):
    """Candidate gets questions for an interview"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def get(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview,
                id=interview_id,
                candidate=request.user
            )

            # Auto-end if time has expired
            if interview.status == 'in_progress' and interview.has_time_expired():
                interview.auto_end_and_submit()
                return Response(
                    {'error': 'Interview time has expired. Your answers were auto-submitted.'},
                    status=403
                )

            # Ensure interview is active
            if interview.status not in ['in_progress', 'completed']:
                return Response(
                    {'error': 'Interview is not active'},
                    status=400
                )

            # Calculate time remaining (seconds)
            time_remaining = None
            if interview.status == 'in_progress':
                # Use get_end_time() method instead of end_time field
                end_time = interview.get_end_time()
                if end_time:
                    delta = end_time - timezone.now()
                    time_remaining = max(0, int(delta.total_seconds()))
                else:
                    # If no end_time calculated, use duration from scheduled date
                    if interview.started_at:
                        end_time = interview.started_at + timezone.timedelta(minutes=interview.duration_minutes)
                        delta = end_time - timezone.now()
                        time_remaining = max(0, int(delta.total_seconds()))
                    else:
                        time_remaining = interview.duration_minutes * 60  # Full duration if not started yet

            # Fetch questions efficiently
            question_sets = InterviewQuestionSet.objects.filter(
                interview=interview
            ).select_related('question', 'question__category').order_by('order')

            questions = []
            for qs in question_sets:
                question = qs.question
                questions.append({
                    'id': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type.code if question.question_type else None,
                    'category': question.category.name,
                    'difficulty': question.difficulty,
                    'points': question.points,
                    'time_limit_minutes': question.time_limit_minutes,
                    'order': qs.order,
                    'has_answer': CandidateAnswer.objects.filter(
                        question_set=qs,
                        candidate=request.user,
                        is_submitted=True
                    ).exists()
                })

            # Count submitted answers
            answered_count = CandidateAnswer.objects.filter(
                question_set__interview=interview,
                candidate=request.user,
                is_submitted=True
            ).count()

            return Response({
                'interview': {
                    'id': str(interview.id),
                    'title': interview.title,
                    'status': interview.status,
                    'time_remaining': time_remaining
                },
                'questions': questions,
                'total_questions': len(questions),
                'answered_count': answered_count
            })

        except Exception as e:
            return Response({'error': str(e)}, status=400)



class SubmitAnswerView(APIView):
    """Candidate submits one or multiple answers safely"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def post(self, request, interview_id):
        print("request.data type:", type(request.data))
        print("request.data:", request.data)
        
        try:
            # Fetch interview
            interview = get_object_or_404(
                Interview,
                id=interview_id,
                candidate=request.user
            )

            if interview.status != 'in_progress':
                return Response({'error': 'Interview is not in progress'}, status=400)

            # 🔒 AUTO-END INTERVIEW IF TIME EXPIRED
            if interview.has_time_expired():
                self.auto_end_interview(interview)
                return Response(
                    {'error': 'Interview time has expired. Your answers were auto-submitted.'},
                    status=403
    )

            payload = request.data
            print("Initial payload type:", type(payload))
            
            # Check if payload is a string that needs parsing
            if isinstance(payload, str):
                try:
                    import json
                    payload = json.loads(payload)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    return Response({"error": "Invalid JSON payload"}, status=400)

            print("Parsed payload type:", type(payload))
            print("Parsed payload:", payload)

            # Determine if single or multiple answers
            answers_list = []
            
            if isinstance(payload, dict):
                if "answers" in payload:
                    # Format: {"answers": [...]}
                    answers_list = payload["answers"]
                    if not isinstance(answers_list, list):
                        return Response({"error": "'answers' must be a list of objects"}, status=400)
                elif "question_id" in payload:
                    # Format: {"question_id": "...", ...}
                    answers_list = [payload]
                else:
                    return Response({"error": "Invalid payload format. Must contain 'question_id' or 'answers' key"}, status=400)
            elif isinstance(payload, list):
                # Format: [...]
                answers_list = payload
            else:
                return Response({"error": f"Invalid payload format. Expected dict or list, got {type(payload)}"}, status=400)

            print(f"Processing {len(answers_list)} answer(s)")

            submitted_answers = []

            for ans_data in answers_list:
                # Double check that ans_data is a dictionary
                if not isinstance(ans_data, dict):
                    print(f"Invalid ans_data type: {type(ans_data)}, value: {ans_data}")
                    return Response({"error": f"Each answer must be an object, got {type(ans_data)}"}, status=400)

                question_id = ans_data.get("question_id")
                if not question_id:
                    return Response({"error": "question_id is required for each answer"}, status=400)

                print(f"\nProcessing question_id: {question_id}")

                try:
                    question_uuid = UUID(question_id)
                except ValueError as e:
                    return Response({"error": f"Invalid question_id format: {str(e)}"}, status=400)

                # Get question set
                try:
                    question_set = InterviewQuestionSet.objects.get(
                        interview=interview,
                        question__id=question_uuid
                    )
                except InterviewQuestionSet.DoesNotExist:
                    return Response({"error": f"Question not found in this interview: {question_id}"}, status=404)

                # Prepare answer data - ensure selected_options is a list
                answer_text = ans_data.get('answer_text', '')
                selected_options = ans_data.get('selected_options', [])
                
                # Ensure selected_options is a list
                if not isinstance(selected_options, list):
                    if selected_options is not None:
                        selected_options = [selected_options]
                    else:
                        selected_options = []
                
                # Filter out None values
                selected_options = [opt for opt in selected_options if opt is not None]
                
                code_snippet = ans_data.get('code_snippet', '')
                time_taken_seconds = ans_data.get('time_taken_seconds', 0)
                
                answer_data = {
                    'answer_text': answer_text,
                    'selected_options': selected_options,
                    'code_snippet': code_snippet,
                    'time_taken_seconds': time_taken_seconds,
                    'is_submitted': True,
                    'submitted_at': timezone.now()
                }
                
                # Handle file upload
                if 'file_upload' in request.FILES:
                    answer_data['file_upload'] = request.FILES['file_upload']

                # Create or update answer
                answer, created = CandidateAnswer.objects.get_or_create(
                    question_set=question_set,
                    candidate=request.user,
                )
                # Always update fields from API
                answer.answer_text = answer_text
                answer.selected_options = selected_options
                answer.code_snippet = code_snippet
                answer.time_taken_seconds = time_taken_seconds
                answer.is_submitted = True
                answer.submitted_at = timezone.now()
                answer.save()


                if not created:
                    answer.answer_text = answer_text
                    answer.selected_options = selected_options
                    answer.code_snippet = code_snippet
                    answer.time_taken_seconds = time_taken_seconds
                    if 'file_upload' in request.FILES:
                        answer.file_upload = request.FILES['file_upload']
                    answer.is_submitted = True
                    answer.submitted_at = timezone.now()
                    answer.save()

                # Auto-score
                try:
                    print(f"\n--- Calculating auto score for answer {answer.id} ---")
                    auto_score = answer.calculate_auto_score()
                    print(f"Auto score result: {auto_score}")
                    
                    if auto_score is not None:
                        answer.auto_score = auto_score
                        answer.save(update_fields=['auto_score'])
                        print(f"Saved auto score: {auto_score}")
                    else:
                        print("Auto score returned None (manual grading required)")
                except Exception as e:
                    print(f"Auto-scoring error for answer {answer.id}: {e}")
                    import traceback
                    traceback.print_exc()

                submitted_answers.append({
                    'answer_id': str(answer.id),
                    'question_id': question_id,
                    'auto_score': answer.auto_score,
                    'submitted_at': answer.submitted_at
                })

            return Response({
                'success': True,
                'message': f"{len(submitted_answers)} answer(s) submitted successfully",
                'submitted_answers': submitted_answers
            })

        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=400)
    def auto_end_interview(self, interview):
        question_sets = InterviewQuestionSet.objects.filter(interview=interview)

        for qs in question_sets:
            answer, _ = CandidateAnswer.objects.get_or_create(
                question_set=qs,
                candidate=interview.candidate,
                defaults={
                    'answer_text': '',
                    'auto_score': 0
                }
            )

            if not answer.is_submitted:
                answer.is_submitted = True
                answer.submitted_at = timezone.now()
                answer.save(update_fields=['is_submitted', 'submitted_at'])

        interview.end_interview()

        
class SubmitAllAnswersView(APIView):
    """Candidate submits all answers at once"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                candidate=request.user
            )
            
            if interview.status != 'in_progress':
                return Response(
                    {'error': 'Interview is not in progress'},
                    status=400
                )
            # 🔒 AUTO-END INTERVIEW IF TIME EXPIRED
            if interview.has_time_expired():
                self.auto_end_interview(interview)
                return Response(
                    {'error': 'Interview time has expired. Your answers were auto-submitted.'},
                    status=403
                )

            
            answers_data = request.data.get('answers', [])
            submitted_count = 0
            
            for answer_data in answers_data:
                question_id = answer_data.get('question_id')
                if not question_id:
                    continue
                
                try:
                    question_set = InterviewQuestionSet.objects.get(
                        interview=interview,
                        question_id=question_id
                    )
                    
                    answer, created = CandidateAnswer.objects.get_or_create(
                        question_set=question_set,
                        candidate=request.user,
                        defaults={
                            'answer_text': answer_data.get('answer_text', ''),
                            'selected_options': answer_data.get('selected_options', []),
                            'code_snippet': answer_data.get('code_snippet', ''),
                            'time_taken_seconds': answer_data.get('time_taken_seconds', 0),
                            'is_submitted': True,
                            'submitted_at': timezone.now()
                        }
                    )
                    
                    if not created:
                        answer.answer_text = answer_data.get('answer_text', answer.answer_text)
                        answer.selected_options = answer_data.get('selected_options', answer.selected_options)
                        answer.code_snippet = answer_data.get('code_snippet', answer.code_snippet)
                        answer.time_taken_seconds = answer_data.get('time_taken_seconds', answer.time_taken_seconds)
                        answer.is_submitted = True
                        answer.submitted_at = timezone.now()
                        answer.save()
                    
                    submitted_count += 1
                    
                except InterviewQuestionSet.DoesNotExist:
                    continue
            
            # Mark interview as completed if all questions answered
            total_questions = InterviewQuestionSet.objects.filter(interview=interview).count()
            answered_count = CandidateAnswer.objects.filter(
                question_set__interview=interview,
                candidate=request.user,
                is_submitted=True
            ).count()
            
            return Response({
                'success': True,
                'message': f'{submitted_count} answers submitted',
                'submitted_count': submitted_count,
                'total_answered': answered_count,
                'interview_status': interview.status
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    def auto_end_interview(self, interview):
        question_sets = InterviewQuestionSet.objects.filter(interview=interview)

        for qs in question_sets:
            answer, _ = CandidateAnswer.objects.get_or_create(
                question_set=qs,
                candidate=interview.candidate,
                defaults={
                    'answer_text': '',
                    'auto_score': 0
                }
            )

            if not answer.is_submitted:
                answer.is_submitted = True
                answer.submitted_at = timezone.now()
                answer.save(update_fields=['is_submitted', 'submitted_at'])

        interview.end_interview()


class GetInterviewResultView(APIView):
    """Candidate gets interview result"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def get(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                candidate=request.user
            )
            
            if interview.status != 'completed':
                return Response(
                    {'error': 'Interview results are not available yet'},
                    status=400
                )
            
            # Get all answers with scores
            answers = CandidateAnswer.objects.filter(
                question_set__interview=interview,
                candidate=request.user,
                is_submitted=True
            ).select_related(
                'question_set__question',
                'question_set__question__category'
            )
            
            # Calculate statistics
            total_score = 0
            max_possible_score = 0
            category_scores = {}
            
            for answer in answers:
                question = answer.question_set.question
                category = question.category.name
                
                # Use HR score if available, otherwise auto score
                score = answer.hr_score if answer.hr_score is not None else answer.auto_score
                if score is not None:
                    total_score += score
                    max_possible_score += question.points
                    
                    if category not in category_scores:
                        category_scores[category] = {
                            'total': 0,
                            'max': 0,
                            'count': 0
                        }
                    
                    category_scores[category]['total'] += score
                    category_scores[category]['max'] += question.points
                    category_scores[category]['count'] += 1
            
            # Calculate percentages
            overall_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
            
            category_results = []
            for category, data in category_scores.items():
                percentage = (data['total'] / data['max'] * 100) if data['max'] > 0 else 0
                category_results.append({
                    'category': category,
                    'score': f"{data['total']}/{data['max']}",
                    'percentage': percentage,
                    'count': data['count']
                })
            
            # Simple performance level
            performance_level = 'Excellent' if overall_percentage >= 80 else \
                               'Good' if overall_percentage >= 60 else \
                               'Fair' if overall_percentage >= 40 else 'Needs Improvement'
            
            return Response({
                'interview': {
                    'id': str(interview.id),
                    'title': interview.title,
                    'overall_score': f"{total_score}/{max_possible_score}",
                    'overall_percentage': overall_percentage
                },
                'category_results': category_results,
                'answers': CandidateAnswerSerializer(answers, many=True).data,
                'performance_level': performance_level
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class PreparationRecommendationsView(APIView):
    """Get personalized preparation recommendations"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Check if user has completed profile
            if not user.first_name or not user.last_name:
                return Response({
                    'error': 'Please complete your profile first',
                    'action_required': 'complete_profile',
                    'redirect_url': '/profile/edit/'
                }, status=400)
            
            # Simple recommendations based on user role
            if user.is_job_seeker():
                # Get categories for upcoming interviews
                upcoming_categories = Interview.objects.filter(
                    candidate=user,
                    status='scheduled'
                ).values_list('categories__name', flat=True).distinct()
                
                recommendations = []
                for category in upcoming_categories:
                    if category:
                        modules = PreparationModule.objects.filter(
                            category__name=category,
                            is_active=True
                        )[:3]
                        if modules.exists():
                            recommendations.append({
                                'category': category,
                                'modules': PreparationModuleSerializer(modules, many=True).data
                            })
                
                if not recommendations:
                    # Default recommendations
                    default_modules = PreparationModule.objects.filter(
                        is_active=True
                    ).order_by('?')[:5]  # Random 5 modules
                    
                    recommendations = [{
                        'category': 'General Preparation',
                        'modules': PreparationModuleSerializer(default_modules, many=True).data
                    }]
                
                return Response({
                    'recommendations': recommendations,
                    'upcoming_categories': list(upcoming_categories)
                })
            
            return Response({
                'error': 'Only job seekers can get preparation recommendations'
            }, status=400)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get recommendations: {str(e)}'},
                status=400
            )

class StartPreparationModuleView(APIView):
    """Candidate starts a preparation module"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, module_id):
        try:
            module = get_object_or_404(PreparationModule, id=module_id, is_active=True)
            
            # Start or resume module
            progress, created = UserPreparationProgress.objects.get_or_create(
                user=request.user,
                module=module,
                defaults={
                    'status': 'in_progress',
                    'last_accessed': timezone.now()
                }
            )
            
            if not created and progress.status == 'completed':
                # Reset if re-starting
                progress.status = 'in_progress'
                progress.progress_percentage = 0
                progress.last_accessed = timezone.now()
                progress.save()
            
            return Response({
                'success': True,
                'message': 'Preparation module started',
                'module': PreparationModuleSerializer(module).data,
                'progress': UserPreparationProgressSerializer(progress).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class CompletePreparationModuleView(APIView):
    """Candidate completes a preparation module"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, module_id):
        try:
            module = get_object_or_404(PreparationModule, id=module_id)
            
            progress = get_object_or_404(
                UserPreparationProgress,
                user=request.user,
                module=module
            )
            
            data = request.data
            score = data.get('score', 0)
            
            # Complete module
            progress.status = 'completed'
            progress.completed_at = timezone.now()
            progress.progress_percentage = 100
            progress.notes = data.get('notes', '')
            progress.save()
            
            return Response({
                'success': True,
                'message': 'Preparation module completed',
                'module': PreparationModuleSerializer(module).data,
                'progress': UserPreparationProgressSerializer(progress).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class PreparationProgressView(APIView):
    """Get candidate's preparation progress"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Get all progress records
            progress_records = UserPreparationProgress.objects.filter(
                user=user
            ).select_related('module', 'module__category').order_by('-last_accessed')
            
            # Calculate statistics
            completed = progress_records.filter(status='completed').count()
            in_progress = progress_records.filter(status='in_progress').count()
            total_modules = progress_records.count()
            
            avg_progress = progress_records.aggregate(
                avg=Avg('progress_percentage')
            )['avg'] or 0
            
            # Get recent activity
            recent_activity = progress_records[:5]
            
            return Response({
                'statistics': {
                    'total_modules': total_modules,
                    'completed': completed,
                    'in_progress': in_progress,
                    'completion_rate': (completed / total_modules * 100) if total_modules > 0 else 0,
                    'average_progress': avg_progress
                },
                'recent_activity': UserPreparationProgressSerializer(recent_activity, many=True).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class ManageAvailabilityView(APIView):
    """Manage candidate availability"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def get(self, request):
        try:
            availability_slots = AvailabilitySlot.objects.filter(
                user=request.user
            ).order_by('start_time')
            
            # Create a simple serializer
            slots_data = []
            for slot in availability_slots:
                slots_data.append({
                    'id': slot.id,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time,
                    'is_available': slot.is_available
                })
            
            return Response({
                'availability': slots_data,
                'count': availability_slots.count()
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)
    
    def post(self, request):
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['start_time', 'end_time']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'{field} is required'},
                        status=400
                    )
            
            # Parse dates
            from django.utils.dateparse import parse_datetime
            start_time = parse_datetime(data['start_time'])
            end_time = parse_datetime(data['end_time'])
            
            if not start_time or not end_time:
                return Response(
                    {'error': 'Invalid date format. Use ISO 8601'},
                    status=400
                )
            
            if start_time >= end_time:
                return Response(
                    {'error': 'Start time must be before end time'},
                    status=400
                )
            
            # Check for overlaps
            overlapping = AvailabilitySlot.objects.filter(
                user=request.user,
                start_time__lt=end_time,
                end_time__gt=start_time,
                is_available=True
            ).exists()
            
            if overlapping:
                return Response(
                    {'error': 'This time slot overlaps with existing availability'},
                    status=400
                )
            
            # Create availability slot
            availability = AvailabilitySlot.objects.create(
                user=request.user,
                start_time=start_time,
                end_time=end_time,
                is_available=data.get('is_available', True)
            )
            
            return Response({
                'success': True,
                'message': 'Availability added successfully',
                'availability': {
                    'id': availability.id,
                    'start_time': availability.start_time,
                    'end_time': availability.end_time,
                    'is_available': availability.is_available
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class CheckSchedulingConflictsView(APIView):
    """Check for scheduling conflicts"""
    permission_classes = [permissions.IsAuthenticated, IsHRUser]
    
    def post(self, request):
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['candidate_email', 'proposed_time', 'duration_minutes']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'{field} is required'},
                        status=400
                    )
            
            # Parse date
            from django.utils.dateparse import parse_datetime
            proposed_time = parse_datetime(data['proposed_time'])
            if not proposed_time:
                return Response(
                    {'error': 'Invalid date format. Use ISO 8601'},
                    status=400
                )
            
            # Get candidate
            from accounts.models import User
            try:
                candidate = User.objects.get(
                email=data['candidate_email'],
                role='job_seeker',
                is_active=True
            )

            except User.DoesNotExist:
                return Response(
                    {'error': 'Candidate not found'},
                    status=404
                )
            
            # Calculate end time
            end_time = proposed_time + timezone.timedelta(minutes=int(data['duration_minutes']))
            
            # Check conflicts with existing interviews
            interview_conflicts = Interview.objects.filter(
                candidate=candidate,
                status__in=['scheduled', 'in_progress'],
                scheduled_date__lt=end_time,
                scheduled_date__gt=proposed_time - timezone.timedelta(minutes=int(data['duration_minutes']))
            )
            
            # Check conflicts with availability
            availability_conflicts = AvailabilitySlot.objects.filter(
                user=candidate,
                is_available=False,
                start_time__lt=end_time,
                end_time__gt=proposed_time
            )
            
            conflicts = []
            for interview in interview_conflicts:
                conflicts.append(f"Has interview: {interview.title} at {interview.scheduled_date}")
            
            for slot in availability_conflicts:
                conflicts.append(f"Unavailable: {slot.start_time} to {slot.end_time}")
            
            return Response({
                'has_conflicts': bool(conflicts),
                'conflicts': conflicts,
                'is_available': len(conflicts) == 0,
                'proposed_time': proposed_time,
                'candidate_name': f"{candidate.first_name} {candidate.last_name}"
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class ImportQuestionsView(APIView):
    """Admin imports questions from CSV/JSON"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=400
                )
            
            import_file = request.FILES['file']
            import_format = request.data.get('format', 'csv')
            category_id = request.data.get('category_id')
            
            if not category_id:
                return Response(
                    {'error': 'category_id is required'},
                    status=400
                )
            
            # Get category
            category = get_object_or_404(InterviewCategory, id=category_id)
            
            # Simple import logic (you should implement proper CSV/JSON parsing)
            # For now, just create a dummy question
            question = InterviewQuestion.objects.create(
                category=category,
                question_text=f"Imported question from {import_file.name}",
                difficulty='medium',
                points=10,
                created_by=request.user,
                question_type=QuestionType.objects.first() or QuestionType.objects.create(
                    name='Descriptive',
                    code='DESC',
                    requires_answer_key=True
                )
            )
            
            return Response({
                'success': True,
                'message': 'Question imported successfully',
                'question': InterviewQuestionSerializer(question).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class InterviewAnalyticsView(APIView):
    """Get interview analytics"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get(self, request):
        try:
            # Get date range
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            
            # Filter interviews
            interviews = Interview.objects.all()
            
            if from_date:
                interviews = interviews.filter(created_at__gte=from_date)
            if to_date:
                interviews = interviews.filter(created_at__lte=to_date)
            
            # Calculate statistics
            total_interviews = interviews.count()
            completed_interviews = interviews.filter(status='completed').count()
            cancelled_interviews = interviews.filter(status='cancelled').count()
            
            # Average duration
            avg_duration = interviews.filter(duration_minutes__isnull=False).aggregate(
                avg=Avg('duration_minutes')
            )['avg'] or 0
            
            # Category distribution
            from django.db.models import Count
            category_distribution = InterviewCategory.objects.annotate(
                interview_count=Count('interviews')
            ).values('name', 'interview_count').order_by('-interview_count')[:10]
            
            return Response({
                'overview': {
                    'total_interviews': total_interviews,
                    'completed': completed_interviews,
                    'cancelled': cancelled_interviews,
                    'completion_rate': (completed_interviews / total_interviews * 100) if total_interviews > 0 else 0,
                    'average_duration_minutes': avg_duration
                },
                'category_distribution': list(category_distribution),
                'time_period': {
                    'from_date': from_date,
                    'to_date': to_date
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsHRUser
from .models import Interview, CandidateAnswer
from .serializers import CandidateAnswerSerializer, InterviewSerializer

# ---------------- View candidate answers ----------------
class ReviewCandidateAnswersView(APIView):
    permission_classes = [IsAuthenticated, IsHRUser]

    def get(self, request, interview_id):
        interview = Interview.objects.filter(id=interview_id, hr_user=request.user).first()
        if not interview:
            return Response({"error": "Interview not found or not authorized"}, status=404)

        # Fetch all answers via related question sets
        answers = CandidateAnswer.objects.filter(question_set__interview=interview)
        serializer = CandidateAnswerReviewSerializer(answers, many=True)
        return Response(serializer.data)



# ---------------- View interview result ----------------
class InterviewResultView(APIView):
    permission_classes = [IsAuthenticated, IsHRUser]

    def get(self, request, interview_id):
        interview = Interview.objects.filter(id=interview_id, hr_user=request.user).first()
        if not interview:
            return Response({"error": "Interview not found or not authorized"}, status=404)

        answers = CandidateAnswer.objects.filter(question_set__interview=interview)
        serializer = CandidateAnswerSerializer(answers, many=True)

        total_score = sum(
            a.hr_score if a.hr_score is not None else a.auto_score or 0
            for a in answers
        )

        max_score = sum(
            a.question_set.question.points or 0
            for a in answers
        )

        percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0

        result = {
            "interview": InterviewSerializer(interview).data,
            "answers": serializer.data,
            "total_score": total_score,
            "max_score": max_score,
            "percentage": percentage
        }
        return Response(result)


# ---------------- Finalize interview ----------------
# views.py
# views.py
from interview.services1 import calculate_interview_result
from .models import InterviewResult

class FinalizeInterviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def post(self, request, interview_id):
        interview = get_object_or_404(
            Interview,
            id=interview_id,
            hr_user=request.user
        )

        # ✅ ALLOW FINALIZATION FROM ANY NON-FINAL STATUS
        # Accept: 'draft', 'scheduled', 'in_progress', 'submitted'
        if interview.status in ['completed', 'cancelled']:
            if interview.status == 'completed':
                # Check if result already exists
                try:
                    existing_result = InterviewResult.objects.get(
                        interview=interview,
                        candidate=interview.candidate
                    )
                    return Response({
                        'success': False,
                        'message': 'Interview is already completed',
                        'existing_result': {
                            'total_score': existing_result.total_score,
                            'max_score': existing_result.max_score,
                            'percentage': existing_result.percentage,
                            'performance_level': existing_result.performance_level,
                            'finalized_at': existing_result.finalized_at
                        }
                    }, status=400)
                except InterviewResult.DoesNotExist:
                    pass
                
                return Response(
                    {'error': 'Interview is already completed'},
                    status=400
                )
            else:
                return Response(
                    {'error': 'Interview has been cancelled'},
                    status=400
                )

        print(f"Finalizing interview: {interview_id}")
        print(f"Current status: {interview.status}")
        print(f"Transitioning from {interview.status} to 'completed'")

        # 🔥 Calculate & store final result
        try:
            result = calculate_interview_result(
                interview=interview,
                candidate=interview.candidate,
                hr_user=request.user
            )
            print(f"Result calculated: {result.total_score}/{result.max_score} = {result.percentage}%")
        except Exception as e:
            print(f"Error calculating result: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to calculate interview result: {str(e)}'},
                status=500
            )

        # Update interview status
        previous_status = interview.status
        interview.status = 'completed'
        interview.completed_at = timezone.now()
        interview.save()
        
        print(f"Status changed: {previous_status} → {interview.status}")

        return Response({
            'success': True,
            'message': f'Interview finalized and scored (from {previous_status} status)',
            'result': {
                'id': str(result.id),
                'total_score': result.total_score,
                'max_score': result.max_score,
                'percentage': result.percentage,
                'performance_level': result.performance_level,
                'category_breakdown': result.category_breakdown
            },
            'interview': {
                'id': str(interview.id),
                'title': interview.title,
                'previous_status': previous_status,
                'new_status': interview.status,
                'completed_at': interview.completed_at
            }
        })


# ---------------- HR Dashboard ----------------
class HRDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsHRUser]

    def get(self, request):
        total_jobs = Interview.objects.filter(hr_user=request.user).count()
        total_applications = sum(job.applications.count() for job in Job.objects.filter(hr_user=request.user))
        scheduled_interviews = Interview.objects.filter(status="scheduled", hr_user=request.user).count()
        completed_interviews = Interview.objects.filter(status="completed", hr_user=request.user).count()

        return Response({
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "scheduled_interviews": scheduled_interviews,
            "completed_interviews": completed_interviews
        })

from .models import CandidateAnswer
from .serializers import CandidateAnswerSerializer
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import IsHRUser

class GradeCandidateAnswerView(APIView):
    """HR assigns score and optional feedback to a candidate's answer"""
    permission_classes = [IsAuthenticated, IsHRUser]

    def post(self, request, answer_id):
        try:
            answer = CandidateAnswer.objects.get(id=answer_id)
            
            # Check HR authorization
            if answer.question_set.interview.hr_user != request.user:
                return Response({"error": "Not authorized to grade this answer"}, status=403)
            
            data = request.data
            score = data.get('score')
            feedback = data.get('feedback', '')

            if score is None:
                return Response({"error": "Score is required"}, status=400)
            
            # Update the answer
            answer.hr_score = score
            answer.hr_feedback = feedback
            answer.graded_at = timezone.now()
            answer.save()

            return Response({
                "success": True,
                "message": "Score updated",
                "answer": CandidateAnswerSerializer(answer).data
            })

        except CandidateAnswer.DoesNotExist:
            return Response({"error": "Answer not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# In views.py
class StartInterviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]
    
    def post(self, request, interview_id):
        try:
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                hr_user=request.user,
                status='scheduled'  # Only start scheduled interviews
            )
            
            # Check if it's time to start
            buffer_time = timezone.timedelta(minutes=15)
            if timezone.now() < (interview.scheduled_date - buffer_time):
                return Response({
                    "error": "Interview cannot be started yet. Please wait until 15 minutes before scheduled time."
                }, status=400)
            
            # Update status
            interview.start_interview()

            
            # TODO: Send notification to candidate
            
            return Response({
                "success": True,
                "message": "Interview started successfully",
                "interview_id": str(interview.id),
                "status": interview.status
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        


# views.py
class BulkInterviewQuestionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def post(self, request):
        questions = request.data.get("questions")

        if not isinstance(questions, list) or not questions:
            return Response(
                {"error": "'questions' must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InterviewQuestionSerializer(
            data=questions,
            many=True,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "created": len(serializer.data),
                "questions": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


# Add to views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from .models import Interview
from .serializers import InterviewSerializer, InterviewDetailSerializer
from .permissions import IsCandidate, IsHRUser as IsHR

class GetInterviewDetailView(APIView):
    """Get interview details (generic endpoint)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, interview_id):
        try:
            interview = get_object_or_404(Interview, id=interview_id)
            
            # Check permissions
            user = request.user
            if user.role == 'candidate' and interview.candidate != user:
                return Response({'error': 'Permission denied'}, status=403)
            elif user.role == 'hr' and interview.hr_user != user:
                return Response({'error': 'Permission denied'}, status=403)
            
            # Return detailed serializer if user has access
            serializer = InterviewDetailSerializer(interview)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class GetCandidateInterviewDetailView(APIView):
    """Get interview details specifically for candidate"""
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    
    def get(self, request, interview_id):
        try:
            # Only return if the candidate owns this interview
            interview = get_object_or_404(
                Interview, 
                id=interview_id, 
                candidate=request.user
            )
            
            serializer = InterviewDetailSerializer(interview)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        


class HRInterviewResultsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def get(self, request, interview_id):
        results = InterviewResult.objects.filter(
            interview_id=interview_id
        ).select_related('candidate')

        return Response({
            "results": [
                {
                    "candidate": r.candidate.get_full_name(),
                    "email": r.candidate.email,
                    "score": f"{r.total_score}/{r.max_score}",
                    "percentage": r.percentage,
                    "performance_level": r.performance_level
                }
                for r in results
            ]
        })




#### For interview Preparation of the Candidate w.r.t Job Description####
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from jobs.models import JobApplication, Job
from interview.models import InterviewPreparation, InterviewChatSession, InterviewChatMessage
from interview.services.interview_preparation_ai import InterviewPreparationGenerator


# ======================================================
# 🎯 INTERVIEW PREPARATION (GET)
# ======================================================

class CandidateInterviewPreparationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "job_seeker":
            return Response(
                {"error": "Only job seekers can access interview preparation"},
                status=status.HTTP_403_FORBIDDEN
            )

        applications = JobApplication.objects.filter(
            applicant=user
        ).select_related("job")

        if not applications.exists():
            return Response(
                {"error": "No applied jobs found"},
                status=status.HTTP_404_NOT_FOUND
            )

        generator = InterviewPreparationGenerator()
        results = []

        for app in applications:
            job = app.job
            if not job:
                continue

            # ✅ Cache per job
            prep, created = InterviewPreparation.objects.get_or_create(
                user=user,
                job=job,
                defaults={
                    "preparation_data": generator.generate_preparation(
                        job_title=job.title,
                        job_description=job.description,
                        company_name=job.company_name
                    )
                }
            )

            results.append({
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company_name,
                "interview_preparation": prep.preparation_data
            })

        return Response({
            "count": len(results),
            "data": results
        })


# ======================================================
# 🔁 GENERATE MORE QUESTIONS (POST)
# ======================================================

class GenerateMoreInterviewQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        job_id = request.data.get("job_id")

        if user.role != "job_seeker":
            return Response({"error": "Unauthorized"}, status=403)

        prep = InterviewPreparation.objects.filter(
            user=user,
            job_id=job_id
        ).first()

        if not prep:
            return Response({"error": "Preparation not found"}, status=404)

        generator = InterviewPreparationGenerator()

        extra_questions = generator.generate_more_questions(
            job_title=prep.job.title,
            job_description=prep.job.description
        )

        # Merge into existing preparation
        for key, value in extra_questions.items():
            prep.preparation_data.setdefault(key, []).extend(value)

        prep.save()

        return Response({
            "message": "More questions generated successfully",
            "new_questions": extra_questions
        })


# ======================================================
# 💬 MOCK INTERVIEW CHAT (POST)
# ======================================================

class InterviewChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        job_id = request.data.get("job_id")
        message = request.data.get("message")

        if user.role != "job_seeker":
            return Response({"error": "Unauthorized"}, status=403)

        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response({"error": "Job not found"}, status=404)

        session, _ = InterviewChatSession.objects.get_or_create(
            user=user,
            job=job
        )

        InterviewChatMessage.objects.create(
            session=session,
            role="user",
            message=message
        )

        generator = InterviewPreparationGenerator()
        ai_reply = generator.chat_reply(
            job_title=job.title,
            job_description=job.description,
            user_message=message
        )

        InterviewChatMessage.objects.create(
            session=session,
            role="assistant",
            message=ai_reply
        )

        return Response({
            "reply": ai_reply
        })



from interview.models import MockInterviewSession, MockInterviewAnswer
from interview.services.mock_interview_ai import MockInterviewAI
from jobs.models import Job


class MockInterviewSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.role != "job_seeker":
            return Response({"error": "Unauthorized"}, status=403)

        job_id = request.data.get("job_id")
        answers = request.data.get("answers")  # Expect a list of {"question_index": int, "answer": str}

        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response({"error": "Job not found"}, status=404)

        ai = MockInterviewAI()

        # 🔹 START NEW SESSION
        if not answers:
            questions = ai.generate_questions(
                job_title=job.title,
                job_description=job.description,
                difficulty=request.data.get("difficulty", "medium"),
                interview_type=request.data.get("interview_type", "technical"),
                total_questions=request.data.get("total_questions", 10)
            )

            session = MockInterviewSession.objects.create(
                user=user,
                job=job,
                questions=questions,
                difficulty=request.data.get("difficulty", "medium"),
                interview_type=request.data.get("interview_type", "technical"),
                total_questions=len(questions)
            )

            return Response({
                "session_id": session.id,
                "questions": [ai.sanitize_question(q) for q in questions]
            })

        # 🔹 SUBMIT ALL ANSWERS
        session = MockInterviewSession.objects.filter(
            id=request.data.get("session_id"),
            user=user
        ).first()
        if not session:
            return Response({"error": "Session not found"}, status=404)

        results = []
        for item in answers:
            idx = item.get("question_index")
            ans = item.get("answer")
            if idx is None or idx >= len(session.questions):
                continue

            question = session.questions[idx]
            evaluation = ai.evaluate_answer(
                job_title=job.title,
                job_description=job.description,
                question=question,
                candidate_answer=ans
            )

            MockInterviewAnswer.objects.update_or_create(
                session=session,
                question_index=idx,
                defaults={
                    "question": ai.sanitize_question(question),
                    "answer": ans,
                    "feedback": evaluation["feedback"],
                    "score": evaluation["score"]
                }
            )

            results.append({
                "question": question["question"],
                "answer": ans,
                "feedback": evaluation["feedback"],
                "score": evaluation["score"]
            })

        session.is_completed = True
        session.save()

        return Response({
            "completed": True,
            "results": results
        })



class MockInterviewProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        user = request.user

        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response({"error": "Job not found"}, status=404)

        sessions = MockInterviewSession.objects.filter(
            user=user,
            job=job,
            is_completed=True
        ).order_by("created_at")

        if not sessions.exists():
            return Response({
                "job_id": job.id,
                "job_title": job.title,
                "sessions_completed": 0,
                "progress_percentage": 0,
                "progress": []
            })

        progress_data = []
        percentages = []

        for session in sessions:
            answers = MockInterviewAnswer.objects.filter(session=session)

            total_score = sum(a.score for a in answers)
            max_score = len(answers) * 100

            percentage = round((total_score / max_score) * 100, 2) if max_score else 0
            percentages.append(percentage)

            progress_data.append({
                "session_id": session.id,
                "date": session.created_at,
                "score_percentage": percentage
            })

        average_progress = round(sum(percentages) / len(percentages), 2)

        return Response({
            "job_id": job.id,
            "job_title": job.title,
            "sessions_completed": len(progress_data),
            "progress_percentage": average_progress,
            "progress": progress_data
        })

