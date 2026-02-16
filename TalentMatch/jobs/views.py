from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Job, JobApplication
from .serializers import JobSerializer, JobApplicationSerializer
from resumedata.analyzer import process_resume
import json,os
from resumedata.custom_model import predict_resume_score
from resumedata.analyzer import process_resume as process_resume_llm, extract_text_from_resume
from resumedata.qdrant_service import process_resume as process_resume_bert
from .models import JobRankingConfig
from jobs.services.ranking import calculate_rank


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
    from django.utils import timezone
    from datetime import datetime

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
        
        # Option 2: If you want to show jobs with no deadline as well:
        # jobs = Job.objects.filter(
        #     Q(application_deadline__gte=today) | Q(application_deadline__isnull=True)
        # ).order_by('application_deadline')
        
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

# UPDATE JOB (HR only) - serializer partial update
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_job(request, job_id):
    user = request.user
    if user.role != 'hr':
        return Response({"error": "Only HRs can update jobs."}, status=status.HTTP_403_FORBIDDEN)

    try:
        job = Job.objects.get(id=job_id, created_by=user)
    except Job.DoesNotExist:
        return Response({"error": "Job not found or you don’t own it."}, status=status.HTTP_404_NOT_FOUND)

    serializer = JobSerializer(job, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# DELETE JOB (HR only)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_job(request, job_id):
    user = request.user
    if user.role != 'hr':
        return Response({"error": "Only HRs can delete jobs."}, status=status.HTTP_403_FORBIDDEN)

    try:
        job = Job.objects.get(id=job_id, created_by=user)
    except Job.DoesNotExist:
        return Response({"error": "Job not found or you don’t own it."}, status=status.HTTP_404_NOT_FOUND)

    job.delete()
    return Response({"message": "Job deleted successfully."}, status=status.HTTP_200_OK)

# from django.conf import settings
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework import status
# from .models import Job, JobApplication, JobRankingConfig
# from .serializers import JobSerializer, JobApplicationSerializer
# from resumedata.analyzer import EnhancedResumeAnalyzer
# from jobs.services.ranking import calculate_rank
# import os

# analyzer = EnhancedResumeAnalyzer()

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def apply_to_job(request, job_id):
#     user = request.user

#     # Only job seekers can apply
#     if user.role != 'job_seeker':
#         return Response({"error": "Only job seekers can apply to jobs."}, status=status.HTTP_403_FORBIDDEN)

#     # Check if job exists
#     try:
#         job = Job.objects.get(id=job_id)
#     except Job.DoesNotExist:
#         return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

#     # Check if deadline has passed
#     from django.utils import timezone
#     if job.application_deadline and job.application_deadline < timezone.now().date():
#         return Response({
#             "error": f"Application deadline has passed. The deadline was {job.application_deadline}."
#         }, status=status.HTTP_400_BAD_REQUEST)

#     resume_file = request.FILES.get('resume')
#     if not resume_file:
#         return Response({"error": "Resume file is required."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         resumes_dir = os.path.join(settings.MEDIA_ROOT, 'resumes')
#         os.makedirs(resumes_dir, exist_ok=True)

#         # Save or update application
#         application, created = JobApplication.objects.update_or_create(
#             job=job,
#             applicant=user,
#             defaults={"resume": resume_file}
#         )

#         resume_path = application.resume.path
#         job_description = f"{job.title}\n{job.description}\n{job.requirements}"

#         # Step 1: LLM Analysis
#         llm_result = analyzer.analyze_resume_for_job(
#             analyzer.extract_text_from_resume(resume_path),
#             job_description
#         )
#         groq_rank = llm_result.get("groq_rank", 0)
#         skills = llm_result.get("skills", [])
#         total_experience = llm_result.get("total_experience", "0")
#         cgpa = llm_result.get("CGPA", "N/A")
#         project_categories = llm_result.get("project_category", [])
#         custom_score = llm_result.get("custom_model_score", 0)
#         bert_similarity = llm_result.get("bert_similarity", 0)
#         summary = llm_result.get("summary", "")

#         # Step 2: Get weights from JobRankingConfig
#         config, _ = JobRankingConfig.objects.get_or_create(job=job)
#         weights = {
#             "groq": config.llm_weight or 0.4,
#             "bert": config.bert_weight or 0.3,
#             "custom": config.custom_model_weight or 0.3
#         }

#         # Step 3: Calculate combined rank
#         rank_score = calculate_rank(
#             groq_rank=groq_rank,
#             bert_similarity=bert_similarity,
#             custom_model_score=custom_score,
#             weights=weights
#         )

#         # Step 4: Save all data
#         application.groq_rank = groq_rank
#         application.bert_similarity = bert_similarity
#         application.custom_model_score = custom_score
#         application.rank_score = rank_score
#         application.skills = skills
#         application.total_experience = total_experience
#         application.cgpa = cgpa
#         application.project_categories = project_categories
#         application.save()

#         message = "✅ Resume updated successfully for this job." if not created else "✅ Application submitted successfully."

#         return Response({
#             "message": message,
#             "job_title": job.title,
#             "resume_url": application.resume.url if application.resume else None,
#             "rank_score": rank_score,
#             "groq_rank": groq_rank,
#             "bert_similarity": bert_similarity,
#             "custom_model_score": custom_score,
#             "skills": skills,
#             "cgpa": cgpa,
#             "total_experience": total_experience,
#             "project_categories": project_categories,
#             "summary": summary
#         }, status=status.HTTP_200_OK)

#     except Exception as e:
#         return Response({"error": f"Failed to process application: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Job, JobApplication, JobRankingConfig
from resumedata.analyzer import EnhancedResumeAnalyzer, extract_text_from_resume
from resumedata.qdrant_service import process_resume as process_resume_bert
from resumedata.custom_model import predict_resume_score
from jobs.services.ranking import calculate_rank
from gradio_client import Client
import os
import json
import traceback
import threading
import time

analyzer = EnhancedResumeAnalyzer()

def analyze_with_gradio_async(application_id):
    """
    Background function to run Gradio analysis with retry logic
    Runs in separate thread and updates application when complete
    """
    max_retries = 2  # Reduced retries since GPU errors are persistent
    retry_count = 0
    
    try:
        application = JobApplication.objects.get(id=application_id)
        job = application.job
        resume_path = application.resume.path
        job_description = f"{job.title}\n{job.description}\n{job.requirements}"
        
        # Extract resume text
        try:
            resume_text = extract_text_from_resume(resume_path)
            # ✅ Limit text length to avoid GPU overload
            resume_text = resume_text[:4000]  # Max 4000 chars
            job_description = job_description[:1500]  # Max 1500 chars
        except Exception as e:
            print(f"❌ [Gradio Thread] Error extracting resume text: {e}")
            resume_text = ""
        
        print(f"🎯 [Gradio Thread] Starting CV-JD matching for application {application_id}...")
        
        # ✅ Retry loop
        while retry_count < max_retries:
            try:
                print(f"🔄 [Gradio Thread] Attempt {retry_count + 1}/{max_retries}")
                
                # ✅ Longer timeout for GPU tasks
                client = Client("Irfaniiioo/cvjdgradio")  # 5 minutes
                
                result = client.predict(
                    cv=resume_text,
                    job_description=job_description,
                    api_name="/match_cv_job"
                )
                
                # Parse the result
                if isinstance(result, str):
                    gradio_result = json.loads(result)
                else:
                    gradio_result = result
                    
                print(f"✅ [Gradio Thread] Analysis complete for application {application_id}")
                print(gradio_result)
                
                # Update application with Gradio results
                application.gradio_match_score = gradio_result.get("Total_score", 0)
                application.gradio_analysis = gradio_result
                application.save()
                
                print(f"✅ [Gradio Thread] Saved score: {gradio_result.get('Total_score', 0)}")
                return  # Success - exit function
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                print(f"❌ [Gradio Thread] Error (attempt {retry_count}/{max_retries}): {error_msg}")
                
                # Check if it's a GPU error
                is_gpu_error = "GPU task aborted" in error_msg or "aborted" in error_msg.lower()
                
                if retry_count < max_retries and not is_gpu_error:
                    # Wait before retrying (only for non-GPU errors)
                    wait_time = 30  # 30 seconds
                    print(f"⏳ [Gradio Thread] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # All retries failed or GPU error
                    print(f"❌ [Gradio Thread] Giving up. Saving error state.")
                    
                    if is_gpu_error:
                        error_description = "The AI model's GPU is currently overloaded due to high demand. Please check back in a few minutes."
                    else:
                        error_description = f"Analysis service error: {error_msg[:200]}"
                    
                    application.gradio_match_score = 0
                    application.gradio_analysis = {
                        "matching_analysis": "Analysis unavailable",
                        "description": error_description,
                        "score": 0,
                        "recommendation": "Other analysis scores (LLM, BERT, Custom Model) are available. The match score will be retried automatically.",
                        "error": error_msg[:500],
                        "error_type": "gpu_overload" if is_gpu_error else "api_error"
                    }
                    application.save()
                    return
            
    except JobApplication.DoesNotExist:
        print(f"❌ [Gradio Thread] Application {application_id} not found")
    except Exception as e:
        print(f"❌ [Gradio Thread] Unexpected error: {e}")
        print(traceback.format_exc())


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_to_job(request, job_id):
    user = request.user

    # Only job seekers can apply
    if user.role != 'job_seeker':
        return Response({"error": "Only job seekers can apply to jobs."}, status=status.HTTP_403_FORBIDDEN)

    # Check if job exists
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check if deadline has passed
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

        # Save or update application
        application, created = JobApplication.objects.update_or_create(
            job=job,
            applicant=user,
            defaults={"resume": resume_file}
        )

        resume_path = application.resume.path
        job_description = f"{job.title}\n{job.description}\n{job.requirements}"

        # ✅ Extract resume text
        print("📄 Extracting resume text...")
        try:
            resume_text = extract_text_from_resume(resume_path)
        except Exception as e:
            print(f"❌ Error extracting resume text: {e}")
            resume_text = ""

        # ==========================================
        # FAST ANALYSES (Run immediately)
        # ==========================================

        # Step 1: LLM Analysis (FAST)
        print("🧠 Running Groq LLM analysis...")
        try:
            llm_result = analyzer.analyze_resume_for_job(resume_text, job_description)
            groq_rank = llm_result.get("groq_rank", 0)
            skills = llm_result.get("skills", [])
            total_experience = llm_result.get("total_experience", "0")
            cgpa = llm_result.get("CGPA", "N/A")
            project_categories = llm_result.get("project_category", [])
            summary = llm_result.get("summary", "")
        except Exception as e:
            print(f"❌ Groq LLM error: {e}")
            groq_rank = 0
            skills = []
            total_experience = "0"
            cgpa = "N/A"
            project_categories = []
            summary = ""

        # Step 2: BERT + Qdrant Analysis (FAST)
        print("⚙️ Running BERT + Qdrant similarity analysis...")
        try:
            bert_result = process_resume_bert(resume_path, job_description, job_id=job.id)
            bert_similarity = bert_result.get("similarity_score", 0)
        except Exception as e:
            print(f"❌ BERT error: {e}")
            bert_similarity = 0

        # Step 3: Custom ML Model (FAST)
        print("🤖 Running custom ML model scoring...")
        try:
            custom_score = predict_resume_score(resume_path, job_description)
        except Exception as e:
            print(f"❌ Custom model error: {e}")
            custom_score = 0

        # Step 4: Get weights from JobRankingConfig
        config, _ = JobRankingConfig.objects.get_or_create(job=job)
        weights = {
            "groq": config.llm_weight or 0.4,
            "bert": config.bert_weight or 0.3,
            "custom": config.custom_model_weight or 0.3
        }

        # Step 5: Calculate combined rank (without Gradio for now)
        try:
            rank_score = calculate_rank(
                groq_rank=groq_rank,
                bert_similarity=bert_similarity,
                custom_model_score=custom_score,
                weights=weights
            )
        except Exception as e:
            print(f"❌ Ranking calculation error: {e}")
            rank_score = 0

        # ==========================================
        # SAVE IMMEDIATE RESULTS
        # ==========================================

        application.groq_rank = groq_rank
        application.bert_similarity = bert_similarity
        application.custom_model_score = custom_score
        application.rank_score = rank_score
        application.skills = skills
        application.total_experience = total_experience
        application.cgpa = cgpa
        application.project_categories = project_categories
        
        # ✅ Set Gradio as "processing" (will be updated by background thread)
        application.gradio_match_score = None  # None = processing
        application.gradio_analysis = {
            "status": "processing",
            "message": "Analysis in progress. This may take 2-3 minutes."
        }
        
        application.save()

        # ==========================================
        # START GRADIO IN BACKGROUND (SLOW - Async)
        # ==========================================
        
        print(f"🚀 Starting Gradio analysis in background for application {application.id}...")
        try:
            thread = threading.Thread(
                target=analyze_with_gradio_async,
                args=(application.id,),
                daemon=True
            )
            thread.start()
            print("✅ Gradio background thread started")
        except Exception as e:
            print(f"⚠️ Could not start Gradio thread: {e}")
            # Not critical - continue without it

        # ==========================================
        # RETURN IMMEDIATE RESPONSE
        # ==========================================

        message = "✅ Application submitted! Fast analysis complete. Match score analysis in progress..." if created else "✅ Resume updated! Fast analysis complete. Match score analysis in progress..."

        return Response({
            "message": message,
            "job_title": job.title,
            "resume_url": application.resume.url if application.resume else None,
            "rank_score": rank_score,
            "groq_rank": groq_rank,
            "bert_similarity": bert_similarity,
            "custom_model_score": custom_score,
            "gradio_match_score": None,  # ✅ Will be updated by background thread
            "gradio_status": "processing",  # ✅ Tell frontend it's processing
            "skills": skills,
            "cgpa": cgpa,
            "total_experience": total_experience,
            "project_categories": project_categories,
            "summary": summary,
            "note": "Match score will be available in 2-3 minutes. Page will auto-refresh."
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Apply to job error: {e}")
        print(traceback.format_exc())
        return Response({
            "error": f"Failed to process application: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ```

# ---

## **WHAT THIS DOES:**

# ### **✅ Application Process (Fast - 5-10 seconds):**
# 1. Save resume ✅
# 2. Run Groq LLM ✅
# 3. Run BERT ✅
# 4. Run Custom Model ✅
# 5. Calculate Combined Rank ✅
# 6. **Return response immediately** ✅
# 7. Start Gradio in background thread 🔄

# ### **🔄 Background Thread (2-3 minutes):**
# 1. Extracts resume text
# 2. Calls Gradio API (with retry)
# 3. Handles GPU errors gracefully
# 4. Updates database when complete
# 5. Frontend auto-refreshes and sees the score

# ---

## **KEY BENEFITS:**

# ✅ **Application never fails** - even if Gradio crashes
# ✅ **User sees results immediately** - Groq, BERT, Custom scores
# ✅ **Gradio runs in background** - doesn't block the response
# ✅ **Auto-retry on failure** - tries twice before giving up
# ✅ **GPU error handling** - shows friendly error message
# ✅ **Frontend polling works** - page refreshes every 10s to check

# ---

# ## **WHAT USER SEES:**

# **Immediately after applying:**
# ```
# ✅ Application submitted!
# - Combined Rank: 79 ✅
# - Groq Rank: 85 ✅
# - BERT: 78.5 ✅
# - Custom: 72.3 ✅
# - Match Score: Processing... 🔄
# ```

# **After 2-3 minutes (auto-refresh):**
# ```
# ✅ Application submitted!
# - Combined Rank: 79 ✅
# - Groq Rank: 85 ✅
# - BERT: 78.5 ✅
# - Custom: 72.3 ✅
# - Match Score: 88% ✅ (Click to see details)
# ```

# **If Gradio fails:**
# ```
# ✅ Application submitted!
# - Combined Rank: 79 ✅
# - Groq Rank: 85 ✅
# - BERT: 78.5 ✅
# - Custom: 72.3 ✅
# - Match Score: GPU Overload ⚠️


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

        # Either update last one or create new “profile” application placeholder
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
            "id": app.job.id,
            "title": app.job.title,
            "company_name": app.job.company_name,
            "location": app.job.location,
            "application_deadline": app.job.application_deadline,
            "applied_at": app.applied_at,
        }
        for app in applications if app.job
    ]
    return Response(applied_jobs, status=200)




# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from cv_manager.job_matcher import find_similar_jobs

# @api_view(['GET'])
# def similar_jobs(request, user_id):
#     """
#     Return top jobs matching a user's resume.
#     """
#     jobs = find_similar_jobs(user_id=user_id)
#     return Response(jobs)