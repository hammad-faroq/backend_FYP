# interviews/services/interview_service.py
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)

class InterviewService:
    """Service class for interview management"""

    @staticmethod
    def schedule_interview(job, hr_user, candidate, scheduled_date, duration_minutes, categories, interview_type='mixed'):
        from ..models import Interview, AvailabilitySlot

        # 1. Validate participants
        if hr_user.role != 'hr':
            raise ValidationError("Only HR users can schedule interviews")

        if candidate.role != 'job_seeker':
            raise ValidationError("Candidate must be a job seeker")

        # 2. Check scheduling conflicts
        conflict_end_time = scheduled_date + timezone.timedelta(minutes=duration_minutes)

        # Check HR availability
        hr_conflicts = AvailabilitySlot.objects.filter(
            user=hr_user,
            start_time__lt=conflict_end_time,
            end_time__gt=scheduled_date,
            is_available=False
        ).exists()

        if hr_conflicts:
            raise ValidationError("HR is not available at the selected time")

        # Check candidate availability
        candidate_conflicts = AvailabilitySlot.objects.filter(
            user=candidate,
            start_time__lt=conflict_end_time,
            end_time__gt=scheduled_date,
            is_available=False
        ).exists()

        if candidate_conflicts:
            raise ValidationError("Candidate is not available at the selected time")

        # 3. Create interview
        with transaction.atomic():
            interview = Interview.objects.create(
                job=job,
                hr_user=hr_user,
                candidate=candidate,
                scheduled_date=scheduled_date,
                duration_minutes=duration_minutes,
                interview_type=interview_type,
                title=f"Interview for {job.title}",
                status='scheduled'
            )

            # Add categories
            interview.categories.set(categories)

            # Create notification for candidate
            Notification.objects.create(
                title="Interview Scheduled",
                message=f"You have been scheduled for an interview for {job.title} on {scheduled_date.strftime('%B %d, %Y at %I:%M %p')}",
                notification_type="info",
                category="interview",
                recipient_type="specific",
                recipient=candidate,
                data={
                    "interview_id": str(interview.id),
                    "job_title": job.title,
                    "scheduled_date": scheduled_date.isoformat(),
                    "interview_type": interview_type
                },
                action_url=f"/interviews/{interview.id}/"
            )

            # Create notification for HR
            Notification.objects.create(
                title="Interview Scheduled",
                message=f"You have scheduled an interview with {candidate.email} for {job.title}",
                notification_type="info",
                category="interview",
                recipient_type="specific",
                recipient=hr_user,
                data={
                    "interview_id": str(interview.id),
                    "candidate_name": f"{candidate.first_name} {candidate.last_name}",
                    "scheduled_date": scheduled_date.isoformat()
                }
            )

            logger.info(f"Interview scheduled: {interview.id}")
            return interview

    @staticmethod
    def add_questions_to_interview(interview, questions_data):
        from ..models import InterviewQuestionSet, InterviewQuestion

        if interview.status != 'draft':
            raise ValidationError("Can only add questions to interviews in draft status")

        with transaction.atomic():
            for idx, question_data in enumerate(questions_data):
                question_id = question_data.get('question_id')
                required = question_data.get('required', True)

                # Get question
                try:
                    question = InterviewQuestion.objects.get(id=question_id, is_active=True)
                except InterviewQuestion.DoesNotExist:
                    raise ValidationError(f"Question {question_id} not found or inactive")

                # Check if question already added
                if InterviewQuestionSet.objects.filter(interview=interview, question=question).exists():
                    continue

                # Add to interview
                InterviewQuestionSet.objects.create(
                    interview=interview,
                    question=question,
                    order=idx,
                    required=required
                )

            if interview.question_sets.count() > 0 and interview.status == 'draft':
                interview.status = 'scheduled'
                interview.save()

    @staticmethod
    def start_interview(interview):
        from ..models import CandidateAnswer

        if not interview.can_start():
            raise ValidationError("Interview cannot be started at this time")

        if interview.status != 'scheduled':
            raise ValidationError(f"Interview is {interview.status}, cannot start")

        interview.status = 'in_progress'
        interview.started_at = timezone.now()
        interview.save()

        # Create initial answers for all questions
        with transaction.atomic():
            for question_set in interview.question_sets.all():
                CandidateAnswer.objects.get_or_create(
                    question_set=question_set,
                    candidate=interview.candidate,
                    defaults={
                        'answer_text': '',
                        'is_submitted': False
                    }
                )

        return interview

    @staticmethod
    def submit_candidate_answer(answer_id, answer_data, candidate):
        from ..models import CandidateAnswer

        try:
            answer = CandidateAnswer.objects.select_related(
                'question_set__question',
                'question_set__interview'
            ).get(id=answer_id, candidate=candidate)
        except CandidateAnswer.DoesNotExist:
            raise ValidationError("Answer not found")

        interview = answer.question_set.interview

        if interview.status != 'in_progress':
            raise ValidationError("Interview is not in progress")

        question = answer.question_set.question
        if answer.time_taken_seconds > (question.time_limit_minutes * 60):
            raise ValidationError("Time limit exceeded")

        with transaction.atomic():
            if question.is_mcq():
                answer.selected_options = answer_data.get('selected_options', [])
            else:
                answer.answer_text = answer_data.get('answer_text', '')

            answer.code_snippet = answer_data.get('code_snippet', '')
            answer.file_upload = answer_data.get('file_upload')
            answer.is_submitted = True
            answer.submitted_at = timezone.now()
            answer.save()

            if question.is_mcq():
                answer.calculate_auto_score()

        return answer

    @staticmethod
    def auto_grade_interview(interview):
        from ..models import CandidateAnswer

        total_auto_score = 0
        total_possible_auto = 0

        for answer in CandidateAnswer.objects.filter(
            question_set__interview=interview,
            is_submitted=True
        ).select_related('question_set__question'):

            question = answer.question_set.question

            if question.is_mcq():
                score = answer.calculate_auto_score()
                total_auto_score += score
                total_possible_auto += question.points

        return {
            'auto_score': total_auto_score,
            'possible_auto_score': total_possible_auto,
            'auto_percentage': (total_auto_score / total_possible_auto * 100) if total_possible_auto > 0 else 0
        }

    @staticmethod
    def finalize_interview(interview, hr_user, feedback_data):
        from ..models import InterviewResult

        if interview.status != 'completed':
            raise ValidationError("Interview must be completed before finalizing")

        if hr_user != interview.hr_user:
            raise ValidationError("Only the scheduling HR can finalize results")

        with transaction.atomic():
            result, created = InterviewResult.objects.get_or_create(interview=interview)
            result.calculate_scores()

            result.overall_feedback = feedback_data.get('overall_feedback', '')
            result.recommendation = feedback_data.get('recommendation', '')
            result.hr_notes = feedback_data.get('hr_notes', '')
            result.is_finalized = True
            result.save()

            interview.completed_at = timezone.now()
            interview.save()

            Notification.objects.create(
                title="Interview Results Available",
                message=f"Your interview results for {interview.job.title} are now available",
                notification_type="info",
                category="interview",
                recipient_type="specific",
                recipient=interview.candidate,
                data={
                    "interview_id": str(interview.id),
                    "job_title": interview.job.title,
                    "percentage_score": result.percentage_score,
                    "recommendation": result.recommendation
                },
                action_url=f"/interviews/{interview.id}/result/"
            )

        return result


class PreparationService:
    """Service class for preparation recommendations"""

    @staticmethod
    def get_preparation_recommendations(user):
        from ..models import InterviewCategory, PreparationModule, UserPreparationProgress
        from cv_manager.models import ResumeAnalysis

        applied_jobs = user.applied_jobs.all() if hasattr(user, 'applied_jobs') else []

        if applied_jobs:
            applied_categories = set()

            for job in applied_jobs:
                categories = InterviewCategory.objects.filter(
                    name__in=job.tags if hasattr(job, 'tags') else []
                )
                applied_categories.update(categories)

            if not applied_categories:
                applied_categories = InterviewCategory.objects.filter(
                    name__in=['Technical', 'Programming', 'Problem Solving']
                )

        else:
            try:
                analysis = ResumeAnalysis.objects.filter(user=user).latest('analysis_timestamp')
                user_skills = analysis.career_insights.get('skills', [])[:10]
            except ResumeAnalysis.DoesNotExist:
                user_skills = []

            skill_keywords = {
                'technical': ['python', 'java', 'javascript', 'react', 'node', 'database', 'sql'],
                'behavioral': ['communication', 'teamwork', 'leadership', 'problem-solving'],
                'system_design': ['architecture', 'design', 'scalability', 'performance'],
                'coding': ['algorithms', 'data structures', 'leetcode', 'hackerrank'],
            }

            applied_categories = set()
            for skill in user_skills:
                skill_lower = skill.lower()
                for category_name, keywords in skill_keywords.items():
                    if any(keyword in skill_lower for keyword in keywords):
                        try:
                            category = InterviewCategory.objects.get(name__icontains=category_name)
                            applied_categories.add(category)
                        except InterviewCategory.DoesNotExist:
                            continue

            if not applied_categories:
                applied_categories = InterviewCategory.objects.filter(is_active=True)[:3]

        modules = PreparationModule.objects.filter(
            category__in=applied_categories,
            is_active=True
        ).order_by('difficulty', 'estimated_time_minutes')

        recommendations = []
        for module in modules:
            try:
                progress = UserPreparationProgress.objects.get(user=user, module=module)
                status = progress.status
                progress_pct = progress.progress_percentage
            except UserPreparationProgress.DoesNotExist:
                status = 'not_started'
                progress_pct = 0

            recommendations.append({
                'module_id': module.id,
                'title': module.title,
                'category': module.category.name,
                'content_type': module.content_type,
                'difficulty': module.difficulty,
                'estimated_time': module.estimated_time_minutes,
                'status': status,
                'progress': progress_pct,
                'recommendation_reason': f"Based on your {'applied positions' if applied_jobs else 'skills'}"
            })

        return {
            'user_has_applied_jobs': bool(applied_jobs),
            'applied_jobs_count': len(applied_jobs),
            'recommended_categories': [cat.name for cat in applied_categories],
            'total_modules': len(recommendations),
            'recommendations': recommendations
        }

    @staticmethod
    def track_preparation_progress(user, module_id, progress_percentage, status):
        from ..models import PreparationModule, UserPreparationProgress

        try:
            module = PreparationModule.objects.get(id=module_id, is_active=True)
        except PreparationModule.DoesNotExist:
            raise ValidationError("Preparation module not found")

        with transaction.atomic():
            progress, created = UserPreparationProgress.objects.update_or_create(
                user=user,
                module=module,
                defaults={
                    'status': status,
                    'progress_percentage': min(100, max(0, progress_percentage)),
                    'last_accessed': timezone.now()
                }
            )

            if progress_percentage >= 100 and status != 'completed':
                progress.status = 'completed'
                progress.completed_at = timezone.now()
                progress.save()

        return progress
