# interviews/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from django.utils import timezone
from datetime import timedelta


class InterviewCategory(models.Model):
    """Categories for organizing interview questions (Technical, Behavioral, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # For UI
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='created_categories')

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Interview Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class QuestionType(models.Model):
    """Types of questions (MCQ, Descriptive, Coding, etc.)"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)  # MCQ, DESC, CODE, etc.
    requires_answer_key = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class InterviewQuestion(models.Model):
    """Base question model that can be used in interviews"""
    DIFFICULTY_LEVELS = (
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(InterviewCategory, on_delete=models.CASCADE, related_name='questions',null=True,blank=True)
    question_type = models.ForeignKey(QuestionType, on_delete=models.CASCADE)
    question_text = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, default='medium')
    points = models.PositiveIntegerField(default=10)
    time_limit_minutes = models.PositiveIntegerField(default=5)  # Time to answer
    
    # For MCQ questions
    options = models.JSONField(default=list, blank=True)  # ['GET', 'POST', 'DELETE', 'CONNECT']
    correct_option_indices = models.JSONField(default=list, blank=True)  # [0, 1] for correct options
    # For descriptive answers
    keywords = models.JSONField(default=list, blank=True)  # For descriptive questions
    auto_score_enabled = models.BooleanField(default=False)  # Whether to auto-score

    # HR-provided answer (only visible to HR)
    hr_answer = models.TextField(blank=True, help_text="Correct answer (visible only to HR)")
    hr_answer_notes = models.TextField(blank=True, help_text="Explanation/grading criteria")
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='created_questions')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'difficulty', 'created_at']
        indexes = [
            models.Index(fields=['category', 'difficulty']),
            models.Index(fields=['question_type', 'is_active']),
        ]
    
    def __str__(self):
        category = self.category.name if self.category else "Uncategorized"
        return f"{category}: {self.question_text[:50]}..."
    
    def is_mcq(self):
        return self.question_type.code == 'MCQ'
    
    def get_correct_options(self):
        """Returns list of correct option indices (for MCQ)"""
        if not self.is_mcq():
            return []
        
        print(f"\n=== DEBUG get_correct_options ===")
        print(f"Question ID: {self.id}")
        print(f"correct_option_indices: {self.correct_option_indices}")
        print(f"Options type: {type(self.options)}")
        
        # First priority: Use the correct_option_indices field
        if hasattr(self, 'correct_option_indices') and self.correct_option_indices is not None:
            print(f"Returning correct_option_indices: {self.correct_option_indices}")
            return self.correct_option_indices
        
        # Second priority: Check if options are dictionaries with is_correct flag
        print(f"Checking options structure...")
        correct_indices = []
        if self.options and isinstance(self.options, list):
            for i, option in enumerate(self.options):
                if isinstance(option, dict):
                    # Check if it's a dictionary with is_correct key
                    if option.get('is_correct', False):
                        correct_indices.append(i)
                        print(f"  Option {i} is correct (dictionary)")
                elif isinstance(option, str):
                    # String options - we can't determine correctness from string alone
                    print(f"  Option {i} is string: '{option}'")
                else:
                    print(f"  Option {i} has unknown type: {type(option)}")
        
        print(f"Correct indices found: {correct_indices}")
        return correct_indices

class Interview(models.Model):
    """Scheduled interview session"""
    INTERVIEW_TYPES = (
        ('written', 'Written Assessment'),
        ('live', 'Live Interview'),
        ('mixed', 'Mixed (Written + Live)'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)
    title = models.CharField(max_length=200, default='Untitled Interview')
    description = models.TextField(blank=True)
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Participants
    hr_user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='hr_interviews')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='candidate_interviews')
    
    # Categories for this interview (for preparation)
    categories = models.ManyToManyField(InterviewCategory, related_name='interviews', blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    meeting_link = models.URLField(blank=True, null=True)  # For live interviews
    instructions = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['hr_user', 'status']),
            models.Index(fields=['candidate', 'status']),
            models.Index(fields=['job', 'status']),
        ]
    
    def __str__(self):
        return {self.title}
    
    def is_past_due(self):
        return timezone.now() > self.scheduled_date
    
    def start_interview(self):
        """
        Start the interview and lock start time
        """
        if self.status != 'scheduled':
            return False

        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        return True


    def get_end_time(self):
        """
        Calculate interview end time
        """
        if not self.started_at:
            return None
        return self.started_at + timedelta(minutes=self.duration_minutes)


    def has_time_expired(self):
        """
        Check if interview duration is over
        """
        end_time = self.get_end_time()
        if not end_time:
            return False
        return timezone.now() >= end_time


    def end_interview(self):
        """
        End interview safely
        """
        if self.status != 'in_progress':
            return False

        self.status = 'completed'
        self.ended_at = timezone.now()
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'ended_at', 'completed_at'])
        return True

    
    def get_preparation_categories(self):
        """Get categories for candidate preparation"""
        return self.categories.all()

    def has_time_expired(self):
        if not self.started_at:
            return False
        end_time = self.started_at + timezone.timedelta(
            minutes=self.duration_minutes
        )
        return timezone.now() >= end_time

    def auto_end_and_submit(self):
        question_sets = InterviewQuestionSet.objects.filter(interview=self)

        for qs in question_sets:
            answer, _ = CandidateAnswer.objects.get_or_create(
                question_set=qs,
                candidate=self.candidate,
                defaults={'answer_text': '', 'auto_score': 0}
            )
            if not answer.is_submitted:
                answer.is_submitted = True
                answer.submitted_at = timezone.now()
                answer.save()

        self.end_interview()
    


from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class InterviewQuestionSet(models.Model):
    """A set of questions assigned to a specific interview"""
    interview = models.ForeignKey('Interview', on_delete=models.CASCADE, related_name='question_sets')
    question = models.ForeignKey('InterviewQuestion', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    expected_answer_text = models.TextField(blank=True, null=True)
    expected_keywords = models.JSONField(blank=True, null=True)  # ["django", "orm", "queryset"]
    auto_score_enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = ('interview', 'question')
        ordering = ['order']

    def __str__(self):
        return f"{self.interview.title} - {self.question.question_text[:30]}"
    
    def save(self, *args, **kwargs):
        # Auto-enable scoring for descriptive questions
        if not self.question.is_mcq():
            if (not self.auto_score_enabled or not self.expected_keywords) and self.question.keywords:
                self.expected_keywords = self.question.keywords
                self.auto_score_enabled = True

        super().save(*args, **kwargs)

class CandidateAnswer(models.Model):
    """Candidate's answer for a specific interview question"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_set = models.ForeignKey('InterviewQuestionSet', on_delete=models.CASCADE, related_name='answers')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    selected_options = models.JSONField(default=list, blank=True)  # For MCQs
    code_snippet = models.TextField(blank=True)
    file_upload = models.FileField(upload_to='candidate_answers/', null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    auto_score = models.FloatField(null=True, blank=True)
    hr_score = models.FloatField(null=True, blank=True)
    hr_feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='graded_answers'
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('question_set', 'candidate')

    def calculate_auto_score(self):
        """
        Calculate auto score for MCQ and descriptive questions.
        Returns float score or None if manual grading is required.
        """
        try:
            question_set = self.question_set
            question = question_set.question
            points = question.points or 0

            # If HR already graded, don't overwrite
            if self.hr_score is not None:
                return self.hr_score

            # ---------------------------
            # Descriptive Question
            # ---------------------------
            if not question.is_mcq():
                if question_set.auto_score_enabled and question_set.expected_keywords:
                    import re
                    # Normalize answer text (lowercase, remove punctuation)
                    answer_text = (self.answer_text or "").lower()
                    answer_text = re.sub(r'\W+', ' ', answer_text)

                    expected_keywords = question_set.expected_keywords or []
                    if expected_keywords:
                        matches = sum(
                            1 for kw in expected_keywords
                            if kw and kw.lower() in answer_text
                        )
                        total_keywords = len(expected_keywords)
                        if total_keywords > 0:
                            score = (matches / total_keywords) * points
                            return round(float(score), 2)
                # No keywords → manual grading required
                return None

            # ---------------------------
            # MCQ Question
            # ---------------------------
            correct_options = question.get_correct_options()
            selected_options = self.selected_options or []

            if not isinstance(selected_options, list):
                selected_options = [selected_options]

            # Convert to int for comparison
            try:
                selected_set = set(int(opt) for opt in selected_options if opt is not None)
                correct_set = set(int(opt) for opt in correct_options if opt is not None)
            except (ValueError, TypeError):
                return 0.0

            # Full points if exact match
            if selected_set == correct_set:
                return float(points)

            # Partial points for multi-select
            if correct_set:
                matched = len(selected_set & correct_set)
                total_correct = len(correct_set)
                if total_correct > 0:
                    score = (matched / total_correct) * points
                    return round(float(score), 2)

            # No match → zero points
            return 0.0

        except Exception as e:
            import traceback
            traceback.print_exc()
            return None



class PreparationModule(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(
        InterviewCategory,
        on_delete=models.CASCADE,
        related_name='preparation_modules'
    )
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    estimated_time_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class UserPreparationProgress(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    module = models.ForeignKey(
        PreparationModule,
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    progress_percentage = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'module')

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class AvailabilitySlot(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_available = models.BooleanField(default=True)

    def clean(self):
        # ✅ Ensure end time is after start time
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        return f"{self.user.email}: {self.start_time} → {self.end_time}"



class InterviewResult(models.Model):
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='results'
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interview_results'
    )

    total_score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)
    percentage = models.FloatField(default=0)

    category_breakdown = models.JSONField(default=dict, blank=True)
    performance_level = models.CharField(max_length=50, blank=True)

    finalized = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='finalized_results'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('interview', 'candidate')

    def __str__(self):
        return f"{self.candidate.email} - {self.interview.title}"



# ================= AI INTERVIEW PREPARATION =================

class AIPreparationSession(models.Model):
    """
    Stores AI-generated interview preparation content
    for a specific job seeker and job.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_preparation_sessions"
    )

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="ai_preparation_sessions"
    )

    # AI-generated interview preparation (questions + answers)
    generated_content = models.JSONField()

    # Track which AI model generated this
    model_used = models.CharField(
        max_length=100,
        default="llama-3.1-8b-instant"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "job")
        ordering = ["-created_at"]
        verbose_name = "AI Interview Preparation Session"
        verbose_name_plural = "AI Interview Preparation Sessions"

    def __str__(self):
        return f"{self.user.email} → {self.job.title}"


from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()


class InterviewPreparation(models.Model):
    """
    Stores main AI-generated interview preparation
    per job per jobseeker
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="interview_preparations"
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="interview_preparations"
    )

    preparation_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #twO NEW FIELDS
    last_more_generated_at = models.DateTimeField(null=True, blank=True)
    more_generate_count = models.IntegerField(default=0, null=False)

    class Meta:
        unique_together = ("user", "job")

    def __str__(self):
        return f"{self.user.email} - {self.job.title}"


class InterviewQuestionGeneration(models.Model):
    """
    Stores extra questions generated when user clicks
    'Generate More Questions'
    """
    preparation = models.ForeignKey(
        InterviewPreparation,
        on_delete=models.CASCADE,
        related_name="extra_generations"
    )

    prompt_used = models.TextField()
    generated_questions = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extra questions for {self.preparation.job.title}"


class InterviewChatSession(models.Model):
    """
    One chat session per job per user
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="interview_chat_sessions"
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="interview_chat_sessions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
   

    def __str__(self):
        return f"Chat: {self.user.email} - {self.job.title}"
class InterviewChatUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    date = models.DateField()

    tokens_used = models.IntegerField(default=0)
    messages_used = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user", "job", "date")


class InterviewChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    session = models.ForeignKey(
        InterviewChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} message"

from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()

class MockInterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mock_interviews")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="mock_interviews")
    interview_type = models.CharField(
        max_length=20,
        choices=[("technical", "Technical"), ("behavioral", "Behavioral"), ("mixed", "Mixed")],
        default="mixed"
    )

    difficulty = models.CharField(
        max_length=20,
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        default="medium"
    )
    total_questions = models.IntegerField(default=10)
    
    is_completed = models.BooleanField(default=False)
    
    questions = models.JSONField(default=list)  # store all generated questions
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MockInterviewSession(user={self.user}, job={self.job})"


class MockInterviewAnswer(models.Model):
    session = models.ForeignKey(
        MockInterviewSession,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question_index = models.PositiveIntegerField()
    question = models.JSONField()
    answer = models.TextField()
    feedback = models.TextField()
    score = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "question_index")