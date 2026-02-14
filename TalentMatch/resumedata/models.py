# from django.db import models

# # Create your models here.
# class Resume(models.Model):
#     resume = models.FileField(upload_to="resume")
#     rank = models.IntegerField(default=0)
#     skills = models.JSONField(default=list)
#     total_experience = models.CharField(max_length=50, default="0")
#     project_category = models.JSONField(default=list)

# class JobDescription(models.Model):
#     job_title=models.CharField(max_length=100)
#     job_description = models.TextField()


#     def __str__(self):
#         return self.job_title

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
