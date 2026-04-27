# In cv_manager/views.py
from django.utils import timezone
import logging
import mimetypes
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string, get_template
from django.urls import reverse
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from cv_manager.services.parser import parse_uploaded_resume 
from weasyprint import HTML, CSS
from .forms import ResumeTemplate1Form, ResumeTemplate2Form
from .models import (
    UploadedResume, ParsedResume,
    ResumeTemplate1, SkillTemplate1, EducationTemplate1,
    ResumeTemplate2, TeachingSkillTemplate2, TechnicalSkillTemplate2,
    EducationTemplate2, TrainingTemplate2, ExperienceTemplate2, SummaryPointTemplate2
)
from .serializers import UploadedResumeSerializer
from rest_framework.settings import api_settings
# Patch DRF APIView to use default settings
APIView.settings = api_settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from cv_manager.models import (
    UploadedResume,
    ParsedResume,
    CareerInsight,
    CertificationRecommendation,
    LearningPath,
)
from resumedata.analyzer import EnhancedResumeAnalyzer
from cv_manager.models import ResumeAnalysis
logger = logging.getLogger(__name__)
from django.core.mail import send_mail
from django.conf import settings

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
]
from django.core.mail import send_mail
from django.template.loader import render_to_string
from cv_manager.services.parser import parse_uploaded_resume
from cv_manager.job_matcher import find_similar_jobs
from django.http import JsonResponse

# ======================================================================
# Resume Template Selection + Input
# ======================================================================

def select_template(request):
    return render(request, 'template_select.html')


def resume_input(request):
    selected_template = request.GET.get('template', 'template1')

    if selected_template == 'template1':
        if request.method == 'POST':
            form = ResumeTemplate1Form(request.POST, request.FILES)
            if form.is_valid():
                resume = form.save()

                # Save skills
                skills = request.POST.getlist('skills')
                for skill in skills:
                    if skill.strip():
                        SkillTemplate1.objects.create(resume=resume, name=skill.strip())

                # Save education
                institutions = request.POST.getlist('edu_institution')
                levels = request.POST.getlist('edu_level')
                details = request.POST.getlist('edu_detail')
                for inst, lvl, det in zip(institutions, levels, details):
                    if inst.strip() and lvl.strip() and det.strip():
                        EducationTemplate1.objects.create(
                            resume=resume,
                            institution=inst.strip(),
                            level=lvl.strip(),
                            detail=det.strip()
                        )

                return redirect('resume_output', template='template1', resume_id=resume.id)
        else:
            form = ResumeTemplate1Form()

        return render(request, 'template1/resume_input.html', {
            'form': form, 'selected_template': selected_template
        })

    elif selected_template == 'template2':
        if request.method == 'POST':
            form = ResumeTemplate2Form(request.POST)
            if form.is_valid():
                resume = form.save()

                # Save summary points
                summary_points = request.POST.getlist('summary_points')
                for point in summary_points:
                    if point.strip():
                        SummaryPointTemplate2.objects.create(resume=resume, point=point.strip())

                # Save teaching skills
                teaching_skills = request.POST.getlist('teaching_skills')
                for ts in teaching_skills:
                    if ts.strip():
                        TeachingSkillTemplate2.objects.create(resume=resume, description=ts.strip())

                # Save technical skills
                categories = request.POST.getlist('tech_category')
                details = request.POST.getlist('tech_details')
                for cat, det in zip(categories, details):
                    if cat.strip() and det.strip():
                        TechnicalSkillTemplate2.objects.create(
                            resume=resume,
                            category=cat.strip(),
                            details=det.strip()
                        )

                # Save education
                degrees = request.POST.getlist('edu_degree')
                institutions = request.POST.getlist('edu_institution')
                years = request.POST.getlist('edu_years')
                for deg, inst, yr in zip(degrees, institutions, years):
                    if deg.strip() and inst.strip():
                        EducationTemplate2.objects.create(
                            resume=resume,
                            degree=deg.strip(),
                            institution=inst.strip(),
                            years=yr.strip()
                        )

                # Save trainings
                titles = request.POST.getlist('training_title')
                providers = request.POST.getlist('training_provider')
                for title, prov in zip(titles, providers):
                    if title.strip():
                        TrainingTemplate2.objects.create(
                            resume=resume,
                            title=title.strip(),
                            provider=prov.strip()
                        )

                # Save experiences
                jobs = request.POST.getlist('exp_job')
                companies = request.POST.getlist('exp_company')
                durations = request.POST.getlist('exp_duration')
                responsibilities = request.POST.getlist('exp_resp')
                for job, comp, dur, resp in zip(jobs, companies, durations, responsibilities):
                    if job.strip() and comp.strip():
                        ExperienceTemplate2.objects.create(
                            resume=resume,
                            job_title=job.strip(),
                            company=comp.strip(),
                            duration=dur.strip(),
                            responsibilities=resp.strip()
                        )

                return redirect(reverse('resume_output', kwargs={
                    'template': 'template2', 'resume_id': resume.id
                }))
        else:
            form = ResumeTemplate2Form()

        return render(request, 'template2/resume_input2.html', {
            'form': form, 'selected_template': selected_template
        })


# ======================================================================
# Resume Output + Download + PDF
# ======================================================================

def resume_output(request, template, resume_id):
    if template == "template1":
        resume = get_object_or_404(ResumeTemplate1, id=resume_id)
        return render(request, 'template1/index.html', {'cv': resume})
    elif template == "template2":
        resume = get_object_or_404(ResumeTemplate2, id=resume_id)
        return render(request, 'template2/index.html', {'cv': resume})


def download_resume(request, resume_id):
    resume = get_object_or_404(ResumeTemplate1, id=resume_id)
    html_content = render_to_string('template1/index.html', {'cv': resume})
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="{resume.full_name}_resume.html"'
    return response


def download_resume2(request, resume_id):
    resume = get_object_or_404(ResumeTemplate2, id=resume_id)
    html_content = render_to_string('template2/index.html', {'cv': resume})
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="{resume.full_name}_resume.html"'
    return response


def resume_pdf1(request, pk):
    resume = ResumeTemplate1.objects.get(pk=pk)
    template_path = 'template1/index.html'
    context = {'cv': resume, 'for_pdf': True, 'BASE_DIR': settings.BASE_DIR}

    html_template = get_template(template_path)
    html_string = html_template.render(context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())

    css_path = finders.find('css/style.css')
    if css_path:
        pdf_file = html.write_pdf(stylesheets=[CSS(filename=css_path)])
    else:
        pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{resume.full_name}_resume.pdf"'
    return response


def resume_pdf2(request, pk):
    resume = get_object_or_404(ResumeTemplate2, pk=pk)
    template_path = 'template2/index.html'
    context = {'cv': resume, 'for_pdf': True, 'BASE_DIR': settings.BASE_DIR}

    html_template = get_template(template_path)
    html_string = html_template.render(context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{resume.full_name}_resume.pdf"'
    return response


# ======================================================================
# cv_manager/views.py - Robust Resume Upload & Analysis
# ======================================================================
# ======================================================================
# Resume Upload & Analysis API
# ====================================================================



class ResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        uploaded_file = request.FILES.get("file")
        job_description = request.data.get("job_description", "")

        # ----------------------- File Validation -----------------------
        if not uploaded_file:
            return Response({"success": False, "message": "No file uploaded."}, status=400)

        if uploaded_file.size > 5 * 1024 * 1024:
            return Response({"success": False, "message": "File size exceeds 5MB limit."}, status=400)

        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if mime_type not in ALLOWED_MIME_TYPES:
            return Response({"success": False, "message": "Unsupported file type."}, status=400)

        try:
            # ------------------- STEP 1 — Delete old resume -------------------
            old_parsed = ParsedResume.objects.filter(user=user).first()
            if old_parsed:
                ResumeAnalysis.objects.filter(parsed_resume=old_parsed).delete()
                CareerInsight.objects.filter(resume=old_parsed).delete()
                CertificationRecommendation.objects.filter(resume=old_parsed).delete()
                LearningPath.objects.filter(resume=old_parsed).delete()

                if old_parsed.uploaded_resume and old_parsed.uploaded_resume.file:
                    old_parsed.uploaded_resume.file.delete(save=False)
                old_parsed.uploaded_resume.delete()
                old_parsed.delete()

            # ------------------- STEP 2 — Save new uploaded resume -------------------
            serializer = UploadedResumeSerializer(data={"file": uploaded_file})
            serializer.is_valid(raise_exception=True)
            uploaded_resume = serializer.save(
                original_name=uploaded_file.name,
                size=uploaded_file.size
            )

            # ------------------- STEP 3 — Parse resume -------------------
            parser_result = parse_uploaded_resume(uploaded_resume.id, user=user)#1st time parsing
            resume_text = parser_result.get("raw_text", "")#get this text
            # print(resume_text)
            if not parser_result.get("success", False):
                return Response({"success": False, "message": parser_result.get("error")}, status=500)

            # ------------------- STEP 4 — Extract text + analyze -------------------
            analyzer = EnhancedResumeAnalyzer()
            # resume_text = analyzer.extract_text_from_resume(uploaded_resume.file.path)#2nd time text extract
            # if not resume_text:
            #     return Response({"success": False, "message": "Resume text extraction failed"}, status=400)

            analysis_result = analyzer.comprehensive_resume_analysis(
                resume_text,
                job_description
            )

            # if not analysis_result.get("success", False):
            #     return Response({"success": False, "message": "Resume analysis failed"}, status=400)

            # ------------------- STEP 5 — Save Parsed Resume -------------------
            parsed_resume, _ = ParsedResume.objects.update_or_create(
                user=user,
                defaults={
                    "uploaded_resume": uploaded_resume,
                    "raw_text": resume_text,
                    "raw_json": analysis_result.get("structured_data", {})
                }
            )
            # ------------------- STEP 8 — Find similar jobs -------------------
            # matched_jobs_result = find_similar_jobs(user, limit=5)
            # matched_jobs = matched_jobs_result.get("matched_jobs", []) if isinstance(matched_jobs_result, dict) else []

            # ------------------- STEP 9 — Save FULL analysis data -------------------
            resume_analysis = ResumeAnalysis.objects.create(
                user=user,
                parsed_resume=parsed_resume,
                career_insights=analysis_result.get("career_analysis", {}),
                certifications=analysis_result.get("certification_recommendations", []),
                learning_path=analysis_result.get("learning_path", {}),
                # job_matches=matched_jobs
            )

            # ------------------- BACKWARD COMPATIBILITY -------------------
            CareerInsight.objects.update_or_create(
                user=user,
                resume=parsed_resume,
                defaults={"insight_data": analysis_result.get("career_analysis", {})}
            )

            CertificationRecommendation.objects.update_or_create(
                user=user,
                resume=parsed_resume,
                defaults={"recommendations": analysis_result.get("certification_recommendations", [])}
            )

            LearningPath.objects.update_or_create(
                user=user,
                resume=parsed_resume,
                defaults={
                    "target_role": analysis_result.get("learning_path", {}).get("target_role", ""),
                    "path_data": analysis_result.get("learning_path", {})
                }
            )

            # # ------------------- STEP 10 — Send analysis email -------------------
            # try:
            #     self.send_analysis_email(user, analysis_result, parsed_resume.id)
            # except Exception as e:
            #     logger.error(f"❌ Email notification failed: {e}", exc_info=True)

            # ------------------- FINAL RESPONSE -------------------
            return Response({
                "success": True,
                "message": "Resume uploaded, analyzed, and matched successfully",
                # "matched_jobs": matched_jobs,
                "career_insights": analysis_result.get("career_analysis", {}),
                "certifications": analysis_result.get("certification_recommendations", []),
                "learning_path": analysis_result.get("learning_path", {}),
                "resume_id": parsed_resume.id,
                "analysis_id": resume_analysis.id
            }, status=201)

        except Exception as e:
            logger.error(f"❌ Resume upload failed: {str(e)}", exc_info=True)
            return Response({"success": False, "message": str(e)}, status=500)

    # ==================================================================
    # Send Resume Analysis Email
    # ==================================================================
    def send_analysis_email(self, user, analysis_result, resume_id):
        """
        Send email with normalized resume analysis results to the job seeker
        """
        try:
            # ------------------- User Info -------------------
            user_email = getattr(user, "email", None)
            if not user_email:
                logger.error("User email not found for notification")
                return False

            user_name = (
                getattr(user, "get_full_name", lambda: "")().strip()
                or getattr(user, "username", "Job Seeker")
            )

            # ------------------- Normalize Career Insights -------------------
            career_analysis = analysis_result.get("career_analysis", {})

            career_insights = {
                "strengths": [
                    insight.get("recommendation", "")
                    for insight in career_analysis.get("industry_insights", [])
                    if insight.get("recommendation")
                ],
                "improvement_areas": [
                    gap.get("skill")
                    for gap in career_analysis.get("skill_gap_analysis", [])
                    if gap.get("skill")
                ],
                "suggested_roles": [
                    role.get("role")
                    for role in career_analysis.get("suitable_roles", [])
                    if role.get("role")
                ],
            }

            # ------------------- Normalize Learning Path -------------------
            learning_raw = analysis_result.get("learning_path") or {}

            target_role = (
                career_analysis.get("suitable_roles", [{}])[0].get("role", "")
                if career_analysis.get("suitable_roles")
                else ""
            )

            learning_path = {
                "target_role": target_role,
                "skills_gap": [
                    gap.get("skill")
                    for gap in career_analysis.get("skill_gap_analysis", [])
                    if gap.get("skill")
                ],
                "recommended_courses": [
                    resource.get("name")
                    for phase in learning_raw.get("learning_path", [])
                    for resource in phase.get("resources", [])
                    if resource.get("type") == "course" and resource.get("name")
                ],
            }

            # ------------------- Normalize Certifications -------------------
            certifications = []
            for cert in analysis_result.get("certification_recommendations", []):
                certifications.append({
                    "name": cert.get("name", ""),
                    "description": cert.get("description")
                    or ", ".join(cert.get("benefits", [])),
                })

            # ------------------- Email Context -------------------
            context = {
                "user_name": user_name,
                "resume_id": resume_id,
                "career_insights": career_insights,
                "certifications": certifications,
                "learning_path": learning_path,
                "analysis_date": timezone.now().strftime("%B %d, %Y"),
            }

            logger.info(f"📧 Preparing resume analysis email for {user_email}")

            # ------------------- Render Email -------------------
            subject = f"Your Resume Analysis is Complete - {context['analysis_date']}"
            text_content = render_to_string(
                "emails/resume_analysis_complete.txt", context
            )
            html_content = render_to_string(
                "emails/resume_analysis_complete.html", context
            )

            # ------------------- Send Email -------------------
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_content,
                fail_silently=False,
            )

            logger.info(f"✅ Resume analysis email sent to {user_email}")
            return True

        except Exception as e:
            logger.error("❌ Error sending resume analysis email", exc_info=True)
            return False




# ======================================================================
# Additional Views & Helpers
# ======================================================================
def upload_success(request):
    return render(request, 'upload_success.html')


def parsing_status(request, uploaded_resume_id):
    """Show parsing progress/status"""
    try:
        uploaded_resume = UploadedResume.objects.get(id=uploaded_resume_id)
        parsed_resume = getattr(uploaded_resume, "parsed", None)

        context = {
            'uploaded_resume': uploaded_resume,
            'parsed': bool(parsed_resume),
            'parsed_resume': parsed_resume
        }
        return render(request, 'parsing_status.html', context)

    except UploadedResume.DoesNotExist:
        return render(request, 'parsing_status.html', {'error': 'Resume not found'})


# Add these to your cv_manager/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stored_career_insights(request):
    """Get career insights from database - NO re-analysis"""
    user = request.user
    try:
        # Try to get from ResumeAnalysis table first
        analysis = ResumeAnalysis.objects.filter(user=user).order_by('-analysis_timestamp').first()
        if analysis:
            return JsonResponse({
                "success": True,
                "career_insights": analysis.career_insights,
                "summary": analysis.career_insights.get("summary", "No summary available"),
                "timestamp": analysis.analysis_timestamp.isoformat()
            })
        
        return JsonResponse({
            "success": False, 
            "message": "No career insights found. Please upload a resume first."
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error fetching stored career insights: {str(e)}")
        return JsonResponse({
            "success": False, 
            "message": f"Failed to fetch career insights: {str(e)}"
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stored_certifications(request):
    """Get certifications from database - NO re-analysis"""
    user = request.user
    try:
        # Try to get from ResumeAnalysis table first
        analysis = ResumeAnalysis.objects.filter(user=user).order_by('-analysis_timestamp').first()
        if analysis:
            return JsonResponse({
                "success": True,
                "certifications": analysis.certifications,
                "timestamp": analysis.analysis_timestamp.isoformat()
            })
        
        return JsonResponse({
            "success": False, 
            "message": "No certifications found. Please upload a resume first."
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error fetching stored certifications: {str(e)}")
        return JsonResponse({
            "success": False, 
            "message": f"Failed to fetch certifications: {str(e)}"
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stored_learning_path(request):
    """Get learning path from database - NO re-analysis"""
    user = request.user
    try:
        # Try to get from ResumeAnalysis table first
        analysis = ResumeAnalysis.objects.filter(user=user).order_by('-analysis_timestamp').first()
        if analysis:
            learning_path = analysis.learning_path
            # Ensure the format matches what frontend expects
            if not learning_path.get('path_steps') and learning_path.get('learning_path'):
                learning_path['path_steps'] = learning_path['learning_path']
            
            return JsonResponse({
                "success": True,
                "learning_path": learning_path,
                "timestamp": analysis.analysis_timestamp.isoformat()
            })
        
        return JsonResponse({
            "success": False, 
            "message": "No learning path found. Please upload a resume first."
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error fetching stored learning path: {str(e)}")
        return JsonResponse({
            "success": False, 
            "message": f"Failed to fetch learning path: {str(e)}"
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stored_job_matches(request):
    """Get job matches from database - NO re-analysis"""
    user = request.user
    try:
        # Try to get from ResumeAnalysis table first
        analysis = ResumeAnalysis.objects.filter(user=user).order_by('-analysis_timestamp').first()
        if analysis:
            return JsonResponse({
                "success": True,
                "job_matches": analysis.job_matches,
                "matched_jobs": analysis.job_matches,  # For compatibility
                "timestamp": analysis.analysis_timestamp.isoformat()
            })
        
        return JsonResponse({
            "success": False, 
            "message": "No job matches found. Please upload a resume first."
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error fetching stored job matches: {str(e)}")
        return JsonResponse({
            "success": False, 
            "message": f"Failed to fetch job matches: {str(e)}"
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_resume_status(request):
    user = request.user
    parsed_resume = ParsedResume.objects.filter(user=user).first()
    if not parsed_resume:
        return Response({"has_resume": False, "message": "No resume uploaded yet"})
    has_text = bool(parsed_resume.raw_text and parsed_resume.raw_text.strip())
    return Response({
        "has_resume": True,
        "has_text": has_text,
        "text_length": len(parsed_resume.raw_text) if has_text else 0,
        "resume_id": parsed_resume.id
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_resume_analysis(request):
    try:
        analysis = ResumeAnalysis.objects.filter(user=request.user).order_by("-analysis_timestamp").first()
        if not analysis:
            return Response({})
        return Response({
            "career_insights": analysis.career_insights,
            "certifications": analysis.certifications,
            "learning_path": analysis.learning_path,
            "job_matches": analysis.job_matches,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def find_similar_jobs_view(request):
    """
    Returns only the similar jobs for the authenticated user.
    Query params:
        - limit (optional, default=5)
        - use_groq (optional, "true" or "false")
    """
    user = request.user
    try:
        use_groq = request.query_params.get("use_groq", "").lower() == "true"
        limit = int(request.query_params.get("limit", 5))

        result = find_similar_jobs(user=user, limit=limit, save_to_db=True)

        # Only return the matched jobs list
        matched_jobs = result.get("matched_jobs", [])

        return Response({"success": True, "matched_jobs": matched_jobs}, status=200)

    except Exception as e:
        logger.error(f"Job matching failed: {str(e)}", exc_info=True)
        return Response({"success": False, "message": f"Job matching failed: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_application_status(request, job_id):
    """Check if user has already applied for a specific job"""
    user = request.user
    
    try:
        # Check if job exists
        from jobs.models import Job
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)
        
        # For now, check from ResumeAnalysis job_matches
        analysis = ResumeAnalysis.objects.filter(user=user).order_by('-analysis_timestamp').first()
        has_applied = False
        
        if analysis and analysis.job_matches:
            # Check if job_id is in job_matches
            for job_match in analysis.job_matches:
                if isinstance(job_match, dict) and job_match.get('job_id') == job_id:
                    has_applied = True
                    break
        
        # Alternative: Check from JobMatch table
        from cv_manager.models import JobMatch
        job_match = JobMatch.objects.filter(user=user, job_id=job_id).first()
        if job_match:
            has_applied = True
        
        return Response({
            "applied": has_applied,
            "job_id": job_id,
            "job_title": job.title
        })
        
    except Exception as e:
        logger.error(f"Error checking application status: {e}")
        return Response({"error": str(e)}, status=500)