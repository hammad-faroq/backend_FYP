from django.db import models
from django.conf import settings
import datetime

class Job(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)
    requirements = models.TextField()
    application_deadline = models.DateField()
    company_name = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ------------------ JOB APPLICATION MODEL ------------------

class JobApplication(models.Model):
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications'  # So job.applications gives all resumes
    )
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/')
    applied_at = models.DateTimeField(auto_now_add=True)

    # 🆕 Add these fields:
    rank_score = models.FloatField(default=0.0)
    groq_rank = models.FloatField(default=0.0)                # LLM (Groq) score
    bert_similarity = models.FloatField(default=0.0) 
    skills = models.JSONField(default=list, blank=True)
    total_experience = models.CharField(max_length=100, blank=True)
    cgpa = models.CharField(max_length=10, blank=True, null=True)  # extracted from resume if found
    project_categories = models.JSONField(default=list, blank=True)
    # jobs/models.py
    custom_model_score = models.FloatField(default=0.0)
    gradio_match_score = models.FloatField(default=0, null=True, blank=True)
    gradio_analysis = models.JSONField(default=dict, null=True, blank=True)


    def __str__(self):
        return f"{self.applicant.email} applied for {self.job.title}"
    


# jobs/models.py

class JobRankingConfig(models.Model):
    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="ranking_config"
    )

    # Weights (0–100)
    cgpa_weight = models.PositiveIntegerField(default=0)
    skills_weight = models.PositiveIntegerField(default=0)
    experience_weight = models.PositiveIntegerField(default=0)
    project_weight = models.PositiveIntegerField(default=0)
    llm_weight = models.PositiveIntegerField(default=0)
    bert_weight = models.PositiveIntegerField(default=0)
    custom_model_weight = models.PositiveIntegerField(default=0)

    # How many CVs to shortlist
    shortlist_count = models.PositiveIntegerField(default=10)

    updated_at = models.DateTimeField(auto_now=True)

    def total_weight(self):
        return (
            self.cgpa_weight +
            self.skills_weight +
            self.experience_weight +
            self.project_weight +
            self.llm_weight +
            self.bert_weight +
            self.custom_model_weight
        )

    def __str__(self):
        return f"Ranking Config for {self.job.title}"
