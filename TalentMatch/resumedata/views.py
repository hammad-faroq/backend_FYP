from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from jobs.models import Job, JobApplication
from resumedata.models import ResumeData
from resumedata.serializer import ResumeSerializer

# Import both analyzers
from resumedata.analyzer import process_resume as process_resume_llm
from resumedata.qdrant_service import process_resume as process_resume_bert
from resumedata.custom_model import predict_resume_score
from jobs.models import JobRankingConfig
from jobs.services.ranking import calculate_rank


class AnalyzeResumeAPI(APIView):
    """
    POST /api/resumedata/analyze/
    {
        "job_application_id": 12
    }

    ✅ Runs:
       - Groq LLM analysis
       - BERT + Qdrant similarity analysis
       - Custom ML model scoring
    """
    def post(self, request):
        try:
            data = request.data
            job_app_id = data.get("job_application_id")
            if not job_app_id:
                return Response({
                    "status": False,
                    "message": "job_application_id is required",
                    "data": None
                })

            # --- Fetch job & resume ---
            job_app = JobApplication.objects.select_related("job", "applicant").get(id=job_app_id)
            job = job_app.job
            resume_path = job_app.resume.path
            job_description = f"{job.title}\n{job.description}\n{job.requirements}"

            # --- Groq LLM ---
            print("🧠 Running Groq LLM analysis...")
            llm_result = process_resume_llm(resume_path, job_description)
            llm_result.setdefault("rank", 0)
            llm_result.setdefault("skills", [])
            llm_result.setdefault("total_experience", "0")
            llm_result.setdefault("project_category", [])

            # --- BERT + Qdrant ---
            print("⚙️ Running BERT + Qdrant similarity analysis...")
            bert_result = process_resume_bert(resume_path, job_description, job_id=job.id)
            bert_score = bert_result.get("similarity_score", 0)

            # --- Custom ML model ---
            print("🤖 Running custom ML model scoring...")
            custom_score = predict_resume_score(resume_path, job_description)
            # --- Weighted combined rank ---
            from jobs.services.ranking import calculate_rank

            combined_rank = calculate_rank(
                groq_rank=llm_result.get("rank", 0),
                bert_similarity=bert_score,
                custom_model_score=custom_score,
            )


            # --- Save ResumeData ---
            resume_data, _ = ResumeData.objects.update_or_create(
                job_application=job_app,
                defaults={
                    "extracted_text": llm_result.get("summary", ""),
                    "analyzed_skills": llm_result.get("skills", []),
                    "experience_years": float(llm_result.get("total_experience", 0)),
                    "education": ", ".join(llm_result.get("project_category", [])),
                },
            )

            # --- Save JobApplication ---
            job_app.rank_score = combined_rank
            job_app.groq_rank = llm_result.get("rank", 0)
            job_app.bert_similarity = bert_score
            job_app.custom_model_score = custom_score
            job_app.cgpa = llm_result.get("CGPA", "N/A")
            job_app.skills = llm_result.get("skills", [])
            job_app.total_experience = str(llm_result.get("total_experience", "0"))
            job_app.save()


            return Response({
                "status": True,
                "message": "Resume analyzed successfully using Groq, BERT, and Custom ML model.",
                "mode": "combined",
                "data": {
                    "combined_rank": combined_rank,
                    "groq_analysis": llm_result,
                    "bert_analysis": bert_result,
                    "custom_model_score": custom_score,
                    "resume_data": ResumeSerializer(resume_data).data,
                }
            })

        except JobApplication.DoesNotExist:
            return Response({
                "status": False,
                "message": "Invalid job_application_id",
                "data": None
            })

        except Exception as e:
            print("❌ AnalyzeResumeAPI error:", e)
            return Response({
                "status": False,
                "message": str(e),
                "data": None
            })



