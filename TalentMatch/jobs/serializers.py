# jobs/serializers.py
from rest_framework import serializers
from .models import JobApplication, Job, JobRankingConfig

# 1️⃣ JobRankingConfigSerializer first
class JobRankingConfigSerializer(serializers.ModelSerializer):
    total_weight = serializers.SerializerMethodField()

    class Meta:
        model = JobRankingConfig
        fields = "__all__"
        read_only_fields = ["job"]
        
    def get_total_weight(self, obj):
        return (
            obj.cgpa_weight +
            obj.skills_weight +
            obj.experience_weight +
            obj.experience_weight +
            obj.project_weight +
            obj.llm_weight +
            obj.bert_weight +
            obj.custom_model_weight
        )


# 2️⃣ JobApplicationSerializer - UPDATED to include ALL fields
class JobApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    applicant_id = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "job_title",
            "applicant",
            "applicant_id",
            "applicant_name",
            "first_name",
            "last_name",
            "applicant_email",
            "resume",
            "resume_url",
            "applied_at",
            "rank_score",
            "groq_rank",
            "bert_similarity",
            "custom_model_score",
            "skills",
            "total_experience",
            "cgpa",
            "project_categories",
            # Add any other fields from your model
        ]
        read_only_fields = [
            "applied_at", "rank_score", "groq_rank", "bert_similarity",
            "custom_model_score", "skills", "total_experience", "cgpa",
            "project_categories"
        ]

    def get_applicant_name(self, obj):
        user = getattr(obj, "applicant", None)
        if user:
            full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            return full_name if full_name else getattr(user, "username", "Unknown User")
        return "N/A"

    def get_first_name(self, obj):
        user = getattr(obj, "applicant", None)
        return getattr(user, 'first_name', '') if user else ''

    def get_last_name(self, obj):
        user = getattr(obj, "applicant", None)
        return getattr(user, 'last_name', '') if user else ''

    def get_applicant_email(self, obj):
        return getattr(getattr(obj, "applicant", None), "email", "N/A")

    def get_applicant_id(self, obj):
        user = getattr(obj, "applicant", None)
        return getattr(user, 'id', None) if user else None

    def get_resume_url(self, obj):
        request = self.context.get("request")
        if obj.resume and hasattr(obj.resume, "url"):
            return request.build_absolute_uri(obj.resume.url) if request else obj.resume.url
        return None

    def get_job_title(self, obj):
        return obj.job.title if obj.job else "N/A"


# 3️⃣ JobSerializer last
class JobSerializer(serializers.ModelSerializer):
    applications = JobApplicationSerializer(many=True, read_only=True)
    applications_count = serializers.SerializerMethodField()
    ranking_config = JobRankingConfigSerializer(required=False)
    
    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "description",
            "requirements",
            "application_deadline",
            "location",
            "company_name",
            "created_by",
            "created_at",
            "updated_at",
            "ranking_config",
            "applications",
            "applications_count",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def get_applications_count(self, obj):
        return obj.applications.count()

    def create(self, validated_data):
        ranking_data = validated_data.pop("ranking_config", None)
        job = Job.objects.create(**validated_data)
        if ranking_data:
            JobRankingConfig.objects.create(job=job, **ranking_data)
        else:
            JobRankingConfig.objects.create(job=job)
        return job

    def update(self, instance, validated_data):
        ranking_data = validated_data.pop("ranking_config", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ranking_data:
            config = getattr(instance, "ranking_config", None)
            if config:
                for key, value in ranking_data.items():
                    setattr(config, key, value)
                config.save()
            else:
                JobRankingConfig.objects.create(job=instance, **ranking_data)
        return instance