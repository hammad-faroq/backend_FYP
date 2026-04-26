from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings

# Resume model specifically for Template 1
class ResumeTemplate1(models.Model):
    full_name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    linkedin = models.URLField()
    github=models.URLField()
    profile = models.TextField()
    interests = models.TextField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(
        upload_to='template1/profile_images/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    

    class Meta:
        db_table = 'resume_template1'

    def __str__(self):
        return self.full_name


# Skills related to Template1 resumes
class SkillTemplate1(models.Model):
    resume = models.ForeignKey(ResumeTemplate1, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'skill_template1'

    def __str__(self):
        return self.name


# Education related to Template1 resumes
class EducationTemplate1(models.Model):
    resume = models.ForeignKey(ResumeTemplate1, on_delete=models.CASCADE, related_name='education')
    institution = models.CharField(max_length=100)
    level = models.CharField(max_length=100)
    detail = models.CharField(max_length=255)

    class Meta:
        db_table = 'education_template1'

    def __str__(self):
        return f"{self.institution} ({self.level})"



# ----------------------#
# ----Temaplate 2-------#
# ----------------------#


# Resume model specifically for Template 2
class ResumeTemplate2(models.Model):
    full_name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    linkedin = models.URLField(blank=True, null=True)
    github = models.URLField(blank=True, null=True)
    
    # summary = models.TextField()

    class Meta:
        db_table = 'resume_template2'

    def __str__(self):
        return self.full_name


class SummaryPointTemplate2(models.Model):
    resume = models.ForeignKey(
        ResumeTemplate2,
        on_delete=models.CASCADE,
        related_name='summary_points'
    )
    point = models.TextField()

    class Meta:
        db_table = 'summary_point_template2'

    def __str__(self):
        return f"Summary Point for {self.resume.name}"  # use 'name' not 'full_name' (if model has 'name')


# Teaching skills section
class TeachingSkillTemplate2(models.Model):
    resume = models.ForeignKey(ResumeTemplate2, on_delete=models.CASCADE, related_name='teaching_skills')
    description = models.TextField()

    class Meta:
        db_table = 'teaching_skill_template2'

    def __str__(self):
        return f"Teaching Skill for {self.resume.full_name}"


# Technical skills section
class TechnicalSkillTemplate2(models.Model):
    resume = models.ForeignKey(ResumeTemplate2, on_delete=models.CASCADE, related_name='technical_skills')
    category = models.CharField(max_length=1000)  # e.g., Internet, Databases, Languages & Tools
    details = models.TextField()

    class Meta:
        db_table = 'technical_skill_template2'

    def __str__(self):
        return f"{self.category} - {self.resume.full_name}"


# Education section
class EducationTemplate2(models.Model):
    resume = models.ForeignKey(ResumeTemplate2, on_delete=models.CASCADE, related_name='education')
    degree = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    years = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'education_template2'

    def __str__(self):
        return f"{self.degree} at {self.institution}"


# Trainings section
class TrainingTemplate2(models.Model):
    resume = models.ForeignKey(ResumeTemplate2, on_delete=models.CASCADE, related_name='trainings')
    title = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'training_template2'

    def __str__(self):
        return self.title


# Experience section
class ExperienceTemplate2(models.Model):
    resume = models.ForeignKey(ResumeTemplate2, on_delete=models.CASCADE, related_name='experience')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    duration = models.CharField(max_length=100)  # e.g., March 2021 - To Date
    responsibilities = models.TextField()

    class Meta:
        db_table = 'experience_template2'

    def __str__(self):
        return f"{self.job_title} at {self.company}"
    
#------------------------This is the Model for saving the meta data of the resume uplaoded through API-------------------#
# models.py

from django.db import models
from django.core.validators import FileExtensionValidator
import uuid
import os

def resume_upload_path(instance, filename):
    # Generate UUID for each file, keep the extension
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join("resumes/", new_filename)

class UploadedResume(models.Model):
    file = models.FileField(
        upload_to=resume_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "docx"])]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_name = models.CharField(max_length=255, blank=True, null=True)
    size = models.PositiveIntegerField(default=0)  # store file size in bytes

    def __str__(self):
        return self.original_name or f"Resume {self.id}"
    
#_______________________THis model gonna contain all the pares resume data and is a genereal model(like for any resume)______________________

from django.contrib.auth.models import User

class ParsedResume(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parsed_resume",null=True,blank=True)
    uploaded_resume = models.OneToOneField(
        "UploadedResume", on_delete=models.CASCADE, related_name="parsed"
    )
    raw_text = models.TextField(blank=True, null=True)
    raw_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        if self.user:
            display_name = getattr(self.user, "username", None) or getattr(self.user, "email", None) or f"User {self.user.id}"
            return f"{display_name}'s Resume"
        return "Unassigned Resume"




from django.db import models
from django.conf import settings

class JobMatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job_id = models.IntegerField()
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    score = models.FloatField()
    source = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.email}"

from django.db import models
from django.conf import settings

class CareerInsight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey("cv_manager.ParsedResume", on_delete=models.CASCADE)
    insight_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Career Insight for {self.user.email}"


class CertificationRecommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey("cv_manager.ParsedResume", on_delete=models.CASCADE)
    recommendations = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certifications for {self.user.email}"


class LearningPath(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey("cv_manager.ParsedResume", on_delete=models.CASCADE)
    target_role = models.CharField(max_length=255)
    path_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Learning Path for {self.user.email} - {self.target_role}"

# Add these models if they don't exist
class ResumeAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    parsed_resume = models.ForeignKey(ParsedResume, on_delete=models.CASCADE)
    career_insights = models.JSONField(default=dict)
    certifications = models.JSONField(default=list)
    learning_path = models.JSONField(default=dict)
    job_matches = models.JSONField(default=list)
    analysis_timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'resume_analysis'

    def __str__(self):
        return f"Analysis for {self.user.email}"