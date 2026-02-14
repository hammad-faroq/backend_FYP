from django.contrib import admin
from .models import (
    ResumeTemplate1, SkillTemplate1, EducationTemplate1,
    ResumeTemplate2, SummaryPointTemplate2, TeachingSkillTemplate2,
    TechnicalSkillTemplate2, EducationTemplate2, TrainingTemplate2,
    ExperienceTemplate2
)

# ======================
# Template 1 Admin Setup
# ======================

class SkillTemplate1Inline(admin.TabularInline):
    model = SkillTemplate1
    extra = 1
    classes = ['collapse']

class EducationTemplate1Inline(admin.TabularInline):
    model = EducationTemplate1
    extra = 1
    classes = ['collapse']

@admin.register(ResumeTemplate1)
class ResumeTemplate1Admin(admin.ModelAdmin):
    inlines = [SkillTemplate1Inline, EducationTemplate1Inline]
    list_display = ['full_name', 'profession', 'email', 'phone']
    search_fields = ['full_name', 'profession', 'email', 'phone']
    list_filter = ['profession']
    fieldsets = [
        ('Personal Information', {
            'fields': [
                'full_name', 'profession', 'email', 'phone',
                'linkedin', 'github', 'profile_image'
            ]
        }),
        ('Profile & Interests', {
            'fields': ['profile', 'interests', 'additional_info'],
            'classes': ['collapse']
        }),
    ]

# ======================
# Template 2 Admin Setup
# ======================

class SummaryPointTemplate2Inline(admin.TabularInline):
    model = SummaryPointTemplate2
    extra = 1
    classes = ['collapse']

class TeachingSkillTemplate2Inline(admin.TabularInline):
    model = TeachingSkillTemplate2
    extra = 1
    classes = ['collapse']

class TechnicalSkillTemplate2Inline(admin.TabularInline):
    model = TechnicalSkillTemplate2
    extra = 1
    classes = ['collapse']

class EducationTemplate2Inline(admin.TabularInline):
    model = EducationTemplate2
    extra = 1
    classes = ['collapse']

class TrainingTemplate2Inline(admin.TabularInline):
    model = TrainingTemplate2
    extra = 1
    classes = ['collapse']

class ExperienceTemplate2Inline(admin.TabularInline):
    model = ExperienceTemplate2
    extra = 1
    classes = ['collapse']

@admin.register(ResumeTemplate2)
class ResumeTemplate2Admin(admin.ModelAdmin):
    inlines = [
        SummaryPointTemplate2Inline,
        TeachingSkillTemplate2Inline,
        TechnicalSkillTemplate2Inline,
        EducationTemplate2Inline,
        TrainingTemplate2Inline,
        ExperienceTemplate2Inline
    ]
    list_display = ['full_name', 'email', 'phone', 'linkedin']
    search_fields = ['full_name', 'email', 'phone', 'linkedin', 'github']
    list_filter = ['created_at'] if hasattr(ResumeTemplate2, 'created_at') else []
    fieldsets = [
        ('Contact Information', {
            'fields': [
                'full_name', 'address', 'phone', 'email',
                'linkedin', 'github'
            ]
        }),
    ]

# Register individual models that might need standalone admin access
@admin.register(SkillTemplate1)
class SkillTemplate1Admin(admin.ModelAdmin):
    list_display = ['name', 'resume']
    list_filter = ['resume']
    search_fields = ['name', 'resume__full_name']

@admin.register(EducationTemplate1)
class EducationTemplate1Admin(admin.ModelAdmin):
    list_display = ['institution', 'level', 'resume']
    list_filter = ['level', 'resume']
    search_fields = ['institution', 'level', 'resume__full_name']

# Register Template 2 related models if needed
@admin.register(SummaryPointTemplate2)
class SummaryPointTemplate2Admin(admin.ModelAdmin):
    list_display = ['point', 'resume']
    list_filter = ['resume']
    search_fields = ['point', 'resume__full_name']

@admin.register(TeachingSkillTemplate2)
class TeachingSkillTemplate2Admin(admin.ModelAdmin):
    list_display = ['description', 'resume']
    list_filter = ['resume']
    search_fields = ['description', 'resume__full_name']

@admin.register(TechnicalSkillTemplate2)
class TechnicalSkillTemplate2Admin(admin.ModelAdmin):
    list_display = ['category', 'resume']
    list_filter = ['category', 'resume']
    search_fields = ['category', 'details', 'resume__full_name']

@admin.register(EducationTemplate2)
class EducationTemplate2Admin(admin.ModelAdmin):
    list_display = ['degree', 'institution', 'resume']
    list_filter = ['institution', 'resume']
    search_fields = ['degree', 'institution', 'resume__full_name']

@admin.register(TrainingTemplate2)
class TrainingTemplate2Admin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'resume']
    list_filter = ['provider', 'resume']
    search_fields = ['title', 'provider', 'resume__full_name']

@admin.register(ExperienceTemplate2)
class ExperienceTemplate2Admin(admin.ModelAdmin):
    list_display = ['job_title', 'company', 'resume']
    list_filter = ['company', 'resume']
    search_fields = ['job_title', 'company', 'resume__full_name']