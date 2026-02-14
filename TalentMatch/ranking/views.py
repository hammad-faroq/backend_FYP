from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ranking.services.ranking_engine import rank_applicants_for_job
from jobs.models import Job

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
