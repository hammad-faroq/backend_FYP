from django.conf import settings
from jobs.services.ranking import calculate_rank
from utils.ml_models import get_sentence_transformer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Job, JobApplication, JobRankingConfig
from .serializers import JobSerializer, JobApplicationSerializer
from resumedata.analyzer import EnhancedResumeAnalyzer
import os
from django.utils import timezone
import logging
from utils.qdrant_client import get_qdrant_client
logger = logging.getLogger(__name__)

# ✅ LAZY LOADING: Initialize as None, load on first use
_analyzer = None

def get_qdrant_client():
    """Lazy load Qdrant client - loads only when first needed"""
    return get_qdrant_client()

def get_sentence_model():
    """Lazy load SentenceTransformer model - loads only when first needed"""
    return get_sentence_transformer()

def get_analyzer():
    """Lazy load EnhancedResumeAnalyzer - loads only when first needed"""
    global _analyzer
    if _analyzer is None:
        _analyzer = EnhancedResumeAnalyzer()
        logger.info("✅ EnhancedResumeAnalyzer loaded")
    return _analyzer

COLLECTION_NAME = "JOBS"


# CREATE JOB (HR only)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_job(request):
    serializer = JobSerializer(data=request.data)
    if serializer.is_valid():
        job = serializer.save(created_by=request.user)
        print("JOB CREATED:", job.id, job.title, "by", request.user.email)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        print("CREATE JOB ERRORS:", serializer.errors)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# LIST JOBS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_jobs(request):
    user = request.user
    if user.role == 'hr':
        # HR sees all jobs they created (including past deadlines)
        jobs = Job.objects.filter(created_by=user)
    elif user.role == 'job_seeker':
        # Job seekers only see jobs with deadline in future or today
        today = timezone.now().date()
        
        # Option 1: Show jobs with deadline >= today (including today)
        jobs = Job.objects.filter(
            application_deadline__gte=today
        ).order_by('application_deadline')
    else:
        return Response({"error": "Invalid user role."}, status=status.HTTP_403_FORBIDDEN)

    serializer = JobSerializer(jobs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# GET JOB DETAIL
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_detail(request, job_id):
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.role == 'hr' and job.created_by != request.user:
        return Response({"error": "You are not allowed to view this job."},
                        status=status.HTTP_403_FORBIDDEN)

    serializer = JobSerializer(job)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_job(request, job_id):
    user = request.user

    if user.role != 'hr':
        return Response({"error": "Only HRs can update jobs."}, status=403)

    try:
        job = Job.objects.get(id=job_id, created_by=user)
    except Job.DoesNotExist:
        return Response({"error": "Job not found"}, status=404)

    serializer = JobSerializer(job, data=request.data, partial=True)

    if serializer.is_valid():
        job = serializer.save()
        return Response(serializer.data, status=200)

    return Response(serializer.errors, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_job(request, job_id):
    user = request.user

    if user.role != 'hr':
        return Response({"error": "Only HRs can delete jobs."}, status=403)

    try:
        job = Job.objects.get(id=job_id, created_by=user)
    except Job.DoesNotExist:
        return Response({"error": "Job not found"}, status=404)

    # 1. Delete from DB
    job.delete()

    return Response({"message": "Job deleted successfully."})


from jobs.services.hf_service import call_hf_model_with_retry
import threading

def _run_hf_analysis(application_id, resume_text, job_description):
    """Runs in background thread after application is saved."""
    from .models import JobApplication
    try:
        hf_result = call_hf_model_with_retry(
            resume_text=resume_text,
            job_description=job_description,
            max_retries=2,
            delay=3
        )
        gradio_analysis = hf_result.get("data", {})
        gradio_score = hf_result.get("score", 0)

        JobApplication.objects.filter(id=application_id).update(
            gradio_match_score=gradio_score,
            gradio_analysis=gradio_analysis
        )
        logger.info(f"HF analysis complete for application {application_id}: score={gradio_score}")
    except Exception as e:
        logger.error(f"Background HF analysis failed for application {application_id}: {e}")
        JobApplication.objects.filter(id=application_id).update(
            gradio_analysis={"error": str(e), "description": "Background analysis failed"}
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_to_job(request, job_id):
    user = request.user

    if user.role != 'job_seeker':
        return Response({"error": "Only job seekers can apply to jobs."}, status=status.HTTP_403_FORBIDDEN)

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    if job.application_deadline and job.application_deadline < timezone.now().date():
        return Response({
            "error": f"Application deadline has passed. The deadline was {job.application_deadline}."
        }, status=status.HTTP_400_BAD_REQUEST)

    resume_file = request.FILES.get('resume')
    if not resume_file:
        return Response({"error": "Resume file is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        resumes_dir = os.path.join(settings.MEDIA_ROOT, 'resumes')
        os.makedirs(resumes_dir, exist_ok=True)

        if JobApplication.objects.filter(job=job, applicant=user).exists():
            return Response(
                {"error": "You have already applied for this job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save application immediately (no HF call yet)
        application = JobApplication.objects.create(
            job=job,
            applicant=user,
            resume=resume_file,
            gradio_match_score=None,   # null = still processing
            gradio_analysis={}
        )

        resume_path = application.resume.path
        job_description = f"{job.title}\n{job.description}\n{job.requirements}"
        
        # ✅ USE LAZY-LOADED ANALYZER (only change - loads on first use)
        analyzer = get_analyzer()
        resume_text = analyzer.extract_text_from_resume(resume_path)

        # --- Sync: fast LLM/BERT/custom scoring ---
        llm_result = analyzer.analyze_resume_for_job(resume_text, job_description)

        groq_rank      = llm_result.get("groq_rank", 0)
        skills         = llm_result.get("skills", [])
        total_experience = llm_result.get("total_experience", "0")
        cgpa           = llm_result.get("CGPA", "N/A")
        project_categories = llm_result.get("project_category", [])
        custom_score   = llm_result.get("custom_model_score", 0)
        bert_similarity = llm_result.get("bert_similarity", 0)
        summary        = llm_result.get("summary", "")

        config, _ = JobRankingConfig.objects.get_or_create(job=job)
        # FIXED — only falls back if the value is actually None (not saved yet)
        weights = {
            "groq":   config.llm_weight if config.llm_weight is not None else 0.4,
            "bert":   config.bert_weight if config.bert_weight is not None else 0.3,
            "custom": config.custom_model_weight if config.custom_model_weight is not None else 0.3
        }

        rank_score = calculate_rank(
            groq_rank=groq_rank,
            bert_similarity=bert_similarity,
            custom_model_score=custom_score,
            weights=weights
        )

        application.groq_rank          = groq_rank
        application.bert_similarity    = bert_similarity
        application.custom_model_score = custom_score
        application.rank_score         = rank_score
        application.skills             = skills
        application.total_experience   = total_experience
        application.cgpa               = cgpa
        application.project_categories = project_categories
        application.save()

        # --- Async: fire-and-forget HF analysis ---
        thread = threading.Thread(
            target=_run_hf_analysis,
            args=(application.id, resume_text, job_description),
            daemon=True
        )
        thread.start()

        return Response({
            "message": "✅ Application submitted successfully. HuggingFace analysis is running in the background.",
            "job_title": job.title,
            "resume_url": application.resume.url if application.resume else None,
            "rank_score": rank_score,
            "groq_rank": groq_rank,
            "bert_similarity": bert_similarity,
            "custom_model_score": custom_score,
            "gradio_match_score": None,   # still processing
            "gradio_analysis": {},
            "skills": skills,
            "cgpa": cgpa,
            "total_experience": total_experience,
            "project_categories": project_categories,
            "summary": summary
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Failed to process application: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_applied_jobs(request):
    user = request.user
    applied_jobs = JobApplication.objects.filter(applicant=user).values_list("job_id", flat=True)

    return Response({
        "applied_jobs": list(applied_jobs)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_job_applications(request, job_id):
    user = request.user
    if user.role != 'hr':
        return Response({"error": "Only HRs can view applications."}, status=403)

    try:
        job = Job.objects.get(id=job_id, created_by=user)
    except Job.DoesNotExist:
        return Response({"error": "Job not found or not owned by you."}, status=404)

    # Get ALL applications without limiting
    applications = job.applications.all().order_by('-rank_score', '-applied_at')
    
    # Get the config for reference
    config = getattr(job, "ranking_config", None)
    shortlist_count = config.shortlist_count if config else 10

    # Use serializer with context for URLs
    serializer = JobApplicationSerializer(applications, many=True, context={'request': request})

    return Response({
        "job_title": job.title,
        "application_deadline": job.application_deadline,
        "ranking_config": {
            "shortlist_count": shortlist_count,
            "cgpa_weight": config.cgpa_weight if config else 0,
            "skills_weight": config.skills_weight if config else 0,
            "experience_weight": config.experience_weight if config else 0,
            "project_weight": config.project_weight if config else 0,
            "llm_weight": config.llm_weight if config else 0,
            "bert_weight": config.bert_weight if config else 0,
            "custom_model_weight": config.custom_model_weight if config else 0,
        } if config else None,
        "applications": serializer.data,
        "total_applications": applications.count(),
        "shortlist_count": shortlist_count
    }, status=200)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def resume_view(request):
    user = request.user

    # Only job seekers should manage resumes
    if user.role != "job_seeker":
        return Response({"error": "Only job seekers can manage resumes."}, status=403)

    # Path to their latest uploaded resume (if any)
    last_application = JobApplication.objects.filter(applicant=user).order_by("-applied_at").first()

    if request.method == "GET":
        if last_application and last_application.resume:
            return Response({"resume_url": last_application.resume.url})
        return Response({"message": "No resume found."}, status=404)

    elif request.method == "POST":
        resume_file = request.FILES.get("resume")
        if not resume_file:
            return Response({"error": "No file provided."}, status=400)

        # Delete old resume if exists
        if last_application and last_application.resume:
            if os.path.exists(last_application.resume.path):
                os.remove(last_application.resume.path)

        # Either update last one or create new "profile" application placeholder
        application = last_application or JobApplication.objects.create(job=None, applicant=user)
        application.resume = resume_file
        application.save()

        return Response({"resume_url": application.resume.url, "message": "Resume uploaded/updated successfully."})

    elif request.method == "DELETE":
        if not last_application or not last_application.resume:
            return Response({"error": "No resume to delete."}, status=404)

        if os.path.exists(last_application.resume.path):
            os.remove(last_application.resume.path)
        last_application.resume.delete(save=True)
        return Response({"status": "deleted", "message": "Resume deleted successfully."})


# ✅ GET all jobs the current user applied to
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_applied_jobs(request):
    user = request.user
    if user.role != 'job_seeker':
        return Response({"error": "Only job seekers can view applied jobs."}, status=403)

    applications = JobApplication.objects.filter(applicant=user).select_related('job')
    applied_jobs = [
    {
        "id": app.id,
        "applied_at": app.applied_at,
        
        "company_name": app.job.company_name,

        # 🔵 JOB DATA (THIS IS WHAT YOU NEED IN FRONTEND)
        "job": {
            "id": app.job.id,
            "title": app.job.title,
            "description": app.job.description,
            "requirements": app.job.requirements,
            "location": app.job.location,
            "application_deadline": app.job.application_deadline,
        },

        # 🟢 APPLICATION DATA
        "application": {
            "rank_score": app.rank_score,
            "groq_rank": app.groq_rank,
            "bert_similarity": app.bert_similarity,
            "skills": app.skills,
            "cgpa": app.cgpa,
            "experience": app.total_experience,
            "project_categories": app.project_categories,
        }
    }
    for app in applications.select_related('job')
    ]
    return Response(applied_jobs, status=200)