
# resumedata/models.py
from django.db import models
from jobs.models import JobApplication

class ResumeData(models.Model):
    job_application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='resume_data'
    )
    extracted_text = models.TextField(blank=True, null=True)
    analyzed_skills = models.JSONField(default=list, blank=True)
    experience_years = models.FloatField(default=0.0)
    education = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"ResumeData for {self.job_application.applicant.email}"
