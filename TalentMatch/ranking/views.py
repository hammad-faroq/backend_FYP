from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ranking.services.ranking_engine import rank_applicants_for_job
from jobs.models import Job

# analysis/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests

HF_API_URL = "https://irfaniiioo-cvjdgradio.hf.space/api/predict/"
FN_INDEX = 0  # Usually 0 for first function

@api_view(['POST'])
def cv_job_match(request):
    cv = request.data.get("cv")
    job_description = request.data.get("job_description")

    if not cv or not job_description:
        return Response({"error": "CV or Job Description missing"}, status=400)

    try:
        payload = {
            "data": [cv, job_description],
            "fn_index": FN_INDEX
        }
        hf_response = requests.post(HF_API_URL, json=payload)
        hf_response.raise_for_status()
        result = hf_response.json().get("data", [None])[0]

        return Response(result)
    except Exception as e:
        print("CV-Job API error:", e)
        return Response({"error": "Failed to fetch CV-Job matching"}, status=500)
# # ___________________

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_ranking_for_job(request, job_id):
    # Only HR who owns the job can trigger ranking
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found."}, status=404)

    if request.user.role != 'hr' or job.created_by != request.user:
        return Response({"error": "Not authorized."}, status=403)

    results = rank_applicants_for_job(job_id, use_qdrant=True, save_to_db=True)
    return Response({"status": True, "ranked": results})
